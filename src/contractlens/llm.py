import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import instructor
import litellm
from litellm import completion
from litellm.exceptions import APIConnectionError, RateLimitError, Timeout
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from contractlens.config import settings
from contractlens.schema import ContractExtraction

litellm.drop_params = True  # ollama ignores params like response_format edge cases gracefully

_LEDGER_PATH = Path(__file__).resolve().parents[2] / "data" / "results" / "llm_calls.jsonl"


class CostLimitExceeded(RuntimeError):
    pass


@dataclass
class SamplingConfig:
    name: str
    temperature: float
    top_p: float


@dataclass
class ExtractionResult:
    doc_id: str
    model: str
    config_name: str
    parsed: ContractExtraction | None
    error: str | None
    latency_s: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    n_attempts: int
    raw_text_chars: int = field(default=0)


def _spent_so_far() -> float:
    if not _LEDGER_PATH.exists():
        return 0.0
    total = 0.0
    with open(_LEDGER_PATH, encoding="utf-8") as fh:
        for line in fh:
            try:
                total += json.loads(line).get("cost_usd", 0.0)
            except json.JSONDecodeError:
                continue
    return total


def _log_call(result: ExtractionResult) -> None:
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LEDGER_PATH, "a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "doc_id": result.doc_id,
                    "model": result.model,
                    "config": result.config_name,
                    "ok": result.error is None,
                    "latency_s": round(result.latency_s, 3),
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "cost_usd": result.cost_usd,
                    "n_attempts": result.n_attempts,
                    "error": result.error,
                },
                ensure_ascii=False,
            )
            + "\n"
        )


SYSTEM_PROMPT = """You are a precise contract-analysis assistant. You extract structured \
fields from a (possibly messy, OCR-like or badly formatted) commercial contract excerpt. \
Only use information present in the text. If a field is not stated, use null (or an empty \
list/false where appropriate). Never invent dates, names, or jurisdictions. The contract \
text may be truncated in the middle; infer only from what is given."""

USER_PROMPT_TEMPLATE = """Extract the contract fields from the document below.

<contract_text>
{text}
</contract_text>"""


_retryable = retry_if_exception_type((APIConnectionError, RateLimitError, Timeout, TimeoutError))


def _call_once(model: str, text: str, cfg: SamplingConfig, timeout: float, max_validation_retries: int):
    # Small local models (served via Ollama) are unreliable at OpenAI-style tool
    # calling; JSON mode (response schema injected into the prompt, format=json
    # on the Ollama side) is far more robust for them. Cloud models keep the
    # default TOOLS mode, which is the most reliable structured-output path there.
    is_ollama = model.startswith("ollama/")
    # instructor.Mode.JSON (schema-in-prompt + format=json) made llama3.2:3b
    # frequently echo the JSON *schema* itself instead of filling in values
    # (~70% failure rate in testing). MD_JSON (ask for a fenced ```json block,
    # no schema echoed into the response) was far more reliable for this model.
    mode = instructor.Mode.MD_JSON if is_ollama else instructor.Mode.TOOLS
    client = instructor.from_litellm(completion, mode=mode)

    @retry(
        retry=_retryable,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _do_call():
        kwargs = dict(
            model=model,
            response_model=ContractExtraction,
            max_retries=max_validation_retries,
            timeout=timeout,
            temperature=cfg.temperature,
            top_p=cfg.top_p,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text)},
            ],
        )
        if is_ollama:
            kwargs["api_base"] = settings.ollama_api_base
            kwargs["num_ctx"] = 8192
        return client.chat.completions.create_with_completion(**kwargs)

    return _do_call()


def extract_contract(
    doc_id: str,
    text: str,
    model: str,
    cfg: SamplingConfig,
    timeout: float | None = None,
    max_validation_retries: int | None = None,
    enforce_cost_limit: bool = True,
) -> ExtractionResult:
    timeout = timeout if timeout is not None else settings.request_timeout_s
    max_validation_retries = (
        max_validation_retries if max_validation_retries is not None else settings.max_retries
    )

    if enforce_cost_limit and _spent_so_far() >= settings.cost_limit_usd:
        raise CostLimitExceeded(
            f"COST_LIMIT_USD={settings.cost_limit_usd} reached; refusing further cloud calls."
        )

    start = time.monotonic()
    parsed = None
    error = None
    prompt_tokens = completion_tokens = 0
    cost_usd = 0.0
    n_attempts = 1
    try:
        parsed, raw = _call_once(model, text, cfg, timeout, max_validation_retries)
        usage = getattr(raw, "usage", None)
        if usage:
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        # OpenRouter's own responses carry the real billed cost (computed from
        # OpenRouter's live pricing, not litellm's static map) in this hidden
        # field; litellm.completion_cost() can't look up "openrouter/<model>"
        # in its pricing table at all and raises, so prefer this when present.
        hidden_cost = getattr(raw, "_hidden_params", {}).get("response_cost")
        if hidden_cost is not None:
            cost_usd = hidden_cost
        else:
            try:
                cost_usd = litellm.completion_cost(completion_response=raw) or 0.0
            except Exception:
                cost_usd = 0.0
        n_attempts = getattr(raw, "_raw_response", None) and 1 or 1
    except Exception as exc:  # noqa: BLE001 - we want to record *any* failure and keep going
        error = f"{type(exc).__name__}: {exc}"

    latency_s = time.monotonic() - start
    result = ExtractionResult(
        doc_id=doc_id,
        model=model,
        config_name=cfg.name,
        parsed=parsed,
        error=error,
        latency_s=latency_s,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        n_attempts=n_attempts,
        raw_text_chars=len(text),
    )
    _log_call(result)
    return result
