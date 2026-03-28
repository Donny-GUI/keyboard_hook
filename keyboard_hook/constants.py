WH_KEYBOARD_LL = 13

WM_QUIT       = 0x0012
WM_KEYDOWN    = 0x0100
WM_KEYUP      = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP   = 0x0105

# Common virtual key codes
VK = {
    "ESCAPE"    : 0x1B,
    "SPACE"     : 0x20,
    "ENTER"     : 0x0D,
    "TAB"       : 0x09,
    "BACKSPACE" : 0x08,
    "SHIFT"     : 0x10,
    "CTRL"      : 0x11,
    "ALT"       : 0x12,
    "CAPS_LOCK" : 0x14,
    "LEFT"      : 0x25,
    "UP"        : 0x26,
    "RIGHT"     : 0x27,
    "DOWN"      : 0x28,
    **{chr(c): c for c in range(ord("A"), ord("Z") + 1)},  # A-Z
    **{str(n): 0x30 + n for n in range(10)},               # 0-9
    **{f"F{n}": 0x6F + n for n in range(1, 13)},           # F1-F12
}
