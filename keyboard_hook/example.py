"""Manual examples for threaded and process-based keyboard hooks."""

import multiprocessing
import logging
from keyboard_hook import HotkeyHook, ProcessKeyboardHook, Key, KeyCombo, throttle, keydown_only

logging.basicConfig(level=logging.DEBUG)


def threaded_example():
    """Run a threaded hotkey demo until Escape is pressed."""
    hook = HotkeyHook()

    @hook.on_down(Key.A)
    @throttle(0.2)
    @keydown_only
    def on_a(event):
        print(f"A pressed (vk={event.vk_code:#x})")

    @hook.on_combo(KeyCombo("CTRL+SHIFT+S"))
    def on_save():
        print("Save combo!")

    (hook
        .register(Key.ESCAPE, hook.stop)
        .register(Key.S,      lambda: print("S pressed"))
        .register(Key.SPACE,  lambda: print("Space!"))
        .register(Key.A,      lambda: print("A repeat"), trigger="repeat")
        .listen(lambda e: print(f"  raw: {e}") if e.is_keydown else None)
    )
    print("Threaded hook — press Escape to quit")
    with hook:
        hook.wait()


def process_example():
    """Run a process-backed hotkey demo until Escape is pressed."""
    hook = ProcessKeyboardHook()

    @hook.on_down(Key.A)
    def on_a():
        print("A pressed")

    (hook
        .register(Key.ESCAPE, hook.stop)
        .register(Key.S,      lambda: print("S pressed"))
        .register_combo(KeyCombo(Key.CTRL, Key.SHIFT, "S"), lambda: print("Save combo!"))
        .listen(lambda e: print(f"  raw: {e}") if e.is_keydown else None)
    )
    print("Process hook — press Escape to quit")
    with hook:
        hook.wait()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    process_example()
