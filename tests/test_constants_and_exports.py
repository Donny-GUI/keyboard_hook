import keyboard_hook
from keyboard_hook.constants import Key, VK
from keyboard_hook.process import ProcessKeyboardHook
from keyboard_hook.threaded import HotkeyHook


def test_vk_contains_common_keys():
    assert VK["ESCAPE"] == 0x1B
    assert VK["SPACE"] == 0x20
    assert VK["ENTER"] == 0x0D
    assert VK["A"] == ord("A")
    assert VK["0"] == 0x30
    assert VK["F1"] == 0x70
    assert VK["F12"] == 0x7B


def test_key_enum_contains_common_keys():
    assert int(Key.ESCAPE) == 0x1B
    assert int(Key.SPACE) == 0x20
    assert int(Key.ENTER) == 0x0D
    assert int(Key.A) == ord("A")
    assert int(Key.NUM_0) == 0x30
    assert int(Key.F1) == 0x70
    assert int(Key.F12) == 0x7B


def test_package_public_exports_present():
    expected = {
        "KeyboardHook",
        "ThreadedKeyboardHook",
        "HotkeyHook",
        "ProcessKeyboardHook",
        "KeyEvent",
        "Key",
        "VK",
    }
    assert expected.issubset(set(keyboard_hook.__all__))


def test_exported_vk_matches_constants_vk():
    assert keyboard_hook.VK is VK


def test_exported_key_matches_constants_key():
    assert keyboard_hook.Key is Key


def test_hotkey_hook_resolve_accepts_key_enum():
    assert HotkeyHook._resolve(Key.ESCAPE) == 0x1B


def test_process_hook_resolve_accepts_key_enum():
    assert ProcessKeyboardHook._resolve(Key.F5) == 0x74
