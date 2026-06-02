"""Procedural boss ladder generation for the Cy-FX Monarchy hierarchy."""

from __future__ import annotations

import random

BOSS_NAMES = [
    "Drone Commander",
    "Logic Warden",
    "Shadow Sentinel",
    "Kernel Enforcer",
    "Firewall Guardian",
    "Protocol Executor",
    "Memory Reaper",
    "Cache Phantom",
    "Bus Arbitrator",
    "The Prime Cy-FX",
    "Monarch of Threads",
    "System Core",
    "The Overclocked",
    "Deadlock King",
    "Race Condition",
]

BOSS_TITLES = [
    "of the Outer Rim",
    "of Station Alpha",
    "of the Code Vault",
    "of the Data Nexus",
    "of the Memory Spire",
    "of the I/O Gate",
    "of the Bus Matrix",
    "of the ALU Chamber",
    "of the Register Array",
    "of the Prime Kernel",
    "of the Shadow Protocol",
    "of the Ascended Core",
    "of the Final Thread",
    "of the Infinite Loop",
    "of the Cy-FX Throne",
]


def generate_boss_ladder(max_level: int = 15, seed: int | None = None) -> dict[int, str]:
    """Generate a procedurally ordered boss ladder for the monarchy hierarchy."""
    if seed is not None:
        random.seed(seed)

    available_names = list(BOSS_NAMES)
    available_titles = list(BOSS_TITLES)
    random.shuffle(available_names)
    random.shuffle(available_titles)

    ladder = {}
    for level in range(1, max_level + 1):
        name_idx = (level - 1) % len(available_names)
        title_idx = (level - 1) % len(available_titles)
        boss_name = f"{available_names[name_idx]} {available_titles[title_idx]}"
        ladder[level] = boss_name

    return ladder
