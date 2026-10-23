# Extraction evaluation report

| model                         | config          |   valid % |   field acc |   p50 (s) |   p95 (s) |    $/doc |   $/1000 docs |
|-------------------------------|-----------------|-----------|-------------|-----------|-----------|----------|---------------|
| ollama/llama3.2:3b            | a_deterministic |      76.7 |       0.457 |     18.72 |     45.75 | 0        |         0     |
| ollama/llama3.2:3b            | b_creative      |      40   |       0.423 |     27.93 |     42.48 | 0        |         0     |
| openrouter/openai/gpt-4o-mini | a_deterministic |     100   |       0.852 |      3.27 |      8.6  | 0.000478 |         0.478 |
| openrouter/openai/gpt-4o-mini | b_creative      |     100   |       0.869 |      3    |      3.53 | 0.00043  |         0.43  |

## ollama/llama3.2:3b / a_deterministic

{
  "file": "data/results/local/a_deterministic.jsonl",
  "model": "ollama/llama3.2:3b",
  "config": "a_deterministic",
  "n_total": 30,
  "n_valid": 23,
  "valid_pct": 76.7,
  "n_graded_against_golden": 8,
  "overall_field_accuracy": 0.457,
  "field_accuracy": {
    "agreement_type": 0.75,
    "parties_f1": 0.95,
    "effective_date": 0.375,
    "governing_law": 0.0,
    "term_description": 0.125,
    "has_termination_clause": 0.75,
    "has_confidentiality_clause": 0.25
  },
  "latency_p50_s": 18.72,
  "latency_p95_s": 45.75,
  "avg_cost_usd_per_doc": 0.0,
  "cost_usd_per_1000_docs": 0.0
}

## ollama/llama3.2:3b / b_creative

{
  "file": "data/results/local/b_creative.jsonl",
  "model": "ollama/llama3.2:3b",
  "config": "b_creative",
  "n_total": 10,
  "n_valid": 4,
  "valid_pct": 40.0,
  "n_graded_against_golden": 4,
  "overall_field_accuracy": 0.423,
  "field_accuracy": {
    "agreement_type": 0.5,
    "parties_f1": 0.714,
    "effective_date": 0.25,
    "governing_law": 0.0,
    "term_description": 0.5,
    "has_termination_clause": 0.5,
    "has_confidentiality_clause": 0.5
  },
  "latency_p50_s": 27.93,
  "latency_p95_s": 42.48,
  "avg_cost_usd_per_doc": 0.0,
  "cost_usd_per_1000_docs": 0.0
}

## openrouter/openai/gpt-4o-mini / a_deterministic

{
  "file": "data/results/cloud/a_deterministic.jsonl",
  "model": "openrouter/openai/gpt-4o-mini",
  "config": "a_deterministic",
  "n_total": 10,
  "n_valid": 10,
  "valid_pct": 100.0,
  "n_graded_against_golden": 10,
  "overall_field_accuracy": 0.852,
  "field_accuracy": {
    "agreement_type": 1.0,
    "parties_f1": 0.967,
    "effective_date": 0.8,
    "governing_law": 0.7,
    "term_description": 0.6,
    "has_termination_clause": 0.9,
    "has_confidentiality_clause": 1.0
  },
  "latency_p50_s": 3.27,
  "latency_p95_s": 8.6,
  "avg_cost_usd_per_doc": 0.000478,
  "cost_usd_per_1000_docs": 0.478
}

## openrouter/openai/gpt-4o-mini / b_creative

{
  "file": "data/results/cloud/b_creative.jsonl",
  "model": "openrouter/openai/gpt-4o-mini",
  "config": "b_creative",
  "n_total": 10,
  "n_valid": 10,
  "valid_pct": 100.0,
  "n_graded_against_golden": 10,
  "overall_field_accuracy": 0.869,
  "field_accuracy": {
    "agreement_type": 1.0,
    "parties_f1": 0.98,
    "effective_date": 0.8,
    "governing_law": 0.7,
    "term_description": 0.7,
    "has_termination_clause": 0.9,
    "has_confidentiality_clause": 1.0
  },
  "latency_p50_s": 3.0,
  "latency_p95_s": 3.53,
  "avg_cost_usd_per_doc": 0.00043,
  "cost_usd_per_1000_docs": 0.43
}

