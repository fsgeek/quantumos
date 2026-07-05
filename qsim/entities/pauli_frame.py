"""PauliFrameToken entity: deferred-correction marker. V1: counted, not
semantically modeled — exists so fast-path pressure relief is observable
later (design spec §5)."""

from dataclasses import dataclass


@dataclass
class PauliFrameToken:
    token_id: str
    created_at: float
