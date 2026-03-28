import ctypes

from keyboard_hook.constants import WM_KEYDOWN, WM_KEYUP
from keyboard_hook.events import KBDLLHOOKSTRUCT, KeyEvent


def test_keyevent_direction_properties():
    down = KeyEvent(WM_KEYDOWN, vk_code=0x41, scan_code=0x1E, flags=0, time=123)
    up = KeyEvent(WM_KEYUP, vk_code=0x41, scan_code=0x1E, flags=0, time=124)

    assert down.is_keydown is True
    assert down.is_keyup is False
    assert up.is_keydown is False
    assert up.is_keyup is True


def test_keyevent_flag_properties():
    injected_and_extended = KeyEvent(
        WM_KEYDOWN,
        vk_code=0x41,
        scan_code=0x1E,
        flags=0x10 | 0x01,
        time=123,
    )

    assert injected_and_extended.is_injected is True
    assert injected_and_extended.is_extended is True


def test_keyevent_repr_includes_state_and_codes():
    event = KeyEvent(WM_KEYDOWN, vk_code=0x41, scan_code=0x1E, flags=0, time=123)
    rendered = repr(event)

    assert "DOWN" in rendered
    assert "vk=0x41" in rendered
    assert "scan=30" in rendered


def test_from_lparam_reads_struct_contents():
    kb = KBDLLHOOKSTRUCT()
    kb.vkCode = 0x42
    kb.scanCode = 0x30
    kb.flags = 0x10
    kb.time = 999

    l_param = ctypes.addressof(kb)
    event = KeyEvent.from_lparam(WM_KEYDOWN, l_param)

    assert event.w_param == WM_KEYDOWN
    assert event.vk_code == 0x42
    assert event.scan_code == 0x30
    assert event.flags == 0x10
    assert event.time == 999