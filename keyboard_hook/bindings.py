import ctypes
from ctypes import wintypes
from .winfunc import User32Func, Kernel32Func


class SetWindowsHookExW(User32Func):
    name     = "SetWindowsHookExW"
    restype  = wintypes.HHOOK
    argtypes = (
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.HINSTANCE,
        wintypes.DWORD,
    )

class UnhookWindowsHookEx(User32Func):
    name     = "UnhookWindowsHookEx"
    restype  = wintypes.BOOL
    argtypes = (wintypes.HHOOK,)

class CallNextHookEx(User32Func):
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
    name          = "TranslateMessage"
    restype       = wintypes.BOOL
    null_is_error = False
    argtypes      = (ctypes.POINTER(wintypes.MSG),)

class DispatchMessageW(User32Func):
    name          = "DispatchMessageW"
    restype       = wintypes.LPARAM
    null_is_error = False
    argtypes      = (ctypes.POINTER(wintypes.MSG),)

class GetCurrentThreadId(Kernel32Func):
    name          = "GetCurrentThreadId"
    restype       = wintypes.DWORD
    null_is_error = False
    argtypes      = ()

class PostThreadMessageW(User32Func):
    name     = "PostThreadMessageW"
    restype  = wintypes.BOOL
    argtypes = (
        wintypes.DWORD,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )


# Singletons — import these directly
set_hook        = SetWindowsHookExW()
unhook          = UnhookWindowsHookEx()
next_hook       = CallNextHookEx()
get_message     = GetMessageW()
translate_msg   = TranslateMessage()
dispatch_msg    = DispatchMessageW()
get_thread_id   = GetCurrentThreadId()
post_thread_msg = PostThreadMessageW()
