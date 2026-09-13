"""Export measured NeuPrint graphs or explicitly requested synthetic examples."""
import argparse
import hashlib
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from data.neuprint_client import NeuPrintExtractor
from data.synthetic_subgraphs import export_all_synthetic_subgraphs

logger = logging.getLogger(__name__)


def export_graphs(output_dir: Path, dataset: str, synthetic: bool = False) -> None:
    """Validate both results before publishing; never substitute synthetic data on error.

    The manifest is written last. Readers should verify its hashes before trusting
    a directory, including after an interrupted replacement of an existing export.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_dir) as staging:
        staged = Path(staging)
        source = "synthetic" if synthetic else "neuprint"
        if synthetic:
            export_all_synthetic_subgraphs(str(staged))
        else:
            extractor = NeuPrintExtractor(dataset=dataset)
            if not extractor.is_connected():
                raise RuntimeError("NeuPrint unavailable. Supply credentials or explicitly use --force-synthetic.")
            graphs = {
                "looming_subgraph.parquet": extractor.query_looming_circuit(),
                "optomotor_subgraph.parquet": extractor.query_optomotor_circuit(),
            }
            for name, df in graphs.items():
                if df.empty:
                    raise ValueError(f"Empty {name}: check dataset coverage and neuron type names")
                df.to_parquet(staged / name, compression="zstd")
        files = sorted(staged.glob("*.parquet"))
        manifest = {
            "source": source,
            "dataset": None if synthetic else dataset,
            "server": None if synthetic else extractor.server,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "biologically_validated": False,
            "note": "Exported tables are not loaded by the current controller. Effective weights use model assumptions.",
            "sha256": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        }
        for f in files:
            f.replace(output_dir / f.name)
        manifest_file = staged / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
        manifest_file.replace(output_dir / "manifest.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="data/artifacts")
    parser.add_argument("--dataset", default="hemibrain:v1.2.1")
    parser.add_argument("--force-synthetic", action="store_true", help="Explicitly generate unvalidated example graphs")
    args = parser.parse_args()
    export_graphs(Path(args.output_dir), args.dataset, args.force_synthetic)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
