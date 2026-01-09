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
]
