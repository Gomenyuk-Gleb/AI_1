# ContractLens — checkpoint (кроки 1–2)

Baseline-екстракція структурованих полів з «брудних» комерційних договорів
(реальні SEC EDGAR filings, той самий домен, що й CUAD v1, який наскрізний
проєкт ContractLens використовує далі), порівняння хмарної та локальної моделі.

## Що зроблено

1. **Схема + baseline-промпт** (`src/contractlens/schema.py`, `src/contractlens/llm.py`)
   — Pydantic-схема на 8 полів (enum `agreement_type`, вкладений список
   `parties: list[Party]` де `Party.role` теж enum, плюс `key_obligations: list[str]`),
   підключення через LiteLLM зі structured output (`instructor`), retry
   (tenacity, мережеві помилки + instructor-retry на невалідний JSON) і timeout.
2. **Друга модель + заміри** — локальна модель через Ollama (`ollama/llama3.2:3b`)
   поруч із хмарною (`CLOUD_MODEL` з `.env`, за замовчуванням Gemini Flash) через
   той самий `llm.py`; дві конфігурації семплінгу (`a_deterministic`: temp=0,
   top_p=1 та `b_creative`: temp=0.7, top_p=0.9); метрики: точність по полях на
   golden set, % валідних відповідей, latency p50/p95, $/1000 документів.

## Дані

- `data/contracts/contract_0XX.txt` — 30 договорів (10+ типів), з
  `data/contracts_manifest.json` (джерело, назва, довжина).
- `data/golden/ground_truth.json` — 10 вручну розмічених golden-записів.
- `data/results/<model>/<config>.jsonl` — сирі результати прогонів.
- `data/results/llm_calls.jsonl` — журнал кожного LLM-виклику (вартість, токени,
  латентність) — це і є бюджетний ledger для `COST_LIMIT_USD`.

## Запуск

### Через Makefile

```bash
make setup           # uv venv, залежності, .env з прикладу
# відредагуйте .env: додайте ключ і ollama pull llama3.2:3b
make run             # локальна модель, config a+b, golden set + звіт метрик
make extract-local-all  # локальна модель, baseline, усі 30 договорів
make extract-cloud   # хмарна модель, config a+b, golden set (потрібен ключ)
make eval            # перерахувати метрики за всіма data/results/*/*.jsonl
make test            # юніт-тести eval-функцій
make cost            # сумарні витрати з data/results/llm_calls.jsonl
```

### Вручну

```bash
uv venv --python 3.11 && uv pip install -e .
cp .env.example .env   # додайте GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY
ollama pull llama3.2:3b  # або інша модель, вказана в LOCAL_MODEL

source .venv/bin/activate

# Локальна модель, обидві конфігурації, на golden set (для метрик)
python scripts/run_extraction.py --model local --config a,b --docs golden

# Локальна модель, baseline-конфігурація, на всіх 30 договорах
python scripts/run_extraction.py --model local --config a --docs all

# Хмарна модель (потрібен ключ у .env) — той самий набір команд з --model cloud
python scripts/run_extraction.py --model cloud --config a,b --docs golden
python scripts/run_extraction.py --model cloud --config a --docs all

# Метрики
python eval/evaluate.py "data/results/*/*.jsonl" --report eval/reports/stage1_2.md
```

## Результати

Див. `eval/reports/stage1_2.md` (генерується командою вище) і
`docs/decisions.md` для пояснення вибору схеми, промпту та архітектурних рішень
(включно з проблемами, які виникли при підключенні локальної моделі і як вони
вирішені).

## Бюджет

`COST_LIMIT_USD` (за замовчуванням $4) перевіряється перед кожним викликом за
сумою з `data/results/llm_calls.jsonl`; при досягненні ліміту скрипт зупиняється
і зберігає часткові результати. Локальна модель завжди коштує $0.
