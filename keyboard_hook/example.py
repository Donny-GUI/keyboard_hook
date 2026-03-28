"""Manual examples for threaded and process-based keyboard hooks."""

import multiprocessing
import logging
from keyboard_hook import HotkeyHook, ProcessKeyboardHook, Key, throttle, keydown_only

logging.basicConfig(level=logging.DEBUG)


def threaded_example():
    """Run a threaded hotkey demo until Escape is pressed."""
    @throttle(0.2)
    @keydown_only
    def on_a(event):
        print(f"A pressed (vk={event.vk_code:#x})")

    hook = HotkeyHook()
    (hook
        .register(Key.ESCAPE, hook.stop)
        .register(Key.A,      on_a, trigger="down")
        .register(Key.S,      lambda: print("S pressed"))
        .register(Key.SPACE,  lambda: print("Space!"))
        .register(Key.A,      lambda: print("A repeat"), trigger="repeat")
        .register_combo("CTRL+SHIFT+S", lambda: print("Save combo!"), trigger="first_down")
        .listen(lambda e: print(f"  raw: {e}") if e.is_keydown else None)
    )
    print("Threaded hook — press Escape to quit")
    with hook:
        hook.wait()


def process_example():
    """Run a process-backed hotkey demo until Escape is pressed."""
    hook = ProcessKeyboardHook()
    (hook
        .register(Key.ESCAPE, hook.stop)
        .register(Key.A,      lambda: print("A pressed"))
        .register(Key.S,      lambda: print("S pressed"))
        .register_combo([Key.CTRL, Key.SHIFT, Key.S], lambda: print("Save combo!"))
        .listen(lambda e: print(f"  raw: {e}") if e.is_keydown else None)
    )
    print("Process hook — press Escape to quit")
    with hook:
        hook.wait()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    process_example()
