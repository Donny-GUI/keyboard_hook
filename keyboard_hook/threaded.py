"""Thread-based wrappers that run keyboard hooks in background threads."""

from __future__ import annotations
import logging
import threading
from typing import Callable

from .events import KeyEvent
from .hook import KeyboardHook
from .constants import WM_KEYDOWN, WM_SYSKEYDOWN

logger = logging.getLogger(__name__)


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

    Keys can be registered by name (from constants.VK) or raw vk_code int.
    Callbacks fire on the hook thread — keep them short or hand off to a queue.
    """

    def __init__(self, daemon: bool = True):
        """Initialize a threaded hotkey hook with no registered callbacks."""
        super().__init__(on_key=self._dispatch, daemon=daemon)
        self._hotkeys  : dict[int, list[tuple[Callable, bool]]] = {}
        self._listeners: list[Callable[[KeyEvent], None]] = []
        self._stopped  = threading.Event()

    # --- Registration ---

    def register(self, key: str | int, callback: Callable, *, on_keyup=False) -> HotkeyHook:
        """
        Register a callback for a key.

        Parameters
        ----------
        key:
            Key name (e.g. "ESCAPE", "A", "F5") or raw vk_code int.
        callback:
            Called with no arguments when the key fires.
        on_keyup:
            Fire on key-up instead of key-down (default False).
        """
        vk = self._resolve(key)
        self._hotkeys.setdefault(vk, []).append((callback, on_keyup))
        return self

    def unregister(self, key: str | int, callback: Callable | None = None) -> HotkeyHook:
        """Remove a specific callback, or all callbacks for a key."""
        vk = self._resolve(key)
        if callback is None:
            self._hotkeys.pop(vk, None)
        else:
            entries = self._hotkeys.get(vk, [])
            self._hotkeys[vk] = [(cb, ku) for cb, ku in entries if cb is not callback]
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
    def _resolve(key: str | int) -> int:
        """Resolve a key name or virtual key code to an integer vk code."""
        if isinstance(key, int):
            return key
        from .constants import VK
        try:
            return VK[key.upper()]
        except KeyError:
            raise ValueError(f"Unknown key name: {key!r}. Use a VK name or raw int.") from None

    def _dispatch(self, event: KeyEvent) -> bool:
        """Dispatch one event to listeners and matching hotkey callbacks."""
        # Raw listeners always fire
        for cb in self._listeners:
            try:
                cb(event)
            except Exception as exc:
                logger.error("Listener error: %s", exc, exc_info=True)

        # Hotkeys fire on correct edge
        for callback, on_keyup in self._hotkeys.get(event.vk_code, []):
            if event.is_keyup == on_keyup:
                try:
                    callback()
                except Exception as exc:
                    logger.error("Hotkey callback error: %s", exc, exc_info=True)

        return False  # never suppress from here

    def stop(self):
        """Stop the underlying hook loop and release :meth:`wait`."""
        super().stop()
        self._stopped.set()

    def wait(self):
        """Block the calling thread until stop() is called."""
        self._stopped.wait()

    def __exit__(self, *_):
        """Ensure shutdown signaling and thread join on context exit."""
        self.stop()
        self.join()
