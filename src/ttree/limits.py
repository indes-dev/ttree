"""Finite TASK-003 limits. Configuration may only lower these ceilings."""

from __future__ import annotations

MIB = 1024 * 1024
CAPS = dict(
    input_bytes=64 * MIB,
    xml_part_bytes=4 * MIB,
    xml_total_bytes=8 * MIB,
    pdf_pages=2000,
    characters=1_000_000,
    wall_seconds=15,
    cpu_seconds=10,
    address_space_bytes=512 * MIB,
    response_bytes=12 * MIB,
    scan_seconds=120,
    entries=100_000,
    xml_depth=128,
    xml_elements=100_000,
    zip_members=4096,
)
CAPS["path_bytes"] = 16 * MIB


def validated(overrides=None):
    limits = CAPS.copy()
    for key, value in (overrides or {}).items():
        if (
            key not in limits
            or isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 < value <= CAPS[key]
        ):
            raise ValueError("invalid finite limit")
        limits[key] = value
    return limits
