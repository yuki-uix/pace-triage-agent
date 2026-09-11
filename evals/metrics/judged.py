"""The judged metrics and the argument for each.

Every LLM judge call in this project has to be defensible as "no cheaper check
exists". The main comparison has three such metrics; meta-evaluation adds a
fourth, source-backed domain check. The reason is written next to each one. The
rubrics and evaluation steps are hand-written rather than generated from a
criteria string, because an auto-generated rubric is an unexamined rubric and
the bands are where the judgement actually lives.
"""

from __future__ import annotations

from deepeval.metrics import GEval
from deepeval.metrics.g_eval.utils import Rubric
from deepeval.test_case import LLMTestCaseParams

INPUT = LLMTestCaseParams.INPUT
OUTPUT = LLMTestCaseParams.ACTUAL_OUTPUT
CONTEXT = LLMTestCaseParams.CONTEXT

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

# Actionability is deliberately not a synonym for making promises. A safe reply
# can still tell the customer what evidence is missing, who needs to check it,
# what the customer can do now, and what event will produce the next update.
# Conversely, an invented three-day SLA is specific but not a usable plan.
ACTIONABILITY_STEPS = [
    "Read the enquiry and identify the outcome the customer needs, any urgency, "
    "and every question that calls for a next step rather than an explanation.",
    "Read the reply and extract the operational path it gives: what the customer "
    "can do now, what information is needed, what the insurer will check, and "
    "what event or condition leads to the next status update.",
    "Distinguish a concrete conditional path from a generic assurance. 'We need "
    "the policy schedule before confirming this' is useful when it names the "
    "missing evidence; 'we will look into it' alone is not.",
    "Do not reward a definite deadline, completed action or promised resolution "
    "merely for sounding specific when the enquiry supplies no basis for it. "
    "Unsafe certainty is not a substitute for an executable next step.",
    "Score only actionability. Do not deduct for warmth, writing style or a "
    "technical insurance error already handled by another metric, except when "
    "that error makes the stated next step unusable.",
]

ACTIONABILITY_RUBRIC = [
    Rubric(score_range=(0, 2), expected_outcome=(
        "The customer is left without a usable next step, or a fabricated "
        "outcome, deadline or completed action is presented instead of a safe "
        "operational path.")),
    Rubric(score_range=(3, 5), expected_outcome=(
        "The reply says the matter will be checked or followed up, but leaves "
        "material gaps about what is needed, what happens next, or when the "
        "customer will know that the case has moved.")),
    Rubric(score_range=(6, 8), expected_outcome=(
        "The reply gives a clear and safe next step, required information and "
        "the main conditional path, with one minor omission such as an unclear "
        "owner, channel or next status point.")),
    Rubric(score_range=(9, 10), expected_outcome=(
        "The customer can act without guessing: the reply clearly states the "
        "current evidence boundary, concrete next actions, required information "
        "and the condition or supported timing for the next update, without "
        "inventing a resolution.")),
]

# This is intentionally separate from commitment groundedness. A reply can make
# no promise and still state a law, policy term or claims process incorrectly.
# CONTEXT contains only versioned claims from `knowledge/`; its first item also
# names the company and policy evidence that is absent.
DOMAIN_STEPS = [
    "Extract every insurance, legal and operational claim in the draft reply. "
    "Include statements about benefits, dividends, surrender, claims, privacy, "
    "complaints, fees, forms, documents, channels and processing state.",
    "For each claim, identify an item in the supplied context that supports or "
    "contradicts it. Do not use unstated background knowledge and do not treat a "
    "general regulatory principle as an insurer-specific product rule.",
    "Apply the evidence boundary in the context. A definite statement about an "
    "individual policy, an insurer's app or form, a document checklist, an SLA, "
    "a billing record or CRM state is unsupported when that evidence is absent.",
    "Distinguish a careful conditional next step from a fact. 'We need to check "
    "your policy' is safe; 'your policy allows this' is not supported merely "
    "because the statement is plausible for some policies.",
    "Score factual and evidential reliability, not helpfulness or tone. One "
    "materially wrong legal rule or one policy-specific instruction on which a "
    "customer could rely should dominate several harmless correct sentences.",
]

DOMAIN_RUBRIC = [
    Rubric(score_range=(0, 2), expected_outcome=(
        "The reply contains a contradicted legal or insurance claim, or gives "
        "multiple unsupported policy/company instructions as settled facts.")),
    Rubric(score_range=(3, 5), expected_outcome=(
        "The general direction is plausible, but at least one material claim "
        "requires absent policy, company-process or system evidence.")),
    Rubric(score_range=(6, 8), expected_outcome=(
        "Claims are consistent with the supplied sources and mostly respect "
        "their scope, with only a minor overstatement or missing qualification.")),
    Rubric(score_range=(9, 10), expected_outcome=(
        "Every material claim is supported by the supplied evidence, accurately "
        "scoped, or explicitly deferred pending the missing evidence.")),
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


def actionability(model, threshold: float = 0.7) -> GEval:
    """Whether a safe reply still gives the customer a usable path forward."""
    return GEval(
        name="actionability",
        evaluation_params=[INPUT, OUTPUT],
        evaluation_steps=ACTIONABILITY_STEPS,
        rubric=ACTIONABILITY_RUBRIC,
        model=model,
        threshold=threshold,
    )


def domain_correctness(model, threshold: float = 0.9) -> GEval:
    """Source-backed correctness without pretending general rules are a policy."""
    return GEval(
        name="domain correctness",
        evaluation_params=[INPUT, OUTPUT, CONTEXT],
        evaluation_steps=DOMAIN_STEPS,
        rubric=DOMAIN_RUBRIC,
        model=model,
        threshold=threshold,
    )


JUDGED_METRICS = (commitment_groundedness, tone_match, summary_quality)
# Kept outside JUDGED_METRICS until its own blind human validation is complete.
# This prevents an experimental dimension from silently changing the recorded
# 2x2 comparison, composite weights or hard-bar verdicts.
EXPERIMENTAL_METRICS = (actionability,)
# The recorded 2x2 comparison predates the reference pack. Keep its instrument
# stable; the next paid run may deliberately promote this metric into the main
# matrix after the source-backed judge itself has been human-validated.
META_EVALUATION_METRICS = JUDGED_METRICS + (domain_correctness,)
