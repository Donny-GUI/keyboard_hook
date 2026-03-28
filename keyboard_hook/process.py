"""Process-isolated keyboard hook that forwards events to the parent."""

from __future__ import annotations
import ctypes
import inspect
import logging
import multiprocessing
import threading
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable, Iterable, Literal

from .constants import Key
from .events import KeyEvent

logger = logging.getLogger(__name__)

_READY = "ready"
_STOP  = "stop"

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


def _hook_process_main(pipe, log_level: int):
    """
    Child process entry point for the hook worker.

    This function is module-level so it can be pickled by the
    ``multiprocessing`` spawn start method used on Windows.
    """
    import ctypes
    from ctypes import wintypes
    import threading
    import logging

    logging.basicConfig(level=log_level)

    from keyboard_hook.bindings import (
        set_hook, unhook, next_hook,
        get_message, translate_msg, dispatch_msg,
        get_thread_id, post_thread_msg,
    )
    from keyboard_hook.constants import WH_KEYBOARD_LL, WM_QUIT
    from keyboard_hook.events import KeyEvent

    LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
        ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    )

    thread_id   = get_thread_id()
    hook_handle = None

    def hook_proc(n_code, w_param, l_param):
        if n_code >= 0:
            try:
                event = KeyEvent.from_lparam(w_param, l_param)
                pipe.send(event)
            except (BrokenPipeError, OSError):
                post_thread_msg(thread_id, WM_QUIT, 0, 0)
                return 0
            except Exception as e:
                logging.error("hook_proc error: %s", e)
        return next_hook(hook_handle, n_code, w_param, l_param)

    proc = LowLevelKeyboardProc(hook_proc)

    def watch_pipe():
        try:
            pipe.recv()
        except EOFError:
            pass
        post_thread_msg(thread_id, WM_QUIT, 0, 0)

    threading.Thread(target=watch_pipe, daemon=True).start()

    hook_handle = set_hook(WH_KEYBOARD_LL, proc, None, 0)
    pipe.send(_READY)

    msg = wintypes.MSG()
    while get_message(ctypes.byref(msg), None, 0, 0):
        translate_msg(ctypes.byref(msg))
        dispatch_msg(ctypes.byref(msg))

    unhook(hook_handle)
    pipe.close()
    logging.debug("Child process: exiting")


