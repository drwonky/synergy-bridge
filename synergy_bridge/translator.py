"""Translate Synergy coordinates into HID-friendly movements."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import List

from .synergy_client import MouseMoveEvent, ScreenTransitionEvent, SynergyEvent


@dataclass(frozen=True)
class AbsoluteCoordinateRange:
    """Absolute HID coordinate range."""

    min_x: int = 0
    min_y: int = 0
    max_x: int = 0x7FFF
    max_y: int = 0x7FFF


@dataclass(frozen=True)
class ScreenLayout:
    """Screen layout in the Synergy absolute coordinate space."""

    name: str
    x: int
    y: int
    width: int
    height: int

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def map_to_hid(self, x: int, y: int, *, hid_range: AbsoluteCoordinateRange) -> tuple[int, int]:
        rel_x = x - self.x
        rel_y = y - self.y
        scaled_x = _scale_axis(
            rel_x,
            0,
            max(1, self.width - 1),
            hid_range.min_x,
            hid_range.max_x,
        )
        scaled_y = _scale_axis(
            rel_y,
            0,
            max(1, self.height - 1),
            hid_range.min_y,
            hid_range.max_y,
        )
        return scaled_x, scaled_y


@dataclass(frozen=True)
class ScreenLayoutConfig:
    """Configuration describing screens and HID absolute ranges."""

    screens: List[ScreenLayout]
    hid_range: AbsoluteCoordinateRange = AbsoluteCoordinateRange()


@dataclass(frozen=True)
class HidPointerEvent:
    """Pointer movement ready for HID reports."""

    x: int
    y: int
    absolute: bool


class SynergyTranslator:
    """Translate Synergy input events into HID-ready movements."""

    def __init__(self, config: ScreenLayoutConfig, *, use_absolute: bool = True) -> None:
        if not config.screens:
            raise ValueError("At least one screen layout must be configured")
        self._config = config
        self._use_absolute = use_absolute
        self._current_screen: ScreenLayout | None = None
        self._last_position: tuple[int, int] | None = None

    def translate(self, event: SynergyEvent) -> List[SynergyEvent | HidPointerEvent]:
        if isinstance(event, MouseMoveEvent):
            return self.translate_mouse_move(event)
        return [event]

    def translate_mouse_move(self, event: MouseMoveEvent) -> List[SynergyEvent | HidPointerEvent]:
        events: List[SynergyEvent | HidPointerEvent] = []
        x, y = self._normalize_position(event)
        screen = self._find_screen(x, y)
        if screen is None:
            return events

        if screen != self._current_screen:
            if self._current_screen is not None:
                events.append(
                    ScreenTransitionEvent(screen=self._current_screen.name, entered=False)
                )
            events.append(ScreenTransitionEvent(screen=screen.name, entered=True))
            self._current_screen = screen

        if self._use_absolute:
            hid_x, hid_y = screen.map_to_hid(x, y, hid_range=self._config.hid_range)
            events.append(HidPointerEvent(x=hid_x, y=hid_y, absolute=True))
        else:
            dx, dy = self._calculate_relative_delta(x, y)
            events.append(HidPointerEvent(x=dx, y=dy, absolute=False))

        self._last_position = (x, y)
        return events

    def _normalize_position(self, event: MouseMoveEvent) -> tuple[int, int]:
        if event.absolute or self._last_position is None:
            return event.x, event.y
        last_x, last_y = self._last_position
        return last_x + event.x, last_y + event.y

    def _calculate_relative_delta(self, x: int, y: int) -> tuple[int, int]:
        if self._last_position is None:
            return 0, 0
        last_x, last_y = self._last_position
        return x - last_x, y - last_y

    def _find_screen(self, x: int, y: int) -> ScreenLayout | None:
        for screen in self._config.screens:
            if screen.contains(x, y):
                return screen
        return None


def load_layout_config(path: str | Path) -> ScreenLayoutConfig:
    """Load configuration from a JSON-compatible YAML file."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_layout_config(data)


def parse_layout_config(data: dict) -> ScreenLayoutConfig:
    """Parse a layout config dictionary into a ScreenLayoutConfig."""

    hid_config = data.get("hid", {})
    hid_range = AbsoluteCoordinateRange(
        min_x=hid_config.get("absolute_min_x", 0),
        min_y=hid_config.get("absolute_min_y", 0),
        max_x=hid_config.get("absolute_max_x", 0x7FFF),
        max_y=hid_config.get("absolute_max_y", 0x7FFF),
    )
    screens: List[ScreenLayout] = []
    for screen in data.get("screens", []):
        screens.append(
            ScreenLayout(
                name=screen["name"],
                x=screen["x"],
                y=screen["y"],
                width=screen["width"],
                height=screen["height"],
            )
        )
    return ScreenLayoutConfig(screens=screens, hid_range=hid_range)


def _scale_axis(
    value: int,
    source_min: int,
    source_max: int,
    target_min: int,
    target_max: int,
) -> int:
    if source_max == source_min:
        return target_min
    ratio = (value - source_min) / (source_max - source_min)
    scaled = target_min + ratio * (target_max - target_min)
    return max(min(int(round(scaled)), target_max), target_min)
