from __future__ import annotations

from aquila.core.base import LayerOutput
from aquila.core.types import LayerName
from aquila.narrative.schemas import NarrativeReport


class NarrativeExplainer:
    def explain(self, outputs: dict[LayerName, LayerOutput]) -> NarrativeReport:
        struct = outputs.get(LayerName.STRUCTURAL)
        path = outputs.get(LayerName.PATHOLOGY)
        temp = outputs.get(LayerName.TEMPORAL)
        decep = outputs.get(LayerName.DECEPTION)
        reg = outputs.get(LayerName.REGIME)
        meta = outputs.get(LayerName.META)

        def _f(x, fn, default="n/a"):
            try:
                return fn(x)
            except Exception:
                return default

        s_sum = _f(struct, lambda o: f"Structural state: {o.payload.state.value} (score {o.payload.score:.2f})")
        p_sum = _f(path, lambda o: f"{len(o.payload.signatures)} pathology signature(s); contradiction {o.payload.aggregate_contradiction_score:.2f}")
        t_sum = _f(temp, lambda o: f"Temporal fused: {o.payload.fused_state.value}; alignment {o.payload.alignment_score:.2f}; conflicts {len(o.payload.conflict_graph.edges)}")
        d_sum = _f(decep, lambda o: f"Deception probability {o.payload.deception_probability:.2f}; {len(o.payload.signatures)} trap signature(s)")
        r_sum = _f(reg, lambda o: f"Regime vol={o.payload.current.volatility.value}, liq={o.payload.current.liquidity.value}, part={o.payload.current.participation.value}; instability {o.payload.instability_score:.2f}")
        m_sum = _f(meta, lambda o: f"Cognitive health {o.payload.cognitive_health:.2f}; uncertainty total {o.payload.uncertainty.total:.2f}; consistent={o.payload.self_consistency.consistent}")

        chain: list[str] = []
        if struct: chain.append(f"L2 {struct.payload.state.value}")
        if path: chain.append(f"L3 pathology score {path.payload.aggregate_pathology_score:.2f}")
        if decep: chain.append(f"L6 deception {decep.payload.deception_probability:.2f}")
        if reg: chain.append(f"L7 instability {reg.payload.instability_score:.2f}")
        if meta: chain.append(f"L8 health {meta.payload.cognitive_health:.2f}")

        conf_just = (
            f"Aggregate cognitive health {meta.payload.cognitive_health:.2f}" if meta else "n/a"
        )
        unc_comm = (
            f"Total uncertainty {meta.payload.uncertainty.total:.2f}; low-vis layers: "
            f"{[l.value for l in meta.payload.low_visibility_layers]}"
            if meta else "n/a"
        )

        corr = next(iter(outputs.values())).correlation_id if outputs else ""
        return NarrativeReport(
            correlation_id=corr,
            structural_summary=s_sum,
            pathology_summary=p_sum,
            temporal_summary=t_sum,
            deception_summary=d_sum,
            regime_summary=r_sum,
            meta_summary=m_sum,
            causal_chain=chain,
            confidence_justification=conf_just,
            uncertainty_communication=unc_comm,
        )
