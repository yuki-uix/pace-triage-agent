"""Run a fresh baseline quality, calibration and serial operational benchmark.

Requires --live to invoke models. Historical submission results are never
replaced; each run must use a new output directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def commands(out: Path, model_a: str, model_b: str) -> list[list[str]]:
    prefix = [sys.executable, '-m']
    return [
        prefix + ['evals.compare', '--out', str(out / 'comparison.json')],
        prefix + ['evals.calibration', '--models', f'{model_a},{model_b}',
                  '--out', str(out / 'calibration.json')],
        prefix + ['evals.latency', '--triage-model', model_a, '--draft-model', model_b,
                  '--out', str(out / 'latency-flash-plus.json')],
        prefix + ['evals.latency', '--triage-model', model_b, '--draft-model', model_a,
                  '--out', str(out / 'latency-plus-flash.json')],
    ]


def fingerprints() -> dict[str, str]:
    paths = [*ROOT.glob('src/**/*.py'), *ROOT.glob('evals/**/*.py'),
             ROOT / 'data/enquiries.jsonl', ROOT / 'data/golden.jsonl',
             ROOT / 'data/model_prices.json', ROOT / 'requirements.txt']
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def run_suite(out: Path, model_a: str, model_b: str) -> int:
    # Exclusive creation prevents accidental replacement of paid evidence.
    out.mkdir(parents=True, exist_ok=False)
    manifest = {
        'status': 'running', 'scope': 'baseline; evidence-backed candidate excluded',
        'started_at': datetime.now(timezone.utc).isoformat(),
        'models': [model_a, model_b], 'fingerprints': fingerprints(), 'steps': [],
    }
    target = out / 'manifest.json'

    def save():
        target.write_text(json.dumps(manifest, indent=2) + '\n')

    save()
    for command in commands(out, model_a, model_b):
        step = {'command': command, 'status': 'running'}
        manifest['steps'].append(step)
        save()
        try:
            code = subprocess.run(command, cwd=ROOT, check=False).returncode
        except (OSError, KeyboardInterrupt) as exc:
            step.update(status='failed', error=type(exc).__name__)
            manifest['status'] = 'failed'
            save()
            return 1
        step.update(returncode=code, status='complete' if code == 0 else 'failed')
        if code or fingerprints() != manifest['fingerprints']:
            manifest['status'] = 'failed' if code else 'source_changed'
            save()
            return code or 1
        save()
    manifest['status'] = 'complete'
    manifest['completed_at'] = datetime.now(timezone.utc).isoformat()
    save()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='make paid model calls')
    parser.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    out = args.out_dir.resolve()
    if not args.live:
        print('Preview only; no model calls. Add --live to execute:')
        for command in commands(out, 'MODEL_A', 'MODEL_B'):
            print(' '.join(command))
        return 0
    from src.generate import load_env
    load_env()
    required = ['DASHSCOPE_API_KEY', 'DASHSCOPE_BASE_URL', 'TRIAGE_MODEL_A',
                'TRIAGE_MODEL_B', 'JUDGE_MODEL']
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        parser.error('Missing configuration: ' + ', '.join(missing))
    if out.exists():
        parser.error('Output directory already exists; choose a new run directory.')
    return run_suite(out, os.environ['TRIAGE_MODEL_A'], os.environ['TRIAGE_MODEL_B'])


if __name__ == '__main__':
    raise SystemExit(main())
