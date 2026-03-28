"""Writers that can be used as hook callbacks."""

from __future__ import annotations

from pathlib import Path
import threading
from typing import Callable, TextIO

from .events import KeyEvent


class KeyWriter:
    """
    File writer callback for :class:`KeyEvent`.

    The instance is callable, so it can be attached directly:

    ``hook.listen(KeyWriter("keys.log"))``
    """

    def __init__(
        self,
        path: str | Path,
        *,
        mode: str = "a",
        encoding: str = "utf-8",
        flush: bool = True,
        formatter: Callable[[KeyEvent], str] | None = None,
    ):
        if "b" in mode:
            raise ValueError("Binary mode is not supported for KeyWriter")
        self.path = Path(path)
        self.mode = mode
        self.encoding = encoding
        self.flush = flush
        self.formatter = formatter or self.default_formatter

        self._file: TextIO | None = None
        self._lock = threading.Lock()

    @staticmethod
    def default_formatter(event: KeyEvent) -> str:
        """Format events as readable one-line log records."""
        action = "DOWN" if event.is_keydown else "UP" if event.is_keyup else f"WM_{event.w_param:#x}"
        return (
            f"time={event.time} "
            f"action={action} "
            f"vk={event.vk_code:#04x} "
            f"scan={event.scan_code} "
            f"flags={event.flags:#x}"
        )

    def open(self) -> KeyWriter:
        """Open the destination file if it is not already open."""
        with self._lock:
            if self._file is None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._file = self.path.open(self.mode, encoding=self.encoding)
        return self

    def close(self) -> None:
        """Close the destination file if it is open."""
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None

    def write(self, event: KeyEvent) -> None:
        """Write one event record."""
        line = self.formatter(event)
        if not line.endswith("\n"):
            line += "\n"
        with self._lock:
            if self._file is None:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self._file = self.path.open(self.mode, encoding=self.encoding)
            self._file.write(line)
            if self.flush:
                self._file.flush()

    def __call__(self, event: KeyEvent) -> None:
        """Allow the writer to be used directly as a hook callback."""
        self.write(event)

    def __enter__(self) -> KeyWriter:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
