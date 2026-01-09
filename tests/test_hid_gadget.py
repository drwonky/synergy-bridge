from pathlib import Path

import pytest

from synergy_bridge.hid_gadget import (
    ABSOLUTE_MOUSE_REPORT_ID,
    KEYBOARD_REPORT_ID,
    MOUSE_REPORT_ID,
    HidDevicePaths,
    HidGadget,
    HidMouseConfig,
    build_absolute_mouse_report,
    build_keyboard_report,
    build_mouse_report,
)


def test_build_keyboard_report_formats_bytes():
    report = build_keyboard_report(0x02, [4, 5])
    assert report == bytes([KEYBOARD_REPORT_ID, 0x02, 0x00, 4, 5, 0, 0, 0, 0])


def test_build_keyboard_report_rejects_too_many_keys():
    with pytest.raises(ValueError):
        build_keyboard_report(0, [1, 2, 3, 4, 5, 6, 7])


def test_build_mouse_report_clamps_to_signed_bytes():
    report = build_mouse_report(0x01, 200, -200, 130)
    assert report == bytes([MOUSE_REPORT_ID, 0x01, 0x7F, 0x81, 0x7F])


def test_build_absolute_mouse_report_clamps_to_max():
    report = build_absolute_mouse_report(0x02, 40000, -5, max_x=30000, max_y=20000)
    assert report == bytes(
        [ABSOLUTE_MOUSE_REPORT_ID, 0x02, 0x30, 0x75, 0x00, 0x00]
    )


def test_hid_gadget_writes_relative_report(tmp_path: Path):
    keyboard = tmp_path / "hidg0"
    mouse = tmp_path / "hidg1"
    abs_mouse = tmp_path / "hidg2"
    paths = HidDevicePaths(
        keyboard=str(keyboard),
        mouse=str(mouse),
        absolute_mouse=str(abs_mouse),
    )
    gadget = HidGadget(paths=paths)

    gadget.write_mouse(buttons=0x01, x=10, y=-5, wheel=1, absolute=False)

    assert mouse.read_bytes() == bytes([MOUSE_REPORT_ID, 0x01, 0x0A, 0xFB, 0x01])
    assert not abs_mouse.exists()


def test_hid_gadget_absolute_respects_config(tmp_path: Path):
    keyboard = tmp_path / "hidg0"
    mouse = tmp_path / "hidg1"
    abs_mouse = tmp_path / "hidg2"
    paths = HidDevicePaths(
        keyboard=str(keyboard),
        mouse=str(mouse),
        absolute_mouse=str(abs_mouse),
    )
    mouse_config = HidMouseConfig(absolute_enabled=False)
    gadget = HidGadget(paths=paths, mouse_config=mouse_config)

    gadget.write_mouse(buttons=0x00, x=120, y=240, absolute=True)

    assert mouse.read_bytes() == bytes([MOUSE_REPORT_ID, 0x00, 0x78, 0x7F, 0x00])
    assert not abs_mouse.exists()
