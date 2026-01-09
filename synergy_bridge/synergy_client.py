"""Synergy protocol client and event parser."""

from __future__ import annotations

from dataclasses import dataclass
import socket
from typing import Callable, Iterator, List, Optional


@dataclass(frozen=True)
class MouseMoveEvent:
    """Absolute mouse movement event."""

    x: int
    y: int
    absolute: bool = True


@dataclass(frozen=True)
class MouseButtonEvent:
    """Mouse button press/release event."""

    button: int
    pressed: bool


@dataclass(frozen=True)
class KeyEvent:
    """Keyboard press/release event."""

    keycode: int
    modifiers: int
    pressed: bool


@dataclass(frozen=True)
class ScreenTransitionEvent:
    """Screen boundary transition event."""

    screen: str
    entered: bool


SynergyEvent = MouseMoveEvent | MouseButtonEvent | KeyEvent | ScreenTransitionEvent


class SynergyProtocolParser:
    """Parse Synergy protocol frames into normalized events."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> List[SynergyEvent]:
        """Feed raw bytes and return any parsed events."""

        self._buffer.extend(data)
        events: List[SynergyEvent] = []

        while True:
            if len(self._buffer) < 4:
                break
            length = int.from_bytes(self._buffer[:4], "big")
            if len(self._buffer) < 4 + length:
                break
            payload = bytes(self._buffer[4 : 4 + length])
            del self._buffer[: 4 + length]
            event = self._parse_payload(payload)
            if event is not None:
                events.append(event)
        return events

    def _parse_payload(self, payload: bytes) -> Optional[SynergyEvent]:
        text = payload.decode("utf-8")
        parts = text.split()
        if not parts:
            return None
        message = parts[0]
        if message == "DMMV" and len(parts) == 3:
            return MouseMoveEvent(x=int(parts[1]), y=int(parts[2]))
        if message == "DMMB" and len(parts) == 3:
            return MouseButtonEvent(button=int(parts[1]), pressed=parts[2] == "1")
        if message == "DKDN" and len(parts) == 3:
            return KeyEvent(keycode=int(parts[1]), modifiers=int(parts[2]), pressed=True)
        if message == "DKUP" and len(parts) == 3:
            return KeyEvent(keycode=int(parts[1]), modifiers=int(parts[2]), pressed=False)
        if message == "CINN" and len(parts) == 2:
            return ScreenTransitionEvent(screen=parts[1], entered=True)
        if message == "COUT" and len(parts) == 2:
            return ScreenTransitionEvent(screen=parts[1], entered=False)
        return None


class SynergyClient:
    """Synergy protocol client for streaming input events."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._parser = SynergyProtocolParser()

    def connect(self) -> None:
        """Open a TCP connection to the Synergy server."""

        self._socket = socket.create_connection((self._host, self._port))

    def close(self) -> None:
        """Close the socket if open."""

        if self._socket is not None:
            self._socket.close()
        self._socket = None

    def iter_events(self, *, chunk_size: int = 4096) -> Iterator[SynergyEvent]:
        """Yield events parsed from the socket stream."""

        if self._socket is None:
            raise RuntimeError("SynergyClient.connect must be called before iterating")
        while True:
            data = self._socket.recv(chunk_size)
            if not data:
                break
            for event in self._parser.feed(data):
                yield event

    def stream_events(
        self,
        callback: Callable[[SynergyEvent], None],
        *,
        chunk_size: int = 4096,
    ) -> None:
        """Stream events and invoke a callback for each event."""

        for event in self.iter_events(chunk_size=chunk_size):
            callback(event)
