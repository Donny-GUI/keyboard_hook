"""Declarative helpers for defining Win32 ctypes function wrappers."""

import ctypes
import logging

logger = logging.getLogger(__name__)


class WinFunc:
    """
    Declarative base for Win32 API bindings.

    Subclass and set:
        lib          - ctypes DLL handle
        name         - function name string
        restype      - return type
        argtypes     - tuple of argument types
        null_is_error - raise WinError on NULL/0 result (default True)
        log_calls    - debug-log every call (default False)
    """
    lib           = None
    name          = None
    restype       = None
    argtypes      = ()
    null_is_error = True
    log_calls     = False

    def __init_subclass__(cls, **kwargs):
        """Bind subclass metadata to the underlying DLL function object."""
        super().__init_subclass__(**kwargs)
        if cls.lib is None or cls.name is None:
            return
        fn              = getattr(cls.lib, cls.name)
        fn.restype      = cls.restype
        fn.argtypes     = cls.argtypes
        fn.errcheck     = cls._errcheck
        cls._fn         = fn

    @classmethod
    def _errcheck(cls, result, func, args):
        """Apply optional call logging and default Win32 error handling."""
        if cls.log_calls:
            logger.debug("%s%s -> %r", cls.name, args, result)
        if cls.null_is_error and not result:
            raise ctypes.WinError()
        return result

    def __call__(self, *args):
        """Invoke the underlying ctypes function."""
        return self._fn(*args)

    def __repr__(self):
        return f"<WinFunc {self.name}>"


class User32Func(WinFunc):
    """Base class for functions resolved from ``user32.dll``."""
    lib = ctypes.windll.user32


class Kernel32Func(WinFunc):
    """Base class for functions resolved from ``kernel32.dll``."""
    lib = ctypes.windll.kernel32
