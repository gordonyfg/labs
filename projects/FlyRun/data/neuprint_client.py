"""NeuPrint Python client interface for Drosophila connectome subgraph extraction.

Interfaces with Janelia NeuPrint server (MaleCNS v1.0, Hemibrain v1.2.1) to extract
ground-truth synaptic topologies and cell types.
"""

from __future__ import annotations
import os
import logging
from typing import Optional, Dict, Any, List
import pandas as pd

logger = logging.getLogger(__name__)

# Polarity convention for neurotransmitters in Drosophila CNS:
# Acetylcholine (ACh): Fast excitatory cation channel
# GABA: Ionotropic / metabotropic inhibitory chloride channel
# Glutamate (Glu): Predominantly inhibitory via GluCl in insect CNS
NT_POLARITY_MAP: Dict[str, float] = {
    "ACH": 1.0,
    "ACETYLCHOLINE": 1.0,
    "CHOLINERGIC": 1.0,
    "GABA": -1.0,
    "GABAERGIC": -1.0,
    "GLUTAMATE": -1.0,
    "GLUT": -1.0,
    "GLUTAMATERGIC": -1.0,
    "HISTAMINE": -1.0,
    "DOPAMINE": 0.0,     # Neuromodulatory (handled via STDP third factor)
    "OCTOPAMINE": 0.0,    # Neuromodulatory
    "SEROTONIN": 0.0,     # Neuromodulatory
    "UNKNOWN": 1.0,       # Default excitatory assumption
}


class NeuPrintExtractor:
    """Extracts target sensorimotor subgraphs from NeuPrint."""

    def __init__(
        self,
        server: str = "https://neuprint.janelia.org",
        dataset: str = "hemibrain:v1.2.1",
        token: Optional[str] = None,
    ):
        self.server = server
        self.dataset = dataset
        self.token = token or os.environ.get("NEUPRINT_APPLICATION_CREDENTIALS")
        self.client = None

        if self.token:
            try:
                from neuprint import Client
                self.client = Client(self.server, dataset=self.dataset, token=self.token)
                logger.info("Connected to NeuPrint at %s, dataset %s", self.server, self.dataset)
            except Exception as e:
                logger.warning("Failed to initialize NeuPrint client: %s", e)
        else:
            logger.info("No NeuPrint token provided. Running in offline / cached mode.")

    def is_connected(self) -> bool:
        return self.client is not None

    def query_looming_circuit(self) -> pd.DataFrame:
        """Query synapses from LC4 and LPLC2 to Giant Fiber (DNp01)."""
        if not self.is_connected():
            raise RuntimeError(
                "NeuPrint token not configured. Set NEUPRINT_APPLICATION_CREDENTIALS or use offline artifacts."
            )

        cypher = """
        MATCH (pre:Neuron)-[e:ConnectsTo]->(post:Neuron)
        WHERE (pre.type STARTS WITH 'LC4' OR pre.type STARTS WITH 'LPLC2')
          AND (post.type STARTS WITH 'DNp01' OR post.type STARTS WITH 'Giant_Fiber')
        RETURN pre.bodyId AS pre_id,
               pre.type AS pre_type,
               post.bodyId AS post_id,
               post.type AS post_type,
               e.weight AS synapse_count,
               pre.predictedNt AS neurotransmitter
        ORDER BY synapse_count DESC
        """
        results, _ = self.client.fetch_custom(cypher)
        df = pd.DataFrame(results)
        return self._annotate_weights(df)

    def query_optomotor_circuit(self) -> pd.DataFrame:
        """Query T4/T5 to Lobula Plate Tangential Cells (HS, VS)."""
        if not self.is_connected():
            raise RuntimeError("NeuPrint client not connected.")

        cypher = """
        MATCH (pre:Neuron)-[e:ConnectsTo]->(post:Neuron)
        WHERE (pre.type STARTS WITH 'T4' OR pre.type STARTS WITH 'T5')
          AND (post.type STARTS WITH 'HS' OR post.type STARTS WITH 'VS' OR post.type STARTS WITH 'LPTC')
        RETURN pre.bodyId AS pre_id,
               pre.type AS pre_type,
               post.bodyId AS post_id,
               post.type AS post_type,
               e.weight AS synapse_count,
               pre.predictedNt AS neurotransmitter
        ORDER BY synapse_count DESC
        """
        results, _ = self.client.fetch_custom(cypher)
        df = pd.DataFrame(results)
        return self._annotate_weights(df)

    def query_mushroom_body_circuit(self) -> pd.DataFrame:
        """Query Kenyon Cells (KC) to MBONs and DAN modulation."""
        if not self.is_connected():
            raise RuntimeError("NeuPrint client not connected.")

        cypher = """
        MATCH (pre:Neuron)-[e:ConnectsTo]->(post:Neuron)
        WHERE (pre.type STARTS WITH 'KC')
          AND (post.type STARTS WITH 'MBON')
        RETURN pre.bodyId AS pre_id,
               pre.type AS pre_type,
               post.bodyId AS post_id,
               post.type AS post_type,
               e.weight AS synapse_count,
               pre.predictedNt AS neurotransmitter
        ORDER BY synapse_count DESC
        LIMIT 5000
        """
        results, _ = self.client.fetch_custom(cypher)
        df = pd.DataFrame(results)
        return self._annotate_weights(df)

    def _annotate_weights(self, df: pd.DataFrame, unitary_weight: float = 0.01) -> pd.DataFrame:
        """Compute effective biophysical synaptic weight W_ij = polarity * count * unitary_weight."""
        if df.empty:
            return df

        def get_polarity(nt: Any) -> float:
            if not isinstance(nt, str):
                return 1.0
            return NT_POLARITY_MAP.get(nt.upper().strip(), 1.0)

        df["polarity"] = df["neurotransmitter"].apply(get_polarity)
        df["weight_eff"] = df["polarity"] * df["synapse_count"] * unitary_weight
        return df
