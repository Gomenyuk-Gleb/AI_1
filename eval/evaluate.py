"""Compute field-level accuracy, validity %, latency and cost metrics for a
run produced by scripts/run_extraction.py, against the golden set.

Usage:
    uv run python eval/evaluate.py data/results/local/a_deterministic.jsonl
    uv run python eval/evaluate.py data/results/local/*.jsonl --report eval/reports/stage1.md
"""
import argparse
import glob
import json
import statistics
from pathlib import Path

from rapidfuzz import fuzz
from tabulate import tabulate

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = ROOT / "data" / "golden" / "ground_truth.json"

FUZZY_THRESHOLD = 75.0


def norm(s):
    return (s or "").strip().lower()


def date_match(pred, gold):
    if gold is None:
        return pred is None
    return norm(pred) == norm(gold)


def text_match(pred, gold):
    if gold is None:
        return pred is None
    if pred is None:
        return False
    return fuzz.WRatio(norm(pred), norm(gold)) >= FUZZY_THRESHOLD


def bool_match(pred, gold):
    return bool(pred) == bool(gold)


def enum_match(pred, gold):
    return norm(pred) == norm(gold)


def parties_f1(pred_parties, gold_parties):
    gold_names = [norm(p["name"]) for p in gold_parties]
    pred_names = [norm(p["name"]) for p in (pred_parties or [])]
    if not gold_names and not pred_names:
        return 1.0
    if not pred_names or not gold_names:
        return 0.0
    matched_gold = set()
    matched_pred = set()
    for i, pn in enumerate(pred_names):
        for j, gn in enumerate(gold_names):
            if j in matched_gold:
                continue
            if fuzz.WRatio(pn, gn) >= FUZZY_THRESHOLD:
                matched_gold.add(j)
                matched_pred.add(i)
                break
    precision = len(matched_pred) / len(pred_names)
    recall = len(matched_gold) / len(gold_names)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def score_record(extraction: dict, gold: dict) -> dict:
    return {
        "agreement_type": enum_match(extraction.get("agreement_type"), gold["agreement_type"]),
        "parties_f1": parties_f1(extraction.get("parties"), gold["parties"]),
        "effective_date": date_match(extraction.get("effective_date"), gold["effective_date"]),
        "governing_law": text_match(extraction.get("governing_law"), gold["governing_law"]),
        "term_description": text_match(extraction.get("term_description"), gold["term_description"]),
        "has_termination_clause": bool_match(
            extraction.get("has_termination_clause"), gold["has_termination_clause"]
        ),
        "has_confidentiality_clause": bool_match(
            extraction.get("has_confidentiality_clause"), gold["has_confidentiality_clause"]
        ),
    }


def percentile(values, pct):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * pct
    f, c = int(k), min(int(k) + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def evaluate_file(path: str, golden: dict) -> dict:
    records = [json.loads(line) for line in open(path, encoding="utf-8")]
    n_total = len(records)
    n_valid = sum(1 for r in records if r["extraction"] is not None)
    latencies = [r["latency_s"] for r in records]
    costs = [r["cost_usd"] for r in records]

    field_scores: dict[str, list[float]] = {}
    graded = 0
    for r in records:
        gold = golden.get(r["doc_id"])
        if gold is None or r["extraction"] is None:
            continue
        graded += 1
        scores = score_record(r["extraction"], gold)
        for k, v in scores.items():
            field_scores.setdefault(k, []).append(float(v))

    field_means = {k: (statistics.mean(v) if v else None) for k, v in field_scores.items()}
    overall = statistics.mean(field_means.values()) if field_means else None

    return {
        "file": path,
        "model": records[0]["model"] if records else None,
        "config": records[0]["config"] if records else None,
        "n_total": n_total,
        "n_valid": n_valid,
        "valid_pct": round(100 * n_valid / n_total, 1) if n_total else None,
        "n_graded_against_golden": graded,
        "overall_field_accuracy": round(overall, 3) if overall is not None else None,
        "field_accuracy": {k: round(v, 3) if v is not None else None for k, v in field_means.items()},
        "latency_p50_s": round(percentile(latencies, 0.5), 2) if latencies else None,
        "latency_p95_s": round(percentile(latencies, 0.95), 2) if latencies else None,
        "avg_cost_usd_per_doc": round(statistics.mean(costs), 6) if costs else None,
        "cost_usd_per_1000_docs": round(statistics.mean(costs) * 1000, 3) if costs else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    files = []
    for p in args.paths:
        files.extend(glob.glob(p))

    golden = json.load(open(GOLDEN_PATH, encoding="utf-8"))["items"]

    summaries = [evaluate_file(f, golden) for f in files]

    table_rows = [
        [
            s["model"],
            s["config"],
            s["valid_pct"],
            s["overall_field_accuracy"],
            s["latency_p50_s"],
            s["latency_p95_s"],
            s["avg_cost_usd_per_doc"],
            s["cost_usd_per_1000_docs"],
        ]
        for s in summaries
    ]
    headers = [
        "model",
        "config",
        "valid %",
        "field acc",
        "p50 (s)",
        "p95 (s)",
        "$/doc",
        "$/1000 docs",
    ]
    table = tabulate(table_rows, headers=headers, tablefmt="github")
    print(table)
    print()
    for s in summaries:
        print(f"--- {s['model']} / {s['config']} per-field accuracy ---")
        for k, v in s["field_accuracy"].items():
            print(f"  {k}: {v}")
        print()

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("# Extraction evaluation report\n\n")
            fh.write(table + "\n\n")
            for s in summaries:
                fh.write(f"## {s['model']} / {s['config']}\n\n")
                fh.write(json.dumps(s, ensure_ascii=False, indent=2))
                fh.write("\n\n")
        print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
