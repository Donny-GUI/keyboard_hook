import keyboard_hook
from keyboard_hook.constants import VK


def test_vk_contains_common_keys():
    assert VK["ESCAPE"] == 0x1B
    assert VK["SPACE"] == 0x20
    assert VK["ENTER"] == 0x0D
    assert VK["A"] == ord("A")
    assert VK["0"] == 0x30
    assert VK["F1"] == 0x70
    assert VK["F12"] == 0x7B


def test_package_public_exports_present():
    expected = {
        "KeyboardHook",
        "ThreadedKeyboardHook",
        "HotkeyHook",
        "ProcessKeyboardHook",
        "KeyEvent",
        "VK",
    }
    assert expected.issubset(set(keyboard_hook.__all__))


def test_exported_vk_matches_constants_vk():
    assert keyboard_hook.VK is VK