"""Command-line interface for running the Synergy bridge."""

from __future__ import annotations

import argparse
import logging
import re
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from .hid_gadget import HidDevicePaths, HidGadget, HidMouseConfig
from .synergy_client import KeyEvent, MouseButtonEvent, ScreenTransitionEvent, SynergyClient
from .translator import (
    HidPointerEvent,
    ScreenLayout,
    ScreenLayoutConfig,
    SynergyTranslator,
    load_layout_config,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class RuntimeState:
    buttons: int = 0
    pressed_keys: set[int] = None
    last_absolute: Optional[tuple[int, int]] = None
    event_count: int = 0
    last_event_time: Optional[float] = None

    def __post_init__(self) -> None:
        if self.pressed_keys is None:
            self.pressed_keys = set()


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge Synergy input events to USB HID gadgets.",
    )
    parser.add_argument(
        "--server",
        default="127.0.0.1:24800",
        help="Synergy server address in host:port form (default: %(default)s).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to a JSON-compatible config file (see config.yaml).",
    )
    parser.add_argument(
        "--screen",
        action="append",
        default=[],
        help=(
            "Screen layout entry formatted as NAME:WIDTHxHEIGHT+X+Y. "
            "Can be specified multiple times."
        ),
    )
    parser.add_argument(
        "--keyboard-path",
        default=HidDevicePaths().keyboard,
        help="HID gadget path for keyboard reports.",
    )
    parser.add_argument(
        "--mouse-path",
        default=HidDevicePaths().mouse,
        help="HID gadget path for relative mouse reports.",
    )
    parser.add_argument(
        "--absolute-mouse-path",
        default=HidDevicePaths().absolute_mouse,
        help="HID gadget path for absolute mouse reports.",
    )
    parser.add_argument(
        "--relative",
        action="store_true",
        help="Emit relative mouse reports instead of absolute coordinates.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: %(default)s).",
    )
    parser.add_argument(
        "--health-interval",
        type=float,
        default=30.0,
        help="Seconds between health-check log messages (0 to disable).",
    )
    return parser.parse_args(argv)


def parse_server(value: str) -> tuple[str, int]:
    if ":" in value:
        host, port_text = value.rsplit(":", 1)
        return host, int(port_text)
    return value, 24800


def parse_screen(value: str) -> ScreenLayout:
    pattern = re.compile(
        r"^(?P<name>[^:]+):(?P<width>\d+)x(?P<height>\d+)(?P<x>[+-]\d+)(?P<y>[+-]\d+)$"
    )
    match = pattern.match(value)
    if not match:
        raise ValueError(f"Invalid screen format: {value}")
    return ScreenLayout(
        name=match.group("name"),
        width=int(match.group("width")),
        height=int(match.group("height")),
        x=int(match.group("x")),
        y=int(match.group("y")),
    )


def load_screen_layout(args: argparse.Namespace) -> ScreenLayoutConfig:
    if args.config:
        return load_layout_config(args.config)
    if args.screen:
        screens = [parse_screen(value) for value in args.screen]
        return ScreenLayoutConfig(screens=screens)
    default_path = Path("config.yaml")
    if default_path.exists():
        return load_layout_config(default_path)
    raise ValueError("No screen layout configured; provide --config or --screen.")


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def update_pressed_keys(keys: set[int], event: KeyEvent) -> List[int]:
    if event.pressed:
        keys.add(event.keycode)
    else:
        keys.discard(event.keycode)
    return sorted(keys)


def apply_mouse_button(state: RuntimeState, event: MouseButtonEvent) -> None:
    mapping = {1: 0x01, 2: 0x02, 3: 0x04}
    mask = mapping.get(event.button)
    if mask is None:
        LOGGER.debug("Ignoring unsupported mouse button %s", event.button)
        return
    if event.pressed:
        state.buttons |= mask
    else:
        state.buttons &= ~mask


def log_health(state: RuntimeState, *, connected: bool) -> None:
    last_event = (
        f"{time.time() - state.last_event_time:.1f}s ago"
        if state.last_event_time
        else "never"
    )
    LOGGER.info(
        "health_check connected=%s events=%s last_event=%s",
        connected,
        state.event_count,
        last_event,
    )


def run_bridge(args: argparse.Namespace) -> None:
    host, port = parse_server(args.server)
    layout_config = load_screen_layout(args)
    hid_paths = HidDevicePaths(
        keyboard=args.keyboard_path,
        mouse=args.mouse_path,
        absolute_mouse=args.absolute_mouse_path,
    )
    hid_gadget = HidGadget(
        paths=hid_paths,
        mouse_config=HidMouseConfig(absolute_enabled=not args.relative),
    )
    translator = SynergyTranslator(layout_config, use_absolute=not args.relative)
    state = RuntimeState()

    client = SynergyClient(host, port)
    try:
        LOGGER.info("Connecting to Synergy server %s:%s", host, port)
        client.connect()
    except OSError as exc:
        LOGGER.error("Failed to connect to Synergy server: %s", exc)
        raise SystemExit(1) from exc

    LOGGER.info(
        "Connected. keyboard=%s mouse=%s absolute_mouse=%s absolute_mode=%s",
        hid_paths.keyboard,
        hid_paths.mouse,
        hid_paths.absolute_mouse,
        not args.relative,
    )

    next_health = time.time() + args.health_interval if args.health_interval > 0 else None
    try:
        for event in client.iter_events():
            state.event_count += 1
            state.last_event_time = time.time()
            if isinstance(event, ScreenTransitionEvent):
                LOGGER.info(
                    "Screen transition %s %s",
                    event.screen,
                    "entered" if event.entered else "left",
                )
            for output in translator.translate(event):
                if isinstance(output, HidPointerEvent):
                    if output.absolute:
                        state.last_absolute = (output.x, output.y)
                    hid_gadget.write_mouse(
                        buttons=state.buttons,
                        x=output.x,
                        y=output.y,
                        absolute=output.absolute,
                    )
                elif isinstance(output, MouseButtonEvent):
                    apply_mouse_button(state, output)
                    x, y = (0, 0)
                    if not args.relative and state.last_absolute is not None:
                        x, y = state.last_absolute
                    hid_gadget.write_mouse(
                        buttons=state.buttons,
                        x=x,
                        y=y,
                        absolute=not args.relative,
                    )
                elif isinstance(output, KeyEvent):
                    key_list = update_pressed_keys(state.pressed_keys, output)
                    if len(key_list) > 6:
                        LOGGER.warning(
                            "Too many keys pressed (%s); truncating to first 6.",
                            len(key_list),
                        )
                        key_list = key_list[:6]
                    hid_gadget.write_keyboard(output.modifiers, key_list)
                elif isinstance(output, ScreenTransitionEvent):
                    LOGGER.debug("Screen event %s entered=%s", output.screen, output.entered)
                else:
                    LOGGER.debug("Unhandled event %s", output)

            if next_health and time.time() >= next_health:
                log_health(state, connected=True)
                next_health = time.time() + args.health_interval
    except KeyboardInterrupt:
        LOGGER.info("Received interrupt, shutting down.")
    except socket.error as exc:
        LOGGER.error("Socket error: %s", exc)
        raise SystemExit(1) from exc
    finally:
        client.close()
        if next_health is not None:
            log_health(state, connected=False)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    setup_logging(args.log_level)
    run_bridge(args)


if __name__ == "__main__":
    main()