class ProcessKeyboardHook:
    """
    Keyboard hook running in a separate process.

    Key events are forwarded over a Pipe and dispatched on a background
    thread in the parent process. Because the hook lives in its own process,
    it survives parent thread crashes and can always be killed cleanly.

    Parameters
    ----------
    log_level:
        Logging level for the child process.

    Usage
    -----
        hook = ProcessKeyboardHook()
        hook.register("ESCAPE", hook.stop)
        hook.register("A", lambda: print("A!"))
        hook.listen(lambda e: print(e))

        with hook:
            hook.wait()
    """

    def __init__(self, log_level: int = logging.WARNING):
        """Create a process-backed hook controller."""
        self._log_level  = log_level
        self._bindings   : list[_HotkeyBinding] = []
        self._listeners  : list[Callable[[KeyEvent], None]] = []
        self._pressed    : set[int] = set()
        self._process    : multiprocessing.Process | None = None
        self._pipe       = None
        self._reader     : threading.Thread | None = None
        self._stopped    = threading.Event()

    # --- Registration ---

    def register(
        self,
        key: Key | str | int,
        callback: Callable,
        *,
        on_keyup: bool = False,
        trigger: TriggerMode | None = None,
    ) -> ProcessKeyboardHook:
        """Register a callback for a single key event."""
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

    def unregister(self, key: Key | str | int, callback: Callable | None = None) -> ProcessKeyboardHook:
        """Remove one callback for a key, or all callbacks for that key."""
        vk = self._resolve(key)
        self._remove_bindings(keys=frozenset({vk}), callback=callback)
        return self

    def register_combo(
        self,
        keys: str | Iterable[Key | str | int],
        callback: Callable,
        *,
        trigger: TriggerMode = "first_down",
    ) -> ProcessKeyboardHook:
        """Register a callback for a key combination."""
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
    ) -> ProcessKeyboardHook:
        """Remove a specific combo callback, or all callbacks for the combo."""
        combo = self._resolve_combo(keys)
        self._remove_bindings(keys=combo, callback=callback)
        return self

    def listen(self, callback: Callable[[KeyEvent], None]) -> ProcessKeyboardHook:
        """Register a listener that receives every forwarded :class:`KeyEvent`."""
        self._listeners.append(callback)
        return self

    def unlisten(self, callback: Callable[[KeyEvent], None]) -> ProcessKeyboardHook:
        """Remove a listener previously added with :meth:`listen`."""
        self._listeners = [cb for cb in self._listeners if cb is not callback]
        return self

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

    # --- Lifecycle ---

    def start(self, timeout: float = 5.0):
        """Start the hook child process and reader thread."""
        if self._process and self._process.is_alive():
            raise RuntimeError("Hook process already running")

        parent_conn, child_conn = multiprocessing.Pipe()
        self._pipe    = parent_conn
        self._stopped.clear()

        self._process = multiprocessing.Process(
            target = _hook_process_main,
            args   = (child_conn, self._log_level),
            daemon = True,
        )
        self._process.start()
        child_conn.close()

        if not parent_conn.poll(timeout):
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(1.0)
            parent_conn.close()
            self._pipe = None
            self._process = None
            raise RuntimeError("Hook process did not start within timeout")

        msg = parent_conn.recv()
        if msg != _READY:
            if self._process.is_alive():
                self._process.terminate()
            self._process.join(1.0)
            parent_conn.close()
            self._pipe = None
            self._process = None
            raise RuntimeError(f"Unexpected startup message: {msg!r}")

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

        logger.debug("Hook process started (pid=%s)", self._process.pid)

    def stop(self):
        """Gracefully signal the child to shut down."""
        if self._pipe:
            try:
                self._pipe.send(_STOP)
            except OSError:
                pass
        self._pressed.clear()
        self._stopped.set()

    def kill(self):
        """Immediately terminate the child process."""
        if self._process:
            self._process.terminate()
        self._stopped.set()

    def join(self, timeout: float = 3.0):
        """Wait for child process and reader thread shutdown."""
        if self._process:
            self._process.join(timeout)
            if self._process.is_alive():
                logger.warning("Process did not exit cleanly — killing")
                self._process.kill()
        if self._reader:
            self._reader.join(timeout)

    def wait(self):
        """Block until stop() or kill() is called."""
        self._stopped.wait()

    @property
    def running(self) -> bool:
        """Return ``True`` while the child hook process is alive."""
        return self._process is not None and self._process.is_alive()

    # --- Event loop ---

    def _read_loop(self):
        """Receive events from the child process and dispatch them locally."""
        while True:
            try:
                if not self._pipe.poll(0.05):
                    if not self._process.is_alive():
                        break
                    continue
                event = self._pipe.recv()
                if isinstance(event, KeyEvent):
                    self._dispatch(event)
            except EOFError:
                break
            except OSError:
                break
        self._stopped.set()

    def _dispatch(self, event: KeyEvent):
        """Dispatch one event to listeners and matching registered hotkeys."""
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
                    logger.error("Hotkey error: %s", exc, exc_info=True)

        if event.is_keyup:
            self._pressed.discard(vk)

    # --- Context manager ---

    def __enter__(self):
        """Start the child hook process on context manager entry."""
        self.start()
        return self

    def __exit__(self, *_):
        """Stop and join worker resources on context manager exit."""
        self.stop()
        self.join()

    def __repr__(self):
        return f"<ProcessKeyboardHook running={self.running} pid={self._process.pid if self._process else None}>"
