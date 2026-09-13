"""Synthetic, Drosophila-inspired example graphs.

These hand-chosen topologies and distributions are not measured connectome data.
"""

from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import pandas as pd


def generate_synthetic_looming_graph(num_lc4: int = 256, num_lplc2: int = 128) -> pd.DataFrame:
    """Generate illustrative LC4 & LPLC2 -> Giant Fiber (DNp01) synaptic connectivity table.

    Model assumptions (not empirically validated):
    - LC4: ~60-120 synapses per cell converging onto Giant Fiber dendrites.
    - Neurotransmitter: Acetylcholine (ACh, excitatory).
    - Bilateral Giant Fibers: GF_L (DNp01_L) and GF_R (DNp01_R).
    """
    records = []

    # LC4 population
    for i in range(num_lc4):
        pre_id = 100000 + i
        pre_type = f"LC4_{i:03d}"
        
        # Determine hemispheric bias
        is_left = i < (num_lc4 // 2)
        target_gfs = ["DNp01_L"] if is_left else ["DNp01_R"]
        # ~25% central neurons connect bilaterally
        if abs(i - (num_lc4 // 2)) < (num_lc4 // 8):
            target_gfs = ["DNp01_L", "DNp01_R"]

        for gf in target_gfs:
            post_id = 900001 if gf == "DNp01_L" else 900002
            synapse_count = int(np.random.normal(loc=75, scale=15))
            synapse_count = max(10, synapse_count)
            records.append({
                "pre_id": pre_id,
                "pre_type": "LC4",
                "post_id": post_id,
                "post_type": gf,
                "synapse_count": synapse_count,
                "neurotransmitter": "ACH",
                "polarity": 1.0,
                "weight_eff": synapse_count * 0.0012,  # Calibrated for LIF threshold
            })

    # LPLC2 population (radial outward flow)
    for i in range(num_lplc2):
        pre_id = 200000 + i
        is_left = i < (num_lplc2 // 2)
        gf = "DNp01_L" if is_left else "DNp01_R"
        post_id = 900001 if gf == "DNp01_L" else 900002
        synapse_count = int(np.random.normal(loc=45, scale=10))
        synapse_count = max(8, synapse_count)
        records.append({
            "pre_id": pre_id,
            "pre_type": "LPLC2",
            "post_id": post_id,
            "post_type": gf,
            "synapse_count": synapse_count,
            "neurotransmitter": "ACH",
            "polarity": 1.0,
            "weight_eff": synapse_count * 0.0010,
        })

    return pd.DataFrame(records)


def generate_synthetic_optomotor_graph(num_t4_t5: int = 512) -> pd.DataFrame:
    """Generate T4/T5 to Lobula Plate Tangential Cells (HSN, HSE, HSS, VS1-6)."""
    records = []
    lptc_types = ["HSN_L", "HSE_L", "HSS_L", "HSN_R", "HSE_R", "HSS_R"]

    for i in range(num_t4_t5):
        pre_id = 300000 + i
        direction = ["a", "b", "c", "d"][i % 4]
        cell_type = f"T4{direction}" if (i % 2 == 0) else f"T5{direction}"
        is_left = i < (num_t4_t5 // 2)
        
        # Connect primarily to corresponding HS cells
        hs_target = lptc_types[0] if is_left else lptc_types[3]
        post_id = 800000 + (0 if is_left else 3)
        syn_count = int(np.random.poisson(lam=25))
        
        records.append({
            "pre_id": pre_id,
            "pre_type": cell_type,
            "post_id": post_id,
            "post_type": hs_target,
            "synapse_count": syn_count,
            "neurotransmitter": "ACH",
            "polarity": 1.0,
            "weight_eff": syn_count * 0.002,
        })

    return pd.DataFrame(records)


def export_all_synthetic_subgraphs(output_dir: str = "data/artifacts") -> None:
    """Export all default connectome subgraphs to compressed Parquet format."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    df_looming = generate_synthetic_looming_graph()
    looming_file = out_path / "looming_subgraph.parquet"
    df_looming.to_parquet(looming_file, compression="zstd")
    print(f"Exported looming subgraph: {len(df_looming)} synapses -> {looming_file}")

    df_optomotor = generate_synthetic_optomotor_graph()
    optomotor_file = out_path / "optomotor_subgraph.parquet"
    df_optomotor.to_parquet(optomotor_file, compression="zstd")
    print(f"Exported optomotor subgraph: {len(df_optomotor)} synapses -> {optomotor_file}")


if __name__ == "__main__":
    export_all_synthetic_subgraphs()
