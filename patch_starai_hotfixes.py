#!/usr/bin/env python3
"""Apply local hotfixes for StarAI/FashionStar LeRobot packages.

Run this with the Python executable from the target LeRobot environment:

    python patch_starai_hotfixes.py

The fixes are intentionally idempotent, so it is safe to run more than once.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def package_file(package: str, relative_path: str) -> Path:
    spec = importlib.util.find_spec(package)
    if spec is None or spec.origin is None:
        raise RuntimeError(f"Package not found in this environment: {package}")
    return Path(spec.origin).parent / relative_path


def replace_once(path: Path, old: str, new: str, description: str) -> None:
    text = path.read_text()
    if new in text:
        print(f"ok: {description} already patched")
        return
    if old not in text:
        raise RuntimeError(f"Could not find expected code for {description} in {path}")
    path.write_text(text.replace(old, new, 1))
    print(f"patched: {description}")


def patch_starai_motor_bus() -> None:
    path = package_file("lerobot_motor_starai", "starai.py")
    old = """            for name in names:
                if monitor_data[name].current_position >= 180:
                    monitor_data[name].current_position = 180
                elif monitor_data[name].current_position <= -180:
                    monitor_data[name].current_position = -180
                monitor_data[name].current_position = (
                    int(monitor_data[name].current_position + 180) / 360.0 * 4096
                )
            for name in names:
                read_data[name] = int(monitor_data[name].current_position)
"""
    new = """            for name in names:
                pos = monitor_data[name].current_position
                if pos >= 180:
                    pos = 180
                elif pos <= -180:
                    pos = -180
                read_data[name] = int((pos + 180) / 360.0 * 4096)
"""
    replace_once(path, old, new, "lerobot_motor_starai sync_read position cache")


def patch_fashionstar_monitor_data() -> None:
    path = package_file("fashionstar_uart_sdk", "uart_pocket_handler.py")
    old = """\t\tif abs(self.current_position - current_position) < 10:
\t\t\tself.current_position = current_position
"""
    new = """\t\tself.current_position = current_position
"""
    replace_once(path, old, new, "fashionstar_uart_sdk Monitor_data.flash position update")


def patch_violin_slow_start() -> None:
    path = package_file("lerobot_teleoperator_violin", "starai_violin.py")
    old = """        if self.is_calibrated:
            logger.info(f"{self} slow start in progress, please wait for 3 seconds.")
            self.move_to_initial_position()
"""
    new = """        if self.is_calibrated:
            logger.info(f"{self} automatic slow start is disabled; skipping initial position move.")
"""
    replace_once(path, old, new, "lerobot_teleoperator_violin automatic initial-position move")


def main() -> None:
    patch_starai_motor_bus()
    patch_fashionstar_monitor_data()
    patch_violin_slow_start()


if __name__ == "__main__":
    main()
