"""Synergy bridge package."""

from .synergy_client import (
    KeyEvent,
    MouseButtonEvent,
    MouseMoveEvent,
    ScreenTransitionEvent,
    SynergyClient,
    SynergyProtocolParser,
)

__all__ = [
    "KeyEvent",
    "MouseButtonEvent",
    "MouseMoveEvent",
    "ScreenTransitionEvent",
    "SynergyClient",
    "SynergyProtocolParser",
]
