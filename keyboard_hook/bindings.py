"""Typed Win32 API bindings used by the keyboard hook implementation."""

import ctypes
from ctypes import wintypes
from .winfunc import User32Func, Kernel32Func


class SetWindowsHookExW(User32Func):
    """Wrap ``user32.SetWindowsHookExW`` for low-level hook installation."""
    name     = "SetWindowsHookExW"
    restype  = wintypes.HHOOK
    argtypes = (
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.HINSTANCE,
        wintypes.DWORD,
    )

class UnhookWindowsHookEx(User32Func):
    """Wrap ``user32.UnhookWindowsHookEx`` to remove installed hooks."""
    name     = "UnhookWindowsHookEx"
    restype  = wintypes.BOOL
    argtypes = (wintypes.HHOOK,)

class CallNextHookEx(User32Func):
    """Wrap ``user32.CallNextHookEx`` to continue hook chain processing."""
    name          = "CallNextHookEx"
    restype       = wintypes.LPARAM
    null_is_error = False
    argtypes      = (
        wintypes.HHOOK,
        ctypes.c_int,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )

class GetMessageW(User32Func):
    """Wrap ``user32.GetMessageW`` to pump the thread message queue."""
    name          = "GetMessageW"
    restype       = wintypes.BOOL
    null_is_error = False
    argtypes      = (
        ctypes.POINTER(wintypes.MSG),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
    )

    @classmethod
    def _errcheck(cls, result, func, args):
        if result == -1:
            raise ctypes.WinError()
        return result

class TranslateMessage(User32Func):
    """Wrap ``user32.TranslateMessage`` for message loop integration."""
    name          = "TranslateMessage"
    restype       = wintypes.BOOL
    null_is_error = False
    argtypes      = (ctypes.POINTER(wintypes.MSG),)

class DispatchMessageW(User32Func):
    """Wrap ``user32.DispatchMessageW`` for message loop dispatch."""
    name          = "DispatchMessageW"
    restype       = wintypes.LPARAM
    null_is_error = False
    argtypes      = (ctypes.POINTER(wintypes.MSG),)

class GetCurrentThreadId(Kernel32Func):
    """Wrap ``kernel32.GetCurrentThreadId`` for loop targeting."""
    name          = "GetCurrentThreadId"
    restype       = wintypes.DWORD
    null_is_error = False
    argtypes      = ()

class PostThreadMessageW(User32Func):
    """Wrap ``user32.PostThreadMessageW`` to signal message loops."""
    name     = "PostThreadMessageW"
    restype  = wintypes.BOOL
    argtypes = (
        wintypes.DWORD,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )


# Singleton callables - import these directly.
set_hook        = SetWindowsHookExW()
unhook          = UnhookWindowsHookEx()
next_hook       = CallNextHookEx()
get_message     = GetMessageW()
translate_msg   = TranslateMessage()
dispatch_msg    = DispatchMessageW()
get_thread_id   = GetCurrentThreadId()
post_thread_msg = PostThreadMessageW()
