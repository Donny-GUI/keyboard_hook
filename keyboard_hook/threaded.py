"""Thread-based wrappers that run keyboard hooks in background threads."""

from __future__ import annotations
import inspect
import logging
import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Literal

from .events import KeyEvent
from .hook import KeyboardHook
from .constants import Key

logger = logging.getLogger(__name__)

TriggerMode = Literal["down", "up", "first_down", "repeat"]
_VALID_TRIGGERS = {"down", "up", "first_down", "repeat"}


@dataclass(slots=True)
class _HotkeyBinding:
    keys: frozenset[int]
    callback: Callable
    trigger: TriggerMode
    pass_event: bool


def _callback_accepts_event(callback: Callable) -> bool:
    """Return ``True`` when callback can accept a positional event argument."""
    try:
        params = inspect.signature(callback).parameters.values()
    except (TypeError, ValueError):
        return False
    for param in params:
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            return True
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
    return False


class ThreadedKeyboardHook(KeyboardHook):
    """
    KeyboardHook that runs its message loop on a background thread.

    Parameters
    ----------
    on_key:
        Called for every key event (on the hook thread).
    on_error:
        Called if an exception escapes on_key.
    daemon:
        Whether the hook thread is a daemon thread (default True).
    """

    def __init__(
        self,
        on_key   : Callable[[KeyEvent], bool | None] | None = None,
        on_error : Callable[[Exception], None] | None = None,
        daemon   : bool = True,
    ):
        super().__init__(on_key=on_key, on_error=on_error)
        self._daemon  = daemon
        self._thread  = None
        self._ready   = threading.Event()

    def _run(self):
        """Install the hook and run the message loop on the worker thread."""
        self.install()
        self._ready.set()
        try:
            self.run()
        finally:
            # Ensure the hook is always removed if the loop exits unexpectedly.
            self.uninstall()

    def start(self, timeout: float = 2.0):
        """Start the hook thread and block until the hook is installed."""
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Hook thread already running")
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, daemon=self._daemon)
        self._thread.start()
        if not self._ready.wait(timeout):
            raise RuntimeError("Hook did not install within timeout")
        logger.debug("Hook thread started")

    def join(self, timeout: float | None = None):
        """Wait for the hook thread to exit."""
        if self._thread:
            self._thread.join(timeout)

    @property
    def running(self) -> bool:
        """Return ``True`` while the background hook thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def __enter__(self):
        """Start the hook thread when entering a context manager block."""
        self.start()
        return self

    def __exit__(self, *_):
        """Stop and join the hook thread on context manager exit."""
        self.stop()
        self.join()


class HotkeyHook(ThreadedKeyboardHook):
    """
    ThreadedKeyboardHook with a hotkey registry and main-thread blocking.

    Usage
    -----
        hook = HotkeyHook()
        hook.register("ESCAPE", hook.stop)
        hook.register("A", lambda: print("A!"))

        with hook:
            hook.wait()

    Keys can be registered by ``Key`` enum, VK name (from ``constants.VK``),
    or raw vk_code int. Supports combo strings like ``"CTRL+SHIFT+S"`` and
    trigger modes: ``down``, ``up``, ``first_down``, and ``repeat``.
    Callbacks fire on the hook thread - keep them short or hand off to a queue.
    """

    def __init__(self, daemon: bool = True):
        """Initialize a threaded hotkey hook with no registered callbacks."""
        super().__init__(on_key=self._dispatch, daemon=daemon)
        self._bindings : list[_HotkeyBinding] = []
        self._listeners: list[Callable[[KeyEvent], None]] = []
        self._pressed  : set[int] = set()
        self._stopped  = threading.Event()

    # --- Registration ---

    def register(
        self,
        key: Key | str | int,
        callback: Callable,
        *,
        on_keyup: bool = False,
        trigger: TriggerMode | None = None,
    ) -> HotkeyHook:
        """
        Register a callback for a single key.

        Parameters
        ----------
        key:
            Key name (e.g. "ESCAPE", "A", "F5"), ``Key`` enum member, or raw
            vk_code int.
        callback:
            Called when the key fires. Callbacks may optionally accept one
            positional argument (``KeyEvent``).
        on_keyup:
            Backward-compatible alias for ``trigger="up"``.
        trigger:
            One of ``"down"``, ``"up"``, ``"first_down"``, ``"repeat"``.
        """
        vk = self._resolve(key)
        mode = self._normalize_trigger(trigger=trigger, on_keyup=on_keyup)
        self._bindings.append(
            _HotkeyBinding(
                keys=frozenset({vk}),
                callback=callback,
                trigger=mode,
                pass_event=_callback_accepts_event(callback),
            )
        )
        return self

    def unregister(self, key: Key | str | int, callback: Callable | None = None) -> HotkeyHook:
        """Remove a specific callback, or all callbacks for a key."""
        vk = self._resolve(key)
        self._remove_bindings(keys=frozenset({vk}), callback=callback)
        return self

    def register_combo(
        self,
        keys: str | Iterable[Key | str | int],
        callback: Callable,
        *,
        trigger: TriggerMode = "first_down",
    ) -> HotkeyHook:
        """
        Register a callback for a key combination.

        Examples
        --------
        ``register_combo("CTRL+SHIFT+S", callback)``
        ``register_combo([Key.CTRL, Key.SHIFT, Key.S], callback)``
        """
        combo = self._resolve_combo(keys)
        if len(combo) < 2:
            raise ValueError("Combo must contain at least two distinct keys")
        mode = self._normalize_trigger(trigger=trigger, on_keyup=False)
        self._bindings.append(
            _HotkeyBinding(
                keys=combo,
                callback=callback,
                trigger=mode,
                pass_event=_callback_accepts_event(callback),
            )
        )
        return self

    def unregister_combo(
        self,
        keys: str | Iterable[Key | str | int],
        callback: Callable | None = None,
    ) -> HotkeyHook:
        """Remove a specific combo callback, or all callbacks for the combo."""
        combo = self._resolve_combo(keys)
        self._remove_bindings(keys=combo, callback=callback)
        return self

    def listen(self, callback: Callable[[KeyEvent], None]) -> HotkeyHook:
        """Register a raw listener that receives every KeyEvent."""
        self._listeners.append(callback)
        return self

    def unlisten(self, callback: Callable[[KeyEvent], None]) -> HotkeyHook:
        """Remove a raw event listener previously added with :meth:`listen`."""
        self._listeners = [cb for cb in self._listeners if cb is not callback]
        return self

    # --- Internals ---

    @staticmethod
    def _normalize_trigger(*, trigger: TriggerMode | None, on_keyup: bool) -> TriggerMode:
        if trigger is None:
            return "up" if on_keyup else "down"
        mode = trigger.lower()
        if mode not in _VALID_TRIGGERS:
            raise ValueError(f"Unknown trigger: {trigger!r}")
        if on_keyup and mode != "up":
            raise ValueError("on_keyup=True cannot be combined with trigger != 'up'")
        return mode

    @staticmethod
    def _resolve(key: Key | str | int) -> int:
        """Resolve a key name or virtual key code to an integer vk code."""
        from .constants import VK
        if isinstance(key, Key):
            return int(key)
        if isinstance(key, int):
            return key
        try:
            return VK[key.upper()]
        except KeyError:
            raise ValueError(
                f"Unknown key name: {key!r}. Use a VK name, Key enum member, or raw int."
            ) from None

    @classmethod
    def _resolve_combo(cls, keys: str | Iterable[Key | str | int]) -> frozenset[int]:
        if isinstance(keys, str):
            parts = [part.strip() for part in keys.split("+") if part.strip()]
            if not parts:
                raise ValueError("Combo string is empty")
            resolved = [cls._resolve(part) for part in parts]
        else:
            resolved = [cls._resolve(part) for part in keys]
            if not resolved:
                raise ValueError("Combo must contain at least one key")
        return frozenset(resolved)

    def _remove_bindings(self, *, keys: frozenset[int], callback: Callable | None):
        if callback is None:
            self._bindings = [binding for binding in self._bindings if binding.keys != keys]
            return
        self._bindings = [
            binding
            for binding in self._bindings
            if not (binding.keys == keys and binding.callback is callback)
        ]

    @staticmethod
    def _active_triggers(event: KeyEvent, *, was_pressed: bool) -> set[TriggerMode]:
        if event.is_keyup:
            return {"up"}
        if event.is_keydown:
            if was_pressed:
                return {"down", "repeat"}
            return {"down", "first_down"}
        return set()

    @staticmethod
    def _invoke_callback(binding: _HotkeyBinding, event: KeyEvent):
        if binding.pass_event:
            binding.callback(event)
        else:
            binding.callback()

    def _dispatch(self, event: KeyEvent) -> bool:
        """Dispatch one event to listeners and matching hotkey callbacks."""
        # Raw listeners always fire
        for cb in self._listeners:
            try:
                cb(event)
            except Exception as exc:
                logger.error("Listener error: %s", exc, exc_info=True)

        vk = event.vk_code
        was_pressed = vk in self._pressed
        if event.is_keydown and not was_pressed:
            self._pressed.add(vk)
        elif event.is_keyup and not was_pressed:
            # Keep release semantics stable even when keydown was missed.
            self._pressed.add(vk)

        active = self._active_triggers(event, was_pressed=was_pressed)
        if active:
            pressed = frozenset(self._pressed)
            for binding in list(self._bindings):
                if vk not in binding.keys:
                    continue
                if binding.trigger not in active:
                    continue
                if not binding.keys.issubset(pressed):
                    continue
                try:
                    self._invoke_callback(binding, event)
                except Exception as exc:
                    logger.error("Hotkey callback error: %s", exc, exc_info=True)

        if event.is_keyup:
            self._pressed.discard(vk)

        return False  # never suppress from here

    def stop(self):
        """Stop the underlying hook loop and release :meth:`wait`."""
        super().stop()
        self._pressed.clear()
        self._stopped.set()

    def wait(self):
        """Block the calling thread until stop() is called."""
        self._stopped.wait()

    def __exit__(self, *_):
        """Ensure shutdown signaling and thread join on context exit."""
        self.stop()
        self.join()
