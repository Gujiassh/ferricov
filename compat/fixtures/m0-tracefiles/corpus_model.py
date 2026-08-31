"""Shared fixture model helpers for the M0 tracefile corpus."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fixture:
    id: str
    path: str
    group: str
    description: str
    data: bytes
    oracle_default: str
    committed: bool = True
    parameters: dict[str, int | str] | None = None


def ascii_bytes(text: str, newline: bytes = b"\n", final_newline: bool = True) -> bytes:
    lines = text.strip("\n").split("\n")
    data = newline.join(line.encode("ascii") for line in lines)
    return data + (newline if final_newline else b"")
