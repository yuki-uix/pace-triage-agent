"""The judge model, and the record of whether it actually scored continuously.

`docs/02-metrics.md` asks GEval to weight the score token by `top_logprobs`
rather than take a discrete integer, and requires the write-up to say whether
the provider actually supplied them - because if it does not, the metric
silently degrades to a coarser instrument and the results look the same.

So this wrapper counts. Every call records whether logprobs came back, and
`JudgeUsage.continuous_scoring_rate` is reported alongside the scores.

**Choosing the judge was decided by that requirement.** ADR-007 named
`deepseek-v4-pro`, chosen for family separation. It rejects the parameter
outright: `400 InternalError.Algo.InvalidParameter: The parameters logprobs is
not supported`. So does MiniMax. `kimi-k3` supports it but generated the
dataset, and a generator scoring its own output is the self-preference bias the
separation exists to avoid. `glm-5.2` supports logprobs and is a fourth family -
not the models under test, not the generator, not the second-opinion labeller.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from deepeval.models.base_model import DeepEvalBaseLLM
from openai import AsyncOpenAI, OpenAI


@dataclass
class JudgeUsage:
    """Measured per run. The scoring-mode figure is a disclosure, not a stat."""

    calls: int = 0
    with_logprobs: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def continuous_scoring_rate(self) -> float:
        """Share of judge calls that could be scored continuously."""
        return self.with_logprobs / self.calls if self.calls else 0.0

    def as_dict(self) -> dict:
        return {
            "calls": self.calls,
            "with_logprobs": self.with_logprobs,
            "continuous_scoring_rate": self.continuous_scoring_rate,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "failures": self.failures,
        }


class DashScopeJudge(DeepEvalBaseLLM):
    """A DeepEval model backed by the OpenAI-compatible endpoint.

    `generate_raw_response` is what makes GEval score continuously; without it
    GEval falls back to the integer the model wrote. Implementing it is not
    optional if the metric is to be what the metrics document says it is.
    """

    def __init__(self, model: str | None = None, usage: JudgeUsage | None = None):
        self.model = model or os.environ["JUDGE_MODEL"]
        self.usage = usage or JudgeUsage()
        self._client = OpenAI(
            api_key=os.environ["DASHSCOPE_API_KEY"],
            base_url=os.environ["DASHSCOPE_BASE_URL"],
        )
        self._async_client = AsyncOpenAI(
            api_key=os.environ["DASHSCOPE_API_KEY"],
            base_url=os.environ["DASHSCOPE_BASE_URL"],
        )

    def load_model(self, *args, **kwargs) -> "DashScopeJudge":
        return self

    def get_model_name(self, *args, **kwargs) -> str:
        return self.model

    def _record(self, response) -> None:
        usage = response.usage
        details = getattr(usage, "completion_tokens_details", None)
        self.usage.calls += 1
        self.usage.prompt_tokens += usage.prompt_tokens
        self.usage.completion_tokens += usage.completion_tokens
        self.usage.reasoning_tokens += getattr(details, "reasoning_tokens", 0) or 0

        logprobs = getattr(response.choices[0], "logprobs", None)
        if logprobs and getattr(logprobs, "content", None):
            self.usage.with_logprobs += 1

    def _request(self, prompt: str, top_logprobs: int | None):
        kwargs: dict = {"model": self.model, "max_tokens": 4096,
                        "messages": [{"role": "user", "content": prompt}]}
        if top_logprobs is not None:
            kwargs.update(logprobs=True, top_logprobs=top_logprobs)
        return kwargs

    def generate(self, prompt: str, *args, **kwargs) -> str:
        response = self._client.chat.completions.create(
            **self._request(prompt, None))
        self._record(response)
        return response.choices[0].message.content or ""

    async def a_generate(self, prompt: str, *args, **kwargs) -> str:
        response = await self._async_client.chat.completions.create(
            **self._request(prompt, None))
        self._record(response)
        return response.choices[0].message.content or ""

    def generate_raw_response(self, prompt: str, top_logprobs: int = 5, **kwargs):
        response = self._client.chat.completions.create(
            **self._request(prompt, top_logprobs))
        self._record(response)
        return response, 0.0

    async def a_generate_raw_response(self, prompt: str, top_logprobs: int = 5,
                                      **kwargs):
        response = await self._async_client.chat.completions.create(
            **self._request(prompt, top_logprobs))
        self._record(response)
        return response, 0.0
