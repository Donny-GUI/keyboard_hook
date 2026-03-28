from __future__ import annotations
import ctypes
import logging
import multiprocessing
import threading
from ctypes import wintypes
from typing import Callable

from .constants import WM_KEYDOWN, WM_SYSKEYDOWN
from .events import KeyEvent

logger = logging.getLogger(__name__)

_READY = "ready"
_STOP  = "stop"


def _hook_process_main(pipe, log_level: int):
    """
    Child process entry point.
    Must be a top-level function for multiprocessing spawn to pickle it.
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
        self._log_level  = log_level
        self._hotkeys    : dict[int, list[tuple[Callable, bool]]] = {}
        self._listeners  : list[Callable[[KeyEvent], None]] = []
        self._process    : multiprocessing.Process | None = None
        self._pipe       = None
        self._reader     : threading.Thread | None = None
        self._stopped    = threading.Event()

    # --- Registration ---

    def register(self, key: str | int, callback: Callable, *, on_keyup=False) -> ProcessKeyboardHook:
        vk = self._resolve(key)
        self._hotkeys.setdefault(vk, []).append((callback, on_keyup))
        return self

    def unregister(self, key: str | int, callback: Callable | None = None) -> ProcessKeyboardHook:
        vk = self._resolve(key)
        if callback is None:
            self._hotkeys.pop(vk, None)
        else:
            entries = self._hotkeys.get(vk, [])
            self._hotkeys[vk] = [(cb, ku) for cb, ku in entries if cb is not callback]
        return self

    def listen(self, callback: Callable[[KeyEvent], None]) -> ProcessKeyboardHook:
        self._listeners.append(callback)
        return self

    def unlisten(self, callback: Callable[[KeyEvent], None]) -> ProcessKeyboardHook:
        self._listeners = [cb for cb in self._listeners if cb is not callback]
        return self

    @staticmethod
    def _resolve(key: str | int) -> int:
        if isinstance(key, int):
            return key
        from .constants import VK
        try:
            return VK[key.upper()]
        except KeyError:
            raise ValueError(f"Unknown key name: {key!r}") from None

    # --- Lifecycle ---

    def start(self, timeout: float = 5.0):
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
            self._process.terminate()
            raise RuntimeError("Hook process did not start within timeout")

        msg = parent_conn.recv()
        if msg != _READY:
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
        self._stopped.set()

    def kill(self):
        """Immediately terminate the child process."""
        if self._process:
            self._process.terminate()
        self._stopped.set()

    def join(self, timeout: float = 3.0):
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
        return self._process is not None and self._process.is_alive()

    # --- Event loop ---

    def _read_loop(self):
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
        for cb in self._listeners:
            try:
                cb(event)
            except Exception as exc:
                logger.error("Listener error: %s", exc, exc_info=True)

        for callback, on_keyup in self._hotkeys.get(event.vk_code, []):
            if event.is_keyup == on_keyup:
                try:
                    callback()
                except Exception as exc:
                    logger.error("Hotkey error: %s", exc, exc_info=True)

    # --- Context manager ---

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
        self.join()

    def __repr__(self):
        return f"<ProcessKeyboardHook running={self.running} pid={self._process.pid if self._process else None}>"
