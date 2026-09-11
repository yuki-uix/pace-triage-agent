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

# Instrument v2 is evidence-aware and deliberately separate from the recorded
# v1 metric. It cannot replace v1 until its own frozen validation has passed.
COMMITMENT_V2_STEPS = [
    "Read the customer email, the draft reply and every supplied evidence item. "
    "Separate customer-stated facts, public regulatory rules and the synthetic "
    "internal service contract; each source class has a different scope.",
    "List every undertaking in the draft: a deadline, outcome, entitlement, "
    "completed action, service route, required input, owner, confirmation or "
    "promise to act. A customer request is not itself evidence that the insurer "
    "has agreed to the requested outcome.",
    "For each undertaking, identify its support. It may be supported by a prior "
    "commitment in the email, an applicable public rule, or a selected internal "
    "service entry. General regulation cannot establish an individual policy "
    "term, account state, internal route or completed action.",
    "Treat a service-contract step as permission to describe that conditional "
    "process, not proof it has already happened. 'Reply with the statement and "
    "Billing will compare it' can be supported; 'we opened case ABC and your "
    "refund is approved' needs case-specific evidence.",
    "Distinguish a safe conditional result from a promised outcome. 'If the "
    "review confirms a duplicate, we will explain the applicable refund path' "
    "does not promise a refund. 'We will refund it' does.",
    "Do not penalise a customer-observable confirmation, information request or "
    "review result when the selected service entry explicitly authorises it. Do "
    "penalise an invented fixed SLA, case reference, contact address, completed "
    "system action, policy entitlement or guaranteed resolution.",
    "Score commitment support only. Do not reward vagueness and do not penalise "
    "a supported operational path for being specific; actionability scores the "
    "quality and completeness of that path separately.",
]

COMMITMENT_V2_RUBRIC = [
    Rubric(score_range=(0, 2), expected_outcome=(
        "The reply promises an unsupported outcome, entitlement or fixed "
        "timeframe, or claims a case-specific action or status already exists "
        "when neither the email nor supplied evidence establishes it.")),
    Rubric(score_range=(3, 5), expected_outcome=(
        "The main direction is plausible, but the reply adds a softer unsupported "
        "assurance, internal route, completion state or service level, or uses a "
        "general source beyond its stated scope.")),
    Rubric(score_range=(6, 8), expected_outcome=(
        "Material undertakings are supported by the email or applicable evidence "
        "and remain conditional where needed, with one minor overstatement or "
        "missing qualification.")),
    Rubric(score_range=(9, 10), expected_outcome=(
        "Every undertaking is traceable to the email or applicable supplied "
        "evidence, respects source scope, and does not turn an authorised process "
        "into a completed action or guaranteed case outcome.")),
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

# Instrument v3. Actionability measures whether the reply supplies a concrete
# operational path.
# It deliberately does not judge whether a stated deadline, completed action or
# promised outcome is supported: commitment groundedness owns that question.
# Keeping the two dimensions orthogonal lets the evaluation distinguish a vague
# but safe reply from a highly actionable reply built on an unsafe promise.
ACTIONABILITY_STEPS = [
    "Read the enquiry and identify the outcome the customer needs, any urgency, "
    "and every question that calls for a next step rather than an explanation.",
    "Read the reply and extract the operational path it gives: what the customer "
    "can do now, what information is needed, what the insurer will check, and "
    "what event or condition leads to the next status update.",
    "Use four control points where applicable: (1) an immediate customer action "
    "or an explicit statement that no action is required now; (2) the required "
    "inputs; (3) a usable submission channel or responsible owner; and (4) a "
    "customer-observable event, condition or date for the next status update.",
    "First identify every independent customer request that needs operational "
    "guidance. Score the whole reply, not only its strongest branch. If any such "
    "request is entirely unaddressed, the reply cannot score above 8; if the "
    "unaddressed request is the main purpose of the enquiry, it cannot score "
    "above 5.",
    "Distinguish a concrete operational path from a generic assurance. 'Submit "
    "the policy schedule through the portal, then claims will review it' is "
    "actionable; 'we will look into it' alone is not.",
    "Replying to the current email is a usable channel when the reply says what "
    "to send. Bare references to an app, online service, a form or customer "
    "service are not complete routes when the customer must ask again for the "
    "actual entry point or instructions.",
    "Apply the band gates before choosing an exact score. If the customer can "
    "only request instructions or trigger a hand-off and still cannot carry out "
    "the main request, the maximum is 5 even when that hand-off has an owner or "
    "will produce another message.",
    "A promise to review or contact the customer is not itself a next-status "
    "control point. It needs a customer-observable trigger, result state or "
    "date; a preferred time of day without a date or trigger is not timing.",
    "Customer-observable means the reply explicitly says the customer will "
    "receive or see a confirmation, request, result or status. An internal event "
    "such as 'we will process it', 'the review will find' or 'refund depends on "
    "the review' is not observable unless the reply says how the customer learns "
    "that it happened; without that, the maximum is 8.",
    "Judge the specificity of a stated deadline, completed action or promised "
    "resolution as part of the path, without deciding whether the enquiry "
    "supports it. Unsupported commitments are penalised by commitment "
    "groundedness, not by this metric.",
    "Score only actionability. Do not deduct for warmth, writing style, "
    "commitment support or technical insurance correctness handled by other "
    "metrics, except when wording is so incomplete that no action can be taken.",
]

ACTIONABILITY_RUBRIC = [
    Rubric(score_range=(0, 2), expected_outcome=(
        "The customer cannot initiate even the first useful step from the "
        "reply: it gives no usable action or route and no explicit no-action "
        "state tied to a defined review.")),
    Rubric(score_range=(3, 5), expected_outcome=(
        "The customer can request instructions or start a hand-off, but cannot "
        "yet carry out the main request from the reply; or two or more material "
        "control points remain unclear.")),
    Rubric(score_range=(6, 8), expected_outcome=(
        "The customer can carry out the main request or enter a defined review "
        "path, but one material control point remains unclear, such as required "
        "input, usable channel or owner, or a customer-observable next status.")),
    Rubric(score_range=(9, 10), expected_outcome=(
        "All applicable control points are present: immediate action or an "
        "explicit no-action state, required inputs, a usable channel or owner, "
        "and a customer-observable condition, result state or date for the next "
        "update. Support is scored separately under commitment groundedness.")),
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


def commitment_groundedness_v2(model, threshold: float = 0.9) -> GEval:
    """Evidence-aware commitment support; experimental until blind validation."""
    return GEval(
        name="commitment groundedness v2",
        evaluation_params=[INPUT, OUTPUT, CONTEXT],
        evaluation_steps=COMMITMENT_V2_STEPS,
        rubric=COMMITMENT_V2_RUBRIC,
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
    """Whether the reply gives the customer a concrete operational path."""
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
# The preregistered, disjoint held-out validation for instrument v3 passed. It
# is therefore available in an explicit shadow profile, while JUDGED_METRICS
# remains the immutable instrument used by the recorded 2x2 comparison.
SHADOW_JUDGED_METRICS = JUDGED_METRICS + (actionability,)
EXPERIMENTAL_METRICS = ()
EVIDENCE_EXPERIMENTAL_METRICS = (commitment_groundedness_v2,)
# The recorded 2x2 comparison predates the reference pack. Keep its instrument
# stable; the next paid run may deliberately promote this metric into the main
# matrix after the source-backed judge itself has been human-validated.
META_EVALUATION_METRICS = JUDGED_METRICS + (domain_correctness,)
