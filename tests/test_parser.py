from pathlib import Path
import base64

from synergy_bridge.synergy_client import (
    KeyEvent,
    MouseButtonEvent,
    MouseMoveEvent,
    ScreenTransitionEvent,
    SynergyProtocolParser,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> bytes:
    encoded = (FIXTURES / f"{name}.b64").read_text().strip()
    return base64.b64decode(encoded)


def test_mouse_move_absolute():
    data = load_fixture("mouse_move")
    parser = SynergyProtocolParser()
    events = parser.feed(data)
    assert events == [MouseMoveEvent(x=1024, y=768)]


def test_key_and_mouse_buttons():
    data = load_fixture("key_mouse")
    parser = SynergyProtocolParser()
    events = parser.feed(data)
    assert events == [
        KeyEvent(keycode=30, modifiers=2, pressed=True),
        KeyEvent(keycode=30, modifiers=2, pressed=False),
        MouseButtonEvent(button=1, pressed=True),
        MouseButtonEvent(button=1, pressed=False),
    ]


def test_screen_transition_events():
    data = load_fixture("screen_transition")
    parser = SynergyProtocolParser()
    events = parser.feed(data)
    assert events == [
        ScreenTransitionEvent(screen="primary", entered=True),
        ScreenTransitionEvent(screen="secondary", entered=False),
    ]


def test_partial_frames_across_chunks():
    data = load_fixture("mouse_move")
    parser = SynergyProtocolParser()
    first = parser.feed(data[:5])
    second = parser.feed(data[5:])
    assert first == []
    assert second == [MouseMoveEvent(x=1024, y=768)]
