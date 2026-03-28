"""Core low-level keyboard hook implementation for a single thread."""

from __future__ import annotations
import ctypes
import logging
from ctypes import wintypes
from typing import Callable

from .constants import WH_KEYBOARD_LL, WM_QUIT
from .bindings import (
    set_hook, unhook, next_hook,
    get_message, translate_msg, dispatch_msg,
    get_thread_id, post_thread_msg,
)
from .events import KeyEvent

logger = logging.getLogger(__name__)

LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)


class KeyboardHook:
    """
    Low-level keyboard hook.
    Installs the Win32 hook and runs a message loop on the calling thread.

    Parameters
    ----------
    on_key:
        Called for every key event.
        Signature: (KeyEvent) -> bool | None
        Return True to suppress the key, False/None to pass through.
    on_error:
        Called if an exception escapes on_key.
        Signature: (Exception) -> None
        Defaults to logging the error and stopping the hook.
    """

    def __init__(
        self,
        on_key   : Callable[[KeyEvent], bool | None] | None = None,
        on_error : Callable[[Exception], None] | None = None,
    ):
        self._on_key    = on_key
        self._on_error  = on_error or self._default_error_handler
        self._hook      = None
        self._thread_id = None
        self._proc      = LowLevelKeyboardProc(self._hook_proc)

    # --- Core ---

    def _hook_proc(self, n_code: int, w_param: int, l_param: int) -> int:
        """Win32 low-level hook procedure invoked for each keyboard message."""
        if n_code >= 0:
            try:
                event = KeyEvent.from_lparam(w_param, l_param)
                if self._on_key and self._on_key(event):
                    return 1  # suppress
            except KeyboardInterrupt:
                self.stop()
                return 0
            except Exception as exc:
                self._on_error(exc)
                return 0
        return next_hook(self._hook, n_code, w_param, l_param)

    def _default_error_handler(self, exc: Exception):
        """Log callback failures and request loop shutdown."""
        logger.error("Hook callback error: %s", exc, exc_info=True)
        self.stop()

    # --- Lifecycle ---

    def install(self):
        """Install the Win32 hook on the current thread."""
        if self._hook:
            raise RuntimeError("Hook already installed")
        self._thread_id = get_thread_id()
        self._hook = set_hook(WH_KEYBOARD_LL, self._proc, None, 0)
        logger.debug("Hook installed: %s (tid=%s)", self._hook, self._thread_id)

    def uninstall(self):
        """Remove the Win32 hook if it is currently installed."""
        if self._hook:
            unhook(self._hook)
            self._hook      = None
            self._thread_id = None
            logger.debug("Hook uninstalled")

    def run(self):
        """Pump messages until stop() is called. Blocks the calling thread."""
        msg = wintypes.MSG()
        while get_message(ctypes.byref(msg), None, 0, 0):
            translate_msg(ctypes.byref(msg))
            dispatch_msg(ctypes.byref(msg))

    def stop(self):
        """Post WM_QUIT to the message loop. Safe to call from any thread."""
        if self._thread_id:
            post_thread_msg(self._thread_id, WM_QUIT, 0, 0)

    @property
    def running(self) -> bool:
        """Return ``True`` when the hook handle is currently installed."""
        return self._hook is not None

    # --- Context manager ---

    def __enter__(self):
        """Install the hook when entering a context manager block."""
        self.install()
        return self

    def __exit__(self, *_):
        """Uninstall the hook when leaving a context manager block."""
        self.uninstall()

    def __repr__(self):
        return f"<KeyboardHook running={self.running}>"
