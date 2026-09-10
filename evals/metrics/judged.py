"""The three metrics that genuinely need a judge, and the argument for each.

Every LLM judge call in this project has to be defensible as "no cheaper check
exists". These three are, and the reason is written next to each one. The
rubrics and the evaluation steps are hand-written rather than generated from a
criteria string, because an auto-generated rubric is an unexamined rubric and
the bands are where the judgement actually lives.
"""

from __future__ import annotations

from deepeval.metrics import GEval
from deepeval.metrics.g_eval.utils import Rubric
from deepeval.test_case import LLMTestCaseParams

INPUT = LLMTestCaseParams.INPUT
OUTPUT = LLMTestCaseParams.ACTUAL_OUTPUT

# Why this one cannot be a set comparison: a fabricated commitment need contain
# no fabricated entity. "We will get back to you shortly" invents nothing an
# extractor can find and still promises something the enquiry does not support.
# Entity groundedness catches the invented policy number; only a reader catches
# the invented obligation.
COMMITMENT_STEPS = [
    "Read the customer's email and list every fact it establishes: what has "
    "happened, what has been submitted, what deadlines the customer states.",
    "Read the draft reply and list every commitment it makes: timeframes, "
    "refunds, outcomes, entitlements, escalations, promises to act.",
    "For each commitment, decide whether the email supports it, or whether the "
    "reply has introduced it. A commitment the insurer has not made before is "
    "introduced even when it sounds routine.",
    "Treat an unsupported timeframe, a promised outcome or a stated entitlement "
    "as the most serious kind: for a regulated insurer these are contractual "
    "exposure, not tone.",
    "Acknowledging receipt, explaining the next step in general terms, or saying "
    "a team will review something are not commitments unless they attach a "
    "deadline or an outcome.",
]

COMMITMENT_RUBRIC = [
    Rubric(score_range=(0, 2), expected_outcome=(
        "The reply promises an outcome, an entitlement or a specific timeframe "
        "the email does not support - a claim will be approved, a refund will "
        "arrive by a date, a benefit applies.")),
    Rubric(score_range=(3, 5), expected_outcome=(
        "The reply introduces a softer commitment the email does not support: "
        "an implied service level, an assurance that something will be "
        "resolved, a suggestion that a decision is likely.")),
    Rubric(score_range=(6, 8), expected_outcome=(
        "The reply commits only to what the email supports, but phrasing in one "
        "place could be read as more than the insurer has undertaken.")),
    Rubric(score_range=(9, 10), expected_outcome=(
        "Every commitment in the reply is supported by the email or is a "
        "generic acknowledgement carrying no deadline or outcome.")),
]

# Why this one cannot be a regex: tone is a relation between the reply and the
# situation, not a word list. "We understand this is frustrating" is warmth in a
# complaint and padding in an urgent claim where the customer needs a decision.
TONE_STEPS = [
    "Establish the situation from the customer's email: is there a deadline or "
    "financial consequence in motion, or is this a routine request?",
    "For an urgent situation, expect a formal and efficient reply: it should "
    "lead with the action being taken, avoid padding, and not spend its opening "
    "on sympathy the customer cannot use.",
    "For a routine situation, expect warmth and helpfulness: a brusque, clipped "
    "reply is a failure here even if every fact in it is correct.",
    "Judge the fit between register and situation, not the presence of polite "
    "phrases. A reply can be full of courtesy and still be wrong in tone.",
    "Do not reward or penalise length on its own.",
]

TONE_RUBRIC = [
    Rubric(score_range=(0, 3), expected_outcome=(
        "The register works against the situation: chatty or padded where the "
        "customer faces a deadline, or curt where they are upset or confused.")),
    Rubric(score_range=(4, 6), expected_outcome=(
        "Broadly appropriate but uneven - an urgent reply that opens with "
        "several lines of sympathy before the action, or a routine reply that "
        "reads as a form letter.")),
    Rubric(score_range=(7, 8), expected_outcome=(
        "Register fits the situation, with a phrase or two that sits slightly "
        "wrong.")),
    Rubric(score_range=(9, 10), expected_outcome=(
        "Register fits the situation throughout: urgent handled formally and "
        "efficiently, routine handled warmly, neither overdone.")),
]

# Why this one cannot be a length check: length is checkable and is not the
# failure. The failure is a summary that reads plausibly while adding something
# the email did not say - which is what makes a reviewer trust it and skim.
SUMMARY_STEPS = [
    "Read the customer's email, then the summary written for the reviewer.",
    "Check every claim in the summary against the email. A summary that adds a "
    "motive, a cause or a detail not in the email fails, however plausible.",
    "Check that the summary carries what a reviewer needs to triage the case: "
    "what is being asked for, and any deadline or consequence.",
    "Penalise a summary that is longer than two sentences, and penalise one so "
    "short that the reviewer would have to read the email anyway.",
    "Do not reward a summary for elegance; it is a working note, not prose.",
]

SUMMARY_RUBRIC = [
    Rubric(score_range=(0, 3), expected_outcome=(
        "The summary states something the email does not, or omits the request "
        "or the deadline that makes the case what it is.")),
    Rubric(score_range=(4, 6), expected_outcome=(
        "Factually contained but the reviewer would still have to read the "
        "email to know what to do, or it runs well past two sentences.")),
    Rubric(score_range=(7, 8), expected_outcome=(
        "Contained and useful, with a minor omission or a little too much "
        "detail.")),
    Rubric(score_range=(9, 10), expected_outcome=(
        "Two sentences or fewer, every claim traceable to the email, and enough "
        "for a reviewer to triage without opening it.")),
]


def commitment_groundedness(model, threshold: float = 0.98) -> GEval:
    """The high-severity half of groundedness that a set comparison cannot see."""
    return GEval(
        name="commitment groundedness",
        evaluation_params=[INPUT, OUTPUT],
        evaluation_steps=COMMITMENT_STEPS,
        rubric=COMMITMENT_RUBRIC,
        model=model,
        threshold=threshold,
    )


def tone_match(model, threshold: float = 0.7) -> GEval:
    return GEval(
        name="tone match",
        evaluation_params=[INPUT, OUTPUT],
        evaluation_steps=TONE_STEPS,
        rubric=TONE_RUBRIC,
        model=model,
        threshold=threshold,
    )


def summary_quality(model, threshold: float = 0.7) -> GEval:
    return GEval(
        name="summary quality",
        evaluation_params=[INPUT, OUTPUT],
        evaluation_steps=SUMMARY_STEPS,
        rubric=SUMMARY_RUBRIC,
        model=model,
        threshold=threshold,
    )


JUDGED_METRICS = (commitment_groundedness, tone_match, summary_quality)
