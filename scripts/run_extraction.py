"""Run baseline structured extraction over the contract corpus.

Usage:
    uv run python scripts/run_extraction.py --model local --config a --docs all
    uv run python scripts/run_extraction.py --model cloud --config a,b --docs golden
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from contractlens.config import settings  # noqa: E402
from contractlens.llm import CostLimitExceeded, SamplingConfig, extract_contract  # noqa: E402

CONTRACTS_DIR = ROOT / "data" / "contracts"
GOLDEN_PATH = ROOT / "data" / "golden" / "ground_truth.json"
RESULTS_DIR = ROOT / "data" / "results"

CONFIGS = {
    "a": SamplingConfig(name="a_deterministic", temperature=0.0, top_p=1.0),
    "b": SamplingConfig(name="b_creative", temperature=0.7, top_p=0.9),
}


def load_doc_ids(scope: str) -> list[str]:
    if scope == "golden":
        with open(GOLDEN_PATH, encoding="utf-8") as fh:
            return sorted(json.load(fh)["items"].keys())
    return sorted(p.stem for p in CONTRACTS_DIR.glob("contract_*.txt"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["cloud", "local"], required=True)
    parser.add_argument("--config", default="a", help="comma-separated: a,b")
    parser.add_argument("--docs", choices=["all", "golden"], default="golden")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    model = settings.cloud_model if args.model == "cloud" else settings.local_model
    if args.model == "cloud" and not settings.has_cloud_key():
        print(
            f"No API key found for cloud model '{model}'. "
            "Set the relevant *_API_KEY in .env first. Aborting.",
            file=sys.stderr,
        )
        sys.exit(1)

    cfg_names = args.config.split(",")
    doc_ids = load_doc_ids(args.docs)
    if args.limit:
        doc_ids = doc_ids[: args.limit]

    out_dir = RESULTS_DIR / args.model
    out_dir.mkdir(parents=True, exist_ok=True)

    for cfg_name in cfg_names:
        cfg = CONFIGS[cfg_name]
        out_path = out_dir / f"{cfg.name}.jsonl"
        print(f"=== model={model} config={cfg.name} docs={len(doc_ids)} -> {out_path} ===")
        with open(out_path, "w", encoding="utf-8") as out_fh:
            for i, doc_id in enumerate(doc_ids, 1):
                text = (CONTRACTS_DIR / f"{doc_id}.txt").read_text(encoding="utf-8")
                try:
                    result = extract_contract(doc_id, text, model, cfg)
                except CostLimitExceeded as exc:
                    print(f"STOPPED: {exc}")
                    break
                status = "OK" if result.error is None else f"ERR: {result.error}"
                print(
                    f"[{i}/{len(doc_ids)}] {doc_id}: {status} "
                    f"({result.latency_s:.1f}s, ${result.cost_usd:.5f})"
                )
                record = {
                    "doc_id": result.doc_id,
                    "model": result.model,
                    "config": result.config_name,
                    "latency_s": result.latency_s,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "cost_usd": result.cost_usd,
                    "error": result.error,
                    "extraction": json.loads(result.parsed.model_dump_json()) if result.parsed else None,
                }
                out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
