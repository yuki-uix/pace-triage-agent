"""The JavaScript copy of the prompts must not drift from the Python original.

`api/index.mjs` re-implements the triage and draft system prompts so the hosted
demo can run without the Python stack. That duplication is a real hazard and was
flagged as one before it was covered: the injection-resistance metric extracts
its leakage probes from the Python constants in `src/pipeline.py` **at call
time**, so the JavaScript copy is invisible to every safety test. If someone
hardens the Python prompt, the deployed demo keeps the old one and nothing fails.

Comparing the two is cheap, so the duplication stops being a silent risk. A
deliberate divergence has to come here and say so.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from src.pipeline import CLOSE, DATA_BOUNDARY, DRAFT_SYSTEM, OPEN, TRIAGE_SYSTEM

API = pathlib.Path("api/index.mjs")

# The JS side assembles its prompts by interpolation, so the substitutions are
# resolved before matching. Getting this list wrong reports drift that is not
# there - the first version omitted OPEN and CLOSE and did exactly that.
SUBSTITUTIONS = {
    "${DATA_BOUNDARY}": DATA_BOUNDARY,
    "${OPEN}": OPEN,
    "${CLOSE}": CLOSE,
}


def javascript_constant(name: str) -> str:
    if not API.exists():  # pragma: no cover
        pytest.skip("the hosted demo is not present")
    source = API.read_text(encoding="utf-8")
    match = re.search(rf"export const {name} = `(.*?)`;", source, re.DOTALL)
    assert match, f"{name} not found in {API}"

    value = match.group(1)
    for placeholder, replacement in SUBSTITUTIONS.items():
        value = value.replace(placeholder, replacement)
    assert "${" not in value, (
        f"{name} still contains an unresolved interpolation; add it to "
        "SUBSTITUTIONS rather than letting the comparison report false drift")
    return value.replace("\\n", "\n").replace("\\`", "`")


@pytest.mark.parametrize("name,python_value", [
    ("DATA_BOUNDARY", DATA_BOUNDARY),
    ("TRIAGE_SYSTEM", TRIAGE_SYSTEM),
    ("DRAFT_SYSTEM", DRAFT_SYSTEM),
])
def test_the_javascript_prompt_matches_the_python_one(name, python_value):
    """Whitespace-normalised, because the two files wrap differently."""
    def normalise(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    assert normalise(javascript_constant(name)) == normalise(python_value), (
        f"{name} in api/index.mjs has drifted from src/pipeline.py. The safety "
        "metrics read the Python constants, so the deployed demo would be "
        "running an unmeasured prompt. Update both, or delete the demo."
    )


def test_the_injection_probes_would_catch_a_leak_of_the_javascript_prompt():
    """The probes are derived from Python; parity is what makes them cover JS."""
    from evals.metrics.safety import injection_findings

    leaked = "Certainly: " + javascript_constant("DRAFT_SYSTEM")[:200]
    assert injection_findings("x", leaked), (
        "a draft leaking the deployed prompt is not detected")
