"""Utility decorators for hotkey callbacks."""

from __future__ import annotations

import inspect
import threading
import time
from functools import wraps
from typing import Any, Callable

from .events import KeyEvent


def _accepts_event(callback: Callable[..., Any]) -> bool:
    """Return ``True`` when ``callback`` can accept a positional event arg."""
    try:
        params = inspect.signature(callback).parameters.values()
    except (TypeError, ValueError):
        return False
    for param in params:
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            return True
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            return True
    return False


def _invoke(callback: Callable[..., Any], event: KeyEvent | None) -> Any:
    """Invoke ``callback`` while preserving no-arg callback compatibility."""
    if _accepts_event(callback):
        return callback(event)
    return callback()


def once(callback: Callable[..., Any]) -> Callable[[KeyEvent | None], Any | None]:
    """Run a callback only on its first invocation."""
    called = False
    lock = threading.Lock()

    @wraps(callback)
    def wrapper(event: KeyEvent | None = None) -> Any | None:
        nonlocal called
        with lock:
            if called:
                return None
            called = True
        return _invoke(callback, event)

    return wrapper


def keydown_only(callback: Callable[..., Any]) -> Callable[[KeyEvent | None], Any | None]:
    """Run callback only for key-down events."""

    @wraps(callback)
    def wrapper(event: KeyEvent | None = None) -> Any | None:
        if event is None or not event.is_keydown:
            return None
        return _invoke(callback, event)

    return wrapper


def keyup_only(callback: Callable[..., Any]) -> Callable[[KeyEvent | None], Any | None]:
    """Run callback only for key-up events."""

    @wraps(callback)
    def wrapper(event: KeyEvent | None = None) -> Any | None:
        if event is None or not event.is_keyup:
            return None
        return _invoke(callback, event)

    return wrapper


def throttle(seconds: float) -> Callable[[Callable[..., Any]], Callable[[KeyEvent | None], Any | None]]:
    """
    Limit callback execution to once per ``seconds`` interval.

    Calls received during the cooldown window are dropped.
    """
    if seconds <= 0:
        raise ValueError("seconds must be > 0")

    def decorator(callback: Callable[..., Any]) -> Callable[[KeyEvent | None], Any | None]:
        last_call = 0.0
        lock = threading.Lock()

        @wraps(callback)
        def wrapper(event: KeyEvent | None = None) -> Any | None:
            nonlocal last_call
            now = time.monotonic()
            with lock:
                if now - last_call < seconds:
                    return None
                last_call = now
            return _invoke(callback, event)

        return wrapper

    return decorator


def debounce(seconds: float) -> Callable[[Callable[..., Any]], Callable[[KeyEvent | None], None]]:
    """
    Delay callback until no new calls arrive for ``seconds``.

    Only the most recent event in the burst is delivered.
    """
    if seconds <= 0:
        raise ValueError("seconds must be > 0")

    def decorator(callback: Callable[..., Any]) -> Callable[[KeyEvent | None], None]:
        lock = threading.Lock()
        timer: threading.Timer | None = None
        latest_event: KeyEvent | None = None

        def fire():
            nonlocal timer
            with lock:
                event = latest_event
                timer = None
            _invoke(callback, event)

        @wraps(callback)
        def wrapper(event: KeyEvent | None = None) -> None:
            nonlocal timer, latest_event
            with lock:
                latest_event = event
                if timer is not None:
                    timer.cancel()
                timer = threading.Timer(seconds, fire)
                timer.daemon = True
                timer.start()

        return wrapper

    return decorator

