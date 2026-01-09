"""Synergy bridge package."""

from .hid_gadget import (
    HID_REPORT_DESCRIPTORS,
    HidDevicePaths,
    HidGadget,
    HidMouseConfig,
)
from .synergy_client import (
    KeyEvent,
    MouseButtonEvent,
    MouseMoveEvent,
    ScreenTransitionEvent,
    SynergyClient,
    SynergyProtocolParser,
)
from .translator import (
    AbsoluteCoordinateRange,
    HidPointerEvent,
    ScreenLayout,
    ScreenLayoutConfig,
    SynergyTranslator,
    load_layout_config,
    parse_layout_config,
)

__all__ = [
    "HID_REPORT_DESCRIPTORS",
    "HidDevicePaths",
    "HidGadget",
    "HidMouseConfig",
    "KeyEvent",
    "MouseButtonEvent",
    "MouseMoveEvent",
    "ScreenTransitionEvent",
    "SynergyClient",
    "SynergyProtocolParser",
    "AbsoluteCoordinateRange",
    "HidPointerEvent",
    "ScreenLayout",
    "ScreenLayoutConfig",
    "SynergyTranslator",
    "load_layout_config",
    "parse_layout_config",
]
