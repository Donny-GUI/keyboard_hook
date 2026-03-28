from pathlib import Path

from keyboard_hook.constants import WM_KEYDOWN
from keyboard_hook.events import KeyEvent
from keyboard_hook.writer import KeyWriter


def _event(vk: int = 0x41) -> KeyEvent:
    return KeyEvent(
        w_param=WM_KEYDOWN,
        vk_code=vk,
        scan_code=0x1E,
        flags=0,
        time=123,
    )


def test_keywriter_default_formatter_contains_basic_fields():
    line = KeyWriter.default_formatter(_event())
    assert "time=123" in line
    assert "action=DOWN" in line
    assert "vk=0x41" in line


def test_keywriter_callable_writes_one_line(tmp_path: Path):
    out = tmp_path / "keys.log"
    writer = KeyWriter(out)

    writer(_event())
    writer.close()

    content = out.read_text(encoding="utf-8")
    assert content.count("\n") == 1
    assert "vk=0x41" in content


def test_keywriter_context_manager_closes_file(tmp_path: Path):
    out = tmp_path / "keys.log"
    with KeyWriter(out, flush=True) as writer:
        writer.write(_event(vk=0x42))

    content = out.read_text(encoding="utf-8")
    assert "vk=0x42" in content
    assert writer._file is None

