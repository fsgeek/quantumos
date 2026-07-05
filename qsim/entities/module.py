"""Module, PortId, and switch-fabric PathId entities (design spec §5, §7)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PortId:
    module_id: str
    port_index: int


@dataclass
class Module:
    module_id: str
    ports: tuple[PortId, ...]


# PathId is the pair of endpoints a crossbar path connects, canonically
# ordered so (a, b) and (b, a) hash identically (design spec §7).
PathId = tuple[PortId, PortId]


def make_path_id(a: PortId, b: PortId) -> PathId:
    return tuple(sorted((a, b), key=lambda p: (p.module_id, p.port_index)))
