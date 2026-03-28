from __future__ import annotations
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from .constants import WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP


class KBDLLHOOKSTRUCT(ctypes.Structure):
    """Raw Win32 struct passed via lParam in the hook callback."""
    _fields_ = [
        ("vkCode",      wintypes.DWORD),
        ("scanCode",    wintypes.DWORD),
        ("flags",       wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


@dataclass(frozen=True, slots=True)
class KeyEvent:
    """
    Immutable, serializable key event.
    Safe to send over a multiprocessing Pipe.
    """
    w_param   : int
    vk_code   : int
    scan_code : int
    flags     : int
    time      : int

    @classmethod
    def from_lparam(cls, w_param: int, l_param: int) -> KeyEvent:
        kb = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        return cls(
            w_param   = w_param,
            vk_code   = kb.vkCode,
            scan_code = kb.scanCode,
            flags     = kb.flags,
            time      = kb.time,
        )

    @property
    def is_keydown(self) -> bool:
        return self.w_param in (WM_KEYDOWN, WM_SYSKEYDOWN)

    @property
    def is_keyup(self) -> bool:
        return self.w_param in (WM_KEYUP, WM_SYSKEYUP)

    @property
    def is_injected(self) -> bool:
        """True if the event was injected by software (not a real keypress)."""
        return bool(self.flags & 0x10)

    @property
    def is_extended(self) -> bool:
        """True for extended keys (numpad, arrows, etc.)."""
        return bool(self.flags & 0x01)

    def __repr__(self):
        action = "DOWN" if self.is_keydown else "UP"
        return f"<KeyEvent {action} vk={self.vk_code:#04x} scan={self.scan_code}>"


# --- Callback types ---

# Return True to suppress the key, False to pass through
KeyCallback  = callable   # (KeyEvent) -> bool | None
HookCallback = callable   # (KeyEvent) -> None  (for raw listeners)
