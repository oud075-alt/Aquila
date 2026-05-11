"""Instrument master — closes audit gap #43."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aquila.core.types import Symbol


class Instrument(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: Symbol
    asset_class: str = "crypto"
    tick_size: float = 0.01
    lot_size: float = 1.0
    session: str = "24x7"


class InstrumentMaster:
    def __init__(self) -> None:
        self._by_symbol: dict[str, Instrument] = {}

    def register(self, inst: Instrument) -> None:
        self._by_symbol[inst.symbol] = inst

    def get(self, symbol: Symbol) -> Instrument:
        if symbol not in self._by_symbol:
            self.register(Instrument(symbol=symbol))
        return self._by_symbol[symbol]

    def all(self) -> list[Instrument]:
        return list(self._by_symbol.values())
