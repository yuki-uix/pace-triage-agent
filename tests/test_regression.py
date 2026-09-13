import json
from types import SimpleNamespace

import pytest

from evals import regression


def test_preview_does_not_call_models_or_create_files(tmp_path, monkeypatch):
    monkeypatch.setattr(regression.subprocess, 'run', lambda *a, **k: pytest.fail('called'))
    out = tmp_path / 'run'
    assert regression.main(['--out-dir', str(out)]) == 0
    assert not out.exists()


def test_full_run_is_sequential_and_covers_both_operational_roles(tmp_path, monkeypatch):
    calls = []
    def fake(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(regression.subprocess, 'run', fake)
    out = tmp_path / 'run'
    assert regression.run_suite(out, 'flash', 'plus') == 0
    assert [c[2] for c in calls] == ['evals.compare', 'evals.calibration',
                                    'evals.latency', 'evals.latency']
    assert calls[2][4] == 'flash' and calls[3][4] == 'plus'
    result = json.loads((out / 'manifest.json').read_text())
    assert result['status'] == 'complete'
    assert result['fingerprints']['data/golden.jsonl']
    with pytest.raises(FileExistsError):
        regression.run_suite(out, 'flash', 'plus')


def test_failure_stops_later_paid_steps_and_preserves_manifest(tmp_path, monkeypatch):
    calls = []
    def fail(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=2)
    monkeypatch.setattr(regression.subprocess, 'run', fail)
    out = tmp_path / 'run'
    assert regression.run_suite(out, 'flash', 'plus') == 2
    assert len(calls) == 1
    assert json.loads((out / 'manifest.json').read_text())['status'] == 'failed'
