"""HID gadget report builders and device writers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

KEYBOARD_REPORT_ID = 1
MOUSE_REPORT_ID = 2
ABSOLUTE_MOUSE_REPORT_ID = 3

HID_REPORT_DESCRIPTORS: dict[str, bytes] = {
    "keyboard": bytes(
        [
            0x05,
            0x01,
            0x09,
            0x06,
            0xA1,
            0x01,
            0x85,
            KEYBOARD_REPORT_ID,
            0x05,
            0x07,
            0x19,
            0xE0,
            0x29,
            0xE7,
            0x15,
            0x00,
            0x25,
            0x01,
            0x75,
            0x01,
            0x95,
            0x08,
            0x81,
            0x02,
            0x95,
            0x01,
            0x75,
            0x08,
            0x81,
            0x03,
            0x95,
            0x06,
            0x75,
            0x08,
            0x15,
            0x00,
            0x25,
            0x65,
            0x05,
            0x07,
            0x19,
            0x00,
            0x29,
            0x65,
            0x81,
            0x00,
            0xC0,
        ]
    ),
    "mouse_relative": bytes(
        [
            0x05,
            0x01,
            0x09,
            0x02,
            0xA1,
            0x01,
            0x85,
            MOUSE_REPORT_ID,
            0x09,
            0x01,
            0xA1,
            0x00,
            0x05,
            0x09,
            0x19,
            0x01,
            0x29,
            0x03,
            0x15,
            0x00,
            0x25,
            0x01,
            0x95,
            0x03,
            0x75,
            0x01,
            0x81,
            0x02,
            0x95,
            0x01,
            0x75,
            0x05,
            0x81,
            0x03,
            0x05,
            0x01,
            0x09,
            0x30,
            0x09,
            0x31,
            0x09,
            0x38,
            0x15,
            0x81,
            0x25,
            0x7F,
            0x75,
            0x08,
            0x95,
            0x03,
            0x81,
            0x06,
            0xC0,
            0xC0,
        ]
    ),
    "mouse_absolute": bytes(
        [
            0x05,
            0x01,
            0x09,
            0x02,
            0xA1,
            0x01,
            0x85,
            ABSOLUTE_MOUSE_REPORT_ID,
            0x09,
            0x01,
            0xA1,
            0x00,
            0x05,
            0x09,
            0x19,
            0x01,
            0x29,
            0x03,
            0x15,
            0x00,
            0x25,
            0x01,
            0x95,
            0x03,
            0x75,
            0x01,
            0x81,
            0x02,
            0x95,
            0x01,
            0x75,
            0x05,
            0x81,
            0x03,
            0x05,
            0x01,
            0x09,
            0x30,
            0x09,
            0x31,
            0x16,
            0x00,
            0x00,
            0x26,
            0xFF,
            0x7F,
            0x75,
            0x10,
            0x95,
            0x02,
            0x81,
            0x02,
            0xC0,
            0xC0,
        ]
    ),
}


@dataclass(frozen=True)
class HidDevicePaths:
    """Configured gadget device paths for each report type."""

    keyboard: str = "/dev/hidg0"
    mouse: str = "/dev/hidg1"
    absolute_mouse: str = "/dev/hidg2"


@dataclass(frozen=True)
class HidMouseConfig:
    """Mouse input configuration based on host capability."""

    absolute_enabled: bool = True
    absolute_max_x: int = 0x7FFF
    absolute_max_y: int = 0x7FFF


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _to_signed_byte(value: int) -> int:
    clamped = _clamp(value, -127, 127)
    return clamped & 0xFF


def build_keyboard_report(modifiers: int, keys: Iterable[int]) -> bytes:
    """Build an 8-byte keyboard report with the configured report ID."""

    key_list = list(keys)
    if len(key_list) > 6:
        raise ValueError("Keyboard reports support at most six keys")
    padded = key_list + [0] * (6 - len(key_list))
    return bytes([KEYBOARD_REPORT_ID, modifiers & 0xFF, 0x00, *padded])


def build_mouse_report(buttons: int, x: int, y: int, wheel: int = 0) -> bytes:
    """Build a relative mouse report with X/Y deltas."""

    return bytes(
        [
            MOUSE_REPORT_ID,
            buttons & 0xFF,
            _to_signed_byte(x),
            _to_signed_byte(y),
            _to_signed_byte(wheel),
        ]
    )


def build_absolute_mouse_report(
    buttons: int,
    x: int,
    y: int,
    *,
    max_x: int = 0x7FFF,
    max_y: int = 0x7FFF,
) -> bytes:
    """Build an absolute mouse report with 16-bit coordinates."""

    clamped_x = _clamp(x, 0, max_x)
    clamped_y = _clamp(y, 0, max_y)
    return bytes([ABSOLUTE_MOUSE_REPORT_ID, buttons & 0xFF]) + clamped_x.to_bytes(
        2, "little"
    ) + clamped_y.to_bytes(2, "little")


class HidGadget:
    """Write HID reports to gadget devices."""

    def __init__(
        self,
        *,
        paths: HidDevicePaths | None = None,
        mouse_config: HidMouseConfig | None = None,
    ) -> None:
        self._paths = paths or HidDevicePaths()
        self._mouse_config = mouse_config or HidMouseConfig()

    @property
    def mouse_config(self) -> HidMouseConfig:
        return self._mouse_config

    def write_keyboard(self, modifiers: int, keys: Iterable[int]) -> None:
        report = build_keyboard_report(modifiers, keys)
        self._write_report(self._paths.keyboard, report)

    def write_mouse(
        self,
        *,
        buttons: int,
        x: int,
        y: int,
        wheel: int = 0,
        absolute: bool = False,
    ) -> None:
        if absolute and self._mouse_config.absolute_enabled:
            report = build_absolute_mouse_report(
                buttons,
                x,
                y,
                max_x=self._mouse_config.absolute_max_x,
                max_y=self._mouse_config.absolute_max_y,
            )
            path = self._paths.absolute_mouse
        else:
            report = build_mouse_report(buttons, x, y, wheel)
            path = self._paths.mouse
        self._write_report(path, report)

    @staticmethod
    def _write_report(path: str, report: bytes) -> None:
        with open(path, "ab") as device:
            device.write(report)
