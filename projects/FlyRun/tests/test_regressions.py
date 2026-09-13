"""Regression coverage for review findings; no network or GPU required."""
import json
import hashlib
import pandas as pd
import pytest
import torch

from circuits.looming import LoomingEscapeCircuit
from circuits.mushroom_body import MushroomBodyCircuit
from engine.buffers import SpikeRingBuffer, StateTraceBuffer
from telemetry.profiler import EnergyEstimator
from data.neuprint_client import NeuPrintExtractor
from data.export_subgraphs import export_graphs


@pytest.mark.parametrize('levels', [[0.85, 0.75], [0.9, 0.5, 0.2, 0.8, 0.1]])
def test_global_illumination_does_not_trigger_escape(levels):
    circuit = LoomingEscapeCircuit()
    for value in levels:
        _, _, telemetry = circuit.process_frame(torch.full((48, 48), value))
        assert not telemetry['jump_command']
        assert telemetry['lc4_spikes_count'] == 0


def test_kc_cap_on_tied_input_over_time():
    circuit = MushroomBodyCircuit(num_pn=32, num_kc=128, target_kc_sparsity=0.05)
    with torch.no_grad():
        counts = [circuit(torch.ones(32))[2]['kc_active_count'] for _ in range(20)]
    assert max(counts) > 0
    assert max(counts) <= 6


def test_energy_power_independent_of_recording_length_and_counts_neurons():
    def estimate(steps):
        e = EnergyEstimator(pJ_per_synop=15, pJ_per_neuron_update=5)
        for _ in range(steps):
            e.record_step(1, 10, 1000)
        return e.summary()
    short, long = estimate(1), estimate(10)
    assert short['estimated_power_mW_at_1kHz'] == pytest.approx(0.00515)
    assert long['estimated_power_mW_at_1kHz'] == short['estimated_power_mW_at_1kHz']
    assert long['total_energy_microjoules'] == pytest.approx(10 * short['total_energy_microjoules'])


@pytest.mark.parametrize('cls', [SpikeRingBuffer, StateTraceBuffer])
def test_buffer_returns_only_recorded_samples_and_copy(cls):
    b = cls(5, 1)
    assert b.window(4).shape == (0, 1)
    b.push(torch.tensor([3.0]))
    window = b.window(4)
    assert window.tolist() == [[3.0]]
    window.fill_(9)
    assert b.window().tolist() == [[3.0]]
    for i in range(6):
        b.push(torch.tensor([float(i)]))
    assert b.window(99).flatten().tolist() == [1, 2, 3, 4, 5]
    with pytest.raises(ValueError):
        b.window(-1)


@pytest.fixture
def measured_frame():
    return pd.DataFrame([[1, 'LC4', 2, 'DNp01', 10, 'ACH']],
                        columns=['pre_id', 'pre_type', 'post_id', 'post_type', 'synapse_count', 'neurotransmitter'])


@pytest.mark.parametrize('query', ['query_looming_circuit', 'query_optomotor_circuit', 'query_mushroom_body_circuit'])
def test_neuprint_dataframe_contract(query, measured_frame, monkeypatch):
    monkeypatch.delenv('NEUPRINT_APPLICATION_CREDENTIALS', raising=False)
    extractor = NeuPrintExtractor()
    class Client:
        def fetch_custom(self, cypher):
            return measured_frame.copy()
    extractor.client = Client()
    result = getattr(extractor, query)()
    assert result.iloc[0]['weight_eff'] == pytest.approx(0.1)
    assert result.iloc[0]['pre_id'] == 1


def test_unknown_neurotransmitter_is_not_assumed_excitatory(measured_frame, monkeypatch):
    monkeypatch.delenv('NEUPRINT_APPLICATION_CREDENTIALS', raising=False)
    measured_frame['neurotransmitter'] = None
    with pytest.raises(ValueError, match='Unknown neurotransmitter'):
        NeuPrintExtractor()._annotate_weights(measured_frame)


def test_missing_credentials_do_not_create_synthetic_data(tmp_path, monkeypatch):
    monkeypatch.delenv('NEUPRINT_APPLICATION_CREDENTIALS', raising=False)
    with pytest.raises(RuntimeError, match='explicitly'):
        export_graphs(tmp_path, 'test')
    assert not list(tmp_path.iterdir())


def test_export_second_query_failure_preserves_previous_files(tmp_path, monkeypatch, measured_frame):
    class Extractor:
        def __init__(self, **kwargs): pass
        def is_connected(self): return True
        def query_looming_circuit(self): return measured_frame
        def query_optomotor_circuit(self): raise RuntimeError('query failed')
    monkeypatch.setattr('data.export_subgraphs.NeuPrintExtractor', Extractor)
    old = tmp_path / 'looming_subgraph.parquet'
    old.write_bytes(b'existing')
    with pytest.raises(RuntimeError, match='query failed'):
        export_graphs(tmp_path, 'test')
    assert old.read_bytes() == b'existing'
    assert not (tmp_path / 'manifest.json').exists()


def test_synthetic_export_has_explicit_provenance(tmp_path):
    export_graphs(tmp_path, 'unused', synthetic=True)
    manifest = json.loads((tmp_path / 'manifest.json').read_text())
    assert manifest['source'] == 'synthetic'
    assert manifest['dataset'] is None
    for name, digest in manifest['sha256'].items():
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() == digest
