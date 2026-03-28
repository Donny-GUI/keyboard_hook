# keyboard_hook

![Tests](https://github.com/OWNER/REPO/actions/workflows/tests.yml/badge.svg)

Windows low-level keyboard hook library built on ctypes and the Win32 LL keyboard hook API.

It provides three operation modes:
- KeyboardHook: blocking loop on the caller thread
- ThreadedKeyboardHook and HotkeyHook: non-blocking background thread
- ProcessKeyboardHook: child-process isolation with hard-kill fallback

## Highlights

- No runtime dependencies outside the Python standard library.
- Small, explicit API for key events and hotkey registration.
- Supports graceful shutdown and forced termination (process mode).
- Designed for local desktop automation and hotkey-driven utilities.

## Platform and requirements

- OS: Windows only
- Python: 3.10+

## Installation

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

## Quickstart

Recommended entry point: HotkeyHook.

```python
from keyboard_hook import HotkeyHook

hook = HotkeyHook()
hook.register("ESCAPE", hook.stop)
hook.register("A", lambda: print("A pressed"))
hook.register("F5", lambda: print("F5 released"), on_keyup=True)
hook.listen(lambda event: print(event))

with hook:
    hook.wait()
```

Run the included demo from repository root:

```bash
python keyboard_hook/example.py
```

## Usage

### Class selection

| Class | Thread model | Process model | Typical usage |
|---|---|---|---|
| KeyboardHook | Calling thread | Same process | Full control over the message loop |
| ThreadedKeyboardHook | Background thread | Same process | Integrate into existing non-blocking app |
| HotkeyHook | Background thread | Same process | Register hotkeys with simple API |
| ProcessKeyboardHook | Background reader thread | Child process hook | Isolation and kill-on-failure safety |

### Lifecycle pattern

Use context managers for predictable setup/teardown:

```python
with hook:
    hook.wait()   # use hook.run() for KeyboardHook
```

Shutdown behavior:
- stop: graceful shutdown request
- kill (ProcessKeyboardHook only): force terminate child hook process

### Callback semantics

- HotkeyHook.register callbacks take no arguments.
- listen callbacks receive a KeyEvent for every key event.
- KeyboardHook on_key can return True to suppress key propagation.

Suppress A on keydown:

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

Register keys by VK name or integer VK code:

```python
hook.register("ESCAPE", callback)
hook.register("SPACE", callback)
hook.register("F5", callback)
hook.register("A", callback)
hook.register("1", callback)
hook.register(0x1B, callback)
```

Key map export:
- keyboard_hook.VK

### KeyEvent model

KeyEvent fields and helpers:
- vk_code
- scan_code
- flags
- time
- is_keydown
- is_keyup
- is_injected
- is_extended

## Testing

Run tests from repository root:

```bash
python -m pytest -q
```

Example passing output:

```text
.......                                                                  [100%]
7 passed in 0.10s
```

## CI

Workflow file:
- .github/workflows/tests.yml

Pipeline behavior:
- Trigger: push, pull_request
- OS: windows-latest
- Python matrix: 3.10, 3.11, 3.12, 3.13

To activate the badge, replace OWNER/REPO in the badge URL with the real repository path.

## Packaging and release

Release checklist:
1. Update version in pyproject.toml.
2. Run tests locally and in CI.
3. Build source and wheel distributions.
4. Publish artifacts.

Build distributions:

```bash
python -m pip install build
python -m build
```

## License

This project is released under the MIT License.

See [LICENSE](../LICENSE).

## Contributing

Contributions are welcome.

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup, coding standards, and pull request guidance.

## Changelog

Release history is tracked in [CHANGELOG.md](../CHANGELOG.md).

## Repository layout

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

## Operational notes

- Keep callback functions short and non-blocking.
- Offload heavy work to worker threads/queues.
- Prefer ProcessKeyboardHook when callback code may fail unpredictably.

## Troubleshooting

- Hook fails to start: verify Windows platform and Python version.
- No events received: keep process alive inside with hook context.
- Shutdown hangs: call stop first; use kill for ProcessKeyboardHook fallback.
