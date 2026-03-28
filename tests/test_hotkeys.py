import pytest

from keyboard_hook.constants import Key, KeyCombo, WM_KEYDOWN, WM_KEYUP
from keyboard_hook.events import KeyEvent
from keyboard_hook.process import ProcessKeyboardHook
from keyboard_hook.threaded import HotkeyHook


def _event(w_param: int, key: Key) -> KeyEvent:
    return KeyEvent(
        w_param=w_param,
        vk_code=int(key),
        scan_code=0,
        flags=0,
        time=0,
    )


@pytest.mark.parametrize("hook_type", [HotkeyHook, ProcessKeyboardHook])
def test_register_callback_can_accept_event(hook_type):
    hook = hook_type()
    seen = []

    hook.register(Key.A, lambda event: seen.append(event.vk_code), trigger="first_down")
    hook._dispatch(_event(WM_KEYDOWN, Key.A))

    assert seen == [int(Key.A)]


@pytest.mark.parametrize("hook_type", [HotkeyHook, ProcessKeyboardHook])
def test_trigger_modes_down_first_down_repeat_up(hook_type):
    hook = hook_type()
    counts = {"down": 0, "first_down": 0, "repeat": 0, "up": 0}

    hook.register(Key.A, lambda: counts.__setitem__("down", counts["down"] + 1), trigger="down")
    hook.register(Key.A, lambda: counts.__setitem__("first_down", counts["first_down"] + 1), trigger="first_down")
    hook.register(Key.A, lambda: counts.__setitem__("repeat", counts["repeat"] + 1), trigger="repeat")
    hook.register(Key.A, lambda: counts.__setitem__("up", counts["up"] + 1), on_keyup=True)

    hook._dispatch(_event(WM_KEYDOWN, Key.A))  # first down
    hook._dispatch(_event(WM_KEYDOWN, Key.A))  # repeat down
    hook._dispatch(_event(WM_KEYUP, Key.A))    # up

    assert counts == {
        "down": 2,
        "first_down": 1,
        "repeat": 1,
        "up": 1,
    }


@pytest.mark.parametrize("hook_type", [HotkeyHook, ProcessKeyboardHook])
def test_register_combo_string_and_iterable(hook_type):
    hook = hook_type()
    fired = []
    fired_event_vk = []

    hook.register_combo("CTRL+SHIFT+S", lambda: fired.append("save"), trigger="first_down")
    hook.register_combo(
        [Key.CTRL, Key.SHIFT, Key.A],
        lambda event: fired_event_vk.append(event.vk_code),
        trigger="first_down",
    )

    hook._dispatch(_event(WM_KEYDOWN, Key.CTRL))
    hook._dispatch(_event(WM_KEYDOWN, Key.SHIFT))
    hook._dispatch(_event(WM_KEYDOWN, Key.S))
    hook._dispatch(_event(WM_KEYDOWN, Key.A))

    assert fired == ["save"]
    assert fired_event_vk == [int(Key.A)]


@pytest.mark.parametrize("hook_type", [HotkeyHook, ProcessKeyboardHook])
def test_unregister_combo_removes_binding(hook_type):
    hook = hook_type()
    fired = []

    hook.register_combo("CTRL+S", lambda: fired.append("x"))
    hook.unregister_combo("CTRL+S")

    hook._dispatch(_event(WM_KEYDOWN, Key.CTRL))
    hook._dispatch(_event(WM_KEYDOWN, Key.S))

    assert fired == []


@pytest.mark.parametrize("hook_type", [HotkeyHook, ProcessKeyboardHook])
def test_on_down_decorator_registers_callback(hook_type):
    hook = hook_type()
    seen = []

    @hook.on_down(Key.A)
    def on_a(event):
        seen.append(event.vk_code)

    hook._dispatch(_event(WM_KEYDOWN, Key.A))

    assert seen == [int(Key.A)]


@pytest.mark.parametrize("hook_type", [HotkeyHook, ProcessKeyboardHook])
def test_on_combo_decorator_registers_callback(hook_type):
    hook = hook_type()
    fired = []

    @hook.on_combo("CTRL+S", trigger="first_down")
    def on_save():
        fired.append("save")

    hook._dispatch(_event(WM_KEYDOWN, Key.CTRL))
    hook._dispatch(_event(WM_KEYDOWN, Key.S))

    assert fired == ["save"]


@pytest.mark.parametrize("hook_type", [HotkeyHook, ProcessKeyboardHook])
def test_on_combo_decorator_accepts_list_and_tuple_of_key_or_string(hook_type):
    hook = hook_type()
    fired = []

    @hook.on_combo([Key.CTRL, "S"], trigger="first_down")
    def on_save_list():
        fired.append("list")

    @hook.on_combo((Key.CTRL, "A"), trigger="first_down")
    def on_a_tuple():
        fired.append("tuple")

    hook._dispatch(_event(WM_KEYDOWN, Key.CTRL))
    hook._dispatch(_event(WM_KEYDOWN, Key.S))
    hook._dispatch(_event(WM_KEYDOWN, Key.A))

    assert fired == ["list", "tuple"]


@pytest.mark.parametrize("hook_type", [HotkeyHook, ProcessKeyboardHook])
def test_on_combo_decorator_accepts_keycombo(hook_type):
    hook = hook_type()
    fired = []

    @hook.on_combo(KeyCombo(Key.CTRL, "S"))
    def on_save():
        fired.append("combo")

    hook._dispatch(_event(WM_KEYDOWN, Key.CTRL))
    hook._dispatch(_event(WM_KEYDOWN, Key.S))

    assert fired == ["combo"]


@pytest.mark.parametrize("hook_type", [HotkeyHook, ProcessKeyboardHook])
def test_on_event_decorator_registers_listener(hook_type):
    hook = hook_type()
    seen = []

    @hook.on_event()
    def on_event(event):
        seen.append(event.vk_code)

    hook._dispatch(_event(WM_KEYDOWN, Key.A))

    assert seen == [int(Key.A)]
