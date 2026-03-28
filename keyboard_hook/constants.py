"""Win32 constants, virtual keys, and the :class:`Key` enum."""

from enum import IntEnum

WH_KEYBOARD_LL = 13

WM_QUIT       = 0x0012
WM_KEYDOWN    = 0x0100
WM_KEYUP      = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP   = 0x0105


class Key(IntEnum):
    """Named virtual-key codes for registration APIs (e.g. ``Key.ESCAPE``)."""

    ESCAPE    = 0x1B
    SPACE     = 0x20
    ENTER     = 0x0D
    TAB       = 0x09
    BACKSPACE = 0x08
    SHIFT     = 0x10
    CTRL      = 0x11
    ALT       = 0x12
    CAPS_LOCK = 0x14
    LEFT      = 0x25
    UP        = 0x26
    RIGHT     = 0x27
    DOWN      = 0x28

    A = 0x41
    B = 0x42
    C = 0x43
    D = 0x44
    E = 0x45
    F = 0x46
    G = 0x47
    H = 0x48
    I = 0x49
    J = 0x4A
    K = 0x4B
    L = 0x4C
    M = 0x4D
    N = 0x4E
    O = 0x4F
    P = 0x50
    Q = 0x51
    R = 0x52
    S = 0x53
    T = 0x54
    U = 0x55
    V = 0x56
    W = 0x57
    X = 0x58
    Y = 0x59
    Z = 0x5A

    # Leading digits are not valid Python identifiers, so use NUM_* names.
    NUM_0 = 0x30
    NUM_1 = 0x31
    NUM_2 = 0x32
    NUM_3 = 0x33
    NUM_4 = 0x34
    NUM_5 = 0x35
    NUM_6 = 0x36
    NUM_7 = 0x37
    NUM_8 = 0x38
    NUM_9 = 0x39

    F1  = 0x70
    F2  = 0x71
    F3  = 0x72
    F4  = 0x73
    F5  = 0x74
    F6  = 0x75
    F7  = 0x76
    F8  = 0x77
    F9  = 0x78
    F10 = 0x79
    F11 = 0x7A
    F12 = 0x7B


# Common virtual key codes used by registration APIs.
# This map preserves existing string-key behavior while adding enum-style names.
VK = {name: int(member) for name, member in Key.__members__.items()}
VK.update({str(n): int(Key[f"NUM_{n}"]) for n in range(10)})
