# keyboard_hook ⌨️🪝

![Tests](https://github.com/OWNER/REPO/actions/workflows/tests.yml/badge.svg)

Windows low-level keyboard hook library built on `ctypes` + Win32 LL keyboard hook APIs.

Because sometimes you need to know exactly which key was pressed, and when.  
And sometimes you just need to catch that one key that keeps ruining your day.

It provides three operation modes:
- `KeyboardHook`: blocking loop on the caller thread (old-school, direct, no nonsense)
- `ThreadedKeyboardHook` and `HotkeyHook`: non-blocking background thread (lets your app breathe)
- `ProcessKeyboardHook`: child-process isolation with hard-kill fallback (for when chaos is expected)

## Highlights ✨

- No runtime dependencies outside the Python standard library.
- Small, explicit API for key events and hotkey registration.
- Combo support (for example, `CTRL+SHIFT+S`) and configurable trigger modes.
- Supports graceful shutdown and forced termination (process mode).
- Designed for local desktop automation and hotkey-driven utilities.

## Platform and requirements 🪟

- OS: Windows only
- Python: 3.10+

If you run this on macOS/Linux, the README will still support you emotionally, but the hook will not.

## Installation 📦

### Local development install

```bash
python -m pip install -e .
```

### Local non-editable install

```bash
python -m pip install .
```

### PyPI install (after publish)

```bash
python -m pip install keyboard-hook
```

## Quickstart 🚀

Recommended entry point: `HotkeyHook`.

```python
from keyboard_hook import HotkeyHook, Key

hook = HotkeyHook()
hook.register(Key.ESCAPE, hook.stop)
hook.register(Key.A, lambda: print("A pressed"))
hook.register(Key.F5, lambda: print("F5 released"), on_keyup=True)
hook.register_combo("CTRL+SHIFT+S", lambda: print("Save!"), trigger="first_down")
hook.listen(lambda event: print(event))

with hook:
    hook.wait()
```

Run the included demo from repository root:

```bash
python keyboard_hook/example.py
```

## Usage 🛠️

### Class selection

| Class | Thread model | Process model | Typical usage |
|---|---|---|---|
| `KeyboardHook` | Calling thread | Same process | Full control over the message loop |
| `ThreadedKeyboardHook` | Background thread | Same process | Integrate into existing non-blocking app |
| `HotkeyHook` | Background thread | Same process | Register hotkeys with simple API |
| `ProcessKeyboardHook` | Background reader thread | Child process hook | Isolation and kill-on-failure safety |

### Lifecycle pattern

Use context managers for predictable setup/teardown:

```python
with hook:
    hook.wait()   # use hook.run() for KeyboardHook
```

Shutdown behavior:
- `stop`: graceful shutdown request
- `kill` (`ProcessKeyboardHook` only): force terminate child hook process

### Callback semantics

- `HotkeyHook.register` callbacks can take no args or one `KeyEvent`.
- `register` / `register_combo` callbacks may also accept one `KeyEvent` argument.
- `listen` callbacks receive a `KeyEvent` for every key event.
- `KeyboardHook` `on_key` can return `True` to suppress key propagation.

Suppress `A` on keydown:

```python
from keyboard_hook import KeyboardHook, KeyEvent

def on_key(event: KeyEvent) -> bool:
    if event.vk_code == ord("A") and event.is_keydown:
        return True
    return False

with KeyboardHook(on_key=on_key) as hook:
    hook.run()
```

### Key registration

Register keys by `Key` enum, VK name, or integer VK code:

```python
hook.register(Key.ESCAPE, callback)
hook.register(Key.SPACE, callback)
hook.register(Key.F5, callback)
hook.register(Key.A, callback)
hook.register(Key.NUM_1, callback)
hook.register("1", callback)     # VK name still supported
hook.register(0x1B, callback)
hook.register_combo("CTRL+SHIFT+S", callback)
```

Exports:
- `keyboard_hook.Key`
- `keyboard_hook.VK`
- `keyboard_hook.once`
- `keyboard_hook.keydown_only`
- `keyboard_hook.keyup_only`
- `keyboard_hook.throttle`
- `keyboard_hook.debounce`

### Trigger modes

You can control when callbacks fire:
- `down`: every keydown message (including repeats)
- `first_down`: first keydown only (no auto-repeat spam)
- `repeat`: key auto-repeat only
- `up`: on key release

```python
hook.register(Key.A, callback, trigger="first_down")
hook.register(Key.A, callback, trigger="repeat")
hook.register(Key.A, callback, trigger="up")
hook.register(Key.A, callback, on_keyup=True)  # alias for trigger="up"
```

### Callback decorators

Built-in decorators help keep hotkey callbacks clean:
- `@once`: run a callback only once
- `@keydown_only`: ignore non-keydown events
- `@keyup_only`: ignore non-keyup events
- `@throttle(seconds)`: limit execution rate
- `@debounce(seconds)`: execute once after input quiets down

```python
from keyboard_hook import HotkeyHook, Key, throttle, keydown_only

hook = HotkeyHook()

@throttle(0.2)
@keydown_only
def on_a(event):
    print("A keydown:", event.vk_code)

hook.register(Key.A, on_a, trigger="down")
```

### KeyEvent model

`KeyEvent` fields and helpers:
- `vk_code`
- `scan_code`
- `flags`
- `time`
- `is_keydown`
- `is_keyup`
- `is_injected`
- `is_extended`

## Testing ✅

Run tests from repository root:

```bash
python -m pytest -q
```

Example passing output:

```text
.........................                                                [100%]
25 passed in 0.16s
```

Green dots are good. Panic is optional.

## CI 🤖

Workflow file:
- `.github/workflows/tests.yml`

Pipeline behavior:
- Trigger: `push`, `pull_request`
- OS: `windows-latest`
- Python matrix: `3.10`, `3.11`, `3.12`, `3.13`

To activate the badge, replace `OWNER/REPO` in the badge URL with the real repository path.

## Packaging and release 📦🚢

Release checklist:
1. Update version in `pyproject.toml`.
2. Run tests locally and in CI.
3. Build source and wheel distributions.
4. Publish artifacts.

Build distributions:

```bash
python -m pip install build
python -m build
```

## License 📜

This project is released under the MIT License.

See [LICENSE](../LICENSE).

## Contributing 🤝

Contributions are welcome.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup, coding standards, and pull request guidance.

## Changelog 🗒️

Release history is tracked in [CHANGELOG.md](../CHANGELOG.md).

## Repository layout 🧭

```text
keyboard_hook/
  __init__.py
  constants.py
  winfunc.py
  bindings.py
  events.py
  hook.py
  threaded.py
  process.py
  example.py
tests/
  test_events.py
  test_constants_and_exports.py
LICENSE
CONTRIBUTING.md
CHANGELOG.md
```

## Operational notes ⚙️

- Keep callback functions short and non-blocking.
- Offload heavy work to worker threads/queues.
- Prefer `ProcessKeyboardHook` when callback code may fail unpredictably.

## Troubleshooting 🧯

- Hook fails to start: verify Windows platform and Python version.
- No events received: keep process alive inside `with hook` context.
- Shutdown hangs: call `stop` first; use `kill` for `ProcessKeyboardHook` fallback.
