import multiprocessing
import logging
from keyboard_hook import HotkeyHook, ProcessKeyboardHook, VK

logging.basicConfig(level=logging.DEBUG)


def threaded_example():
    hook = HotkeyHook()
    (hook
        .register("ESCAPE", hook.stop)
        .register("A",      lambda: print("A pressed"))
        .register("S",      lambda: print("S pressed"))
        .register("SPACE",  lambda: print("Space!"))
        .listen(lambda e: print(f"  raw: {e}") if e.is_keydown else None)
    )
    print("Threaded hook — press Escape to quit")
    with hook:
        hook.wait()


def process_example():
    hook = ProcessKeyboardHook()
    (hook
        .register("ESCAPE", hook.stop)
        .register("A",      lambda: print("A pressed"))
        .register("S",      lambda: print("S pressed"))
        .listen(lambda e: print(f"  raw: {e}") if e.is_keydown else None)
    )
    print("Process hook — press Escape to quit")
    with hook:
        hook.wait()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    process_example()
