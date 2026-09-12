"""Command-line utility to pull and serialize target connectome subgraphs to Parquet."""

import argparse
import logging
from pathlib import Path
import pandas as pd

from data.neuprint_client import NeuPrintExtractor
from data.synthetic_subgraphs import export_all_synthetic_subgraphs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Export Drosophila Connectome Subgraphs")
    parser.add_argument("--output-dir", type=str, default="data/artifacts", help="Output directory for Parquet files")
    parser.add_argument("--dataset", type=str, default="hemibrain:v1.2.1", help="NeuPrint dataset")
    parser.add_argument("--force-synthetic", action="store_true", help="Force generation of synthetic ground-truth subgraphs")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.force_synthetic:
        try:
            extractor = NeuPrintExtractor(dataset=args.dataset)
            if extractor.is_connected():
                logger.info("Querying NeuPrint for Looming Circuit (LC4 -> GF)...")
                df_looming = extractor.query_looming_circuit()
                df_looming.to_parquet(out_dir / "looming_subgraph.parquet", compression="zstd")
                logger.info("Successfully exported %d looming synapses.", len(df_looming))

                logger.info("Querying NeuPrint for Optomotor Circuit (T4/T5 -> HS/VS)...")
                df_optomotor = extractor.query_optomotor_circuit()
                df_optomotor.to_parquet(out_dir / "optomotor_subgraph.parquet", compression="zstd")
                logger.info("Successfully exported %d optomotor synapses.", len(df_optomotor))
                return
        except Exception as e:
            logger.warning("NeuPrint extraction failed or credentials not present: %s", e)
            logger.info("Falling back to high-fidelity biological synthetic subgraphs...")

    logger.info("Generating synthetic biological subgraphs in %s...", out_dir)
    export_all_synthetic_subgraphs(output_dir=str(out_dir))
    logger.info("Export completed successfully.")


if __name__ == "__main__":
    main()
