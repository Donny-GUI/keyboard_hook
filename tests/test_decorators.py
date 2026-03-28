import time

from keyboard_hook import debounce, keydown_only, keyup_only, once, throttle
from keyboard_hook.constants import Key, WM_KEYDOWN, WM_KEYUP
from keyboard_hook.events import KeyEvent


def _event(w_param: int, key: Key) -> KeyEvent:
    return KeyEvent(
        w_param=w_param,
        vk_code=int(key),
        scan_code=0,
        flags=0,
        time=0,
    )


def test_once_runs_only_once_for_noarg_callback():
    calls = []

    @once
    def cb():
        calls.append("x")

    cb()
    cb()
    cb()

    assert calls == ["x"]


def test_once_runs_only_once_for_event_callback():
    seen = []

    @once
    def cb(event):
        seen.append(event.vk_code)

    cb(_event(WM_KEYDOWN, Key.A))
    cb(_event(WM_KEYDOWN, Key.B))

    assert seen == [int(Key.A)]


def test_keydown_only_filters_to_keydown():
    seen = []

    @keydown_only
    def cb(event):
        seen.append(event.vk_code)

    cb(_event(WM_KEYUP, Key.A))
    cb(_event(WM_KEYDOWN, Key.A))

    assert seen == [int(Key.A)]


def test_keyup_only_filters_to_keyup():
    seen = []

    @keyup_only
    def cb(event):
        seen.append(event.vk_code)

    cb(_event(WM_KEYDOWN, Key.A))
    cb(_event(WM_KEYUP, Key.A))

    assert seen == [int(Key.A)]


def test_throttle_limits_execution_rate():
    calls = []

    @throttle(0.03)
    def cb():
        calls.append(time.monotonic())

    cb()
    cb()
    time.sleep(0.04)
    cb()

    assert len(calls) == 2


def test_debounce_keeps_only_latest_event():
    seen = []

    @debounce(0.02)
    def cb(event):
        seen.append(event.vk_code)

    cb(_event(WM_KEYDOWN, Key.A))
    time.sleep(0.01)
    cb(_event(WM_KEYDOWN, Key.B))
    time.sleep(0.05)

    assert seen == [int(Key.B)]
