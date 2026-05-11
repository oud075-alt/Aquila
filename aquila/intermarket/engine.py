from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName, Symbol
from aquila.intermarket.schemas import IntermarketRelation, IntermarketReport
from aquila.regime.schemas import RegimeKind


class IntermarketCognition:
    def __init__(self) -> None:
        self._latest: dict[Symbol, dict[LayerName, LayerOutput]] = {}

    def observe(self, symbol: Symbol, outputs: dict[LayerName, LayerOutput]) -> None:
        self._latest[symbol] = dict(outputs)

    def report(self) -> IntermarketReport:
        contras: list[IntermarketRelation] = []
        migrations: list[IntermarketRelation] = []
        contagion: list[IntermarketRelation] = []
        symbols = list(self._latest.keys())
        for i, a in enumerate(symbols):
            for b in symbols[i + 1 :]:
                ra = self._latest[a].get(LayerName.REGIME)
                rb = self._latest[b].get(LayerName.REGIME)
                if ra is None or rb is None:
                    continue
                ra_state = ra.payload.current; rb_state = rb.payload.current  # type: ignore[attr-defined]
                if ra_state.volatility != rb_state.volatility:
                    contras.append(IntermarketRelation(
                        a=a, b=b, score=0.5, kind="vol_regime_disagreement",
                        rationale=f"{ra_state.volatility.value} vs {rb_state.volatility.value}",
                    ))
                if ra_state.liquidity == RegimeKind.THIN_LIQUIDITY and rb_state.liquidity == RegimeKind.DEEP_LIQUIDITY:
                    migrations.append(IntermarketRelation(
                        a=a, b=b, score=0.6, kind="liquidity_migration",
                        rationale=f"liquidity migrated {a}->{b}",
                    ))
                if ra_state.volatility == RegimeKind.HIGH_VOL and rb_state.volatility == RegimeKind.HIGH_VOL:
                    contagion.append(IntermarketRelation(
                        a=a, b=b, score=0.7, kind="regime_contagion_high_vol",
                    ))
        rels = contras + migrations + contagion
        return IntermarketReport(
            relations=rels,
            contradictions=contras,
            liquidity_migrations=migrations,
            regime_contagion=contagion,
        )
