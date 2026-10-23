# ContractLens checkpoint (кроки 1-2) — зручні команди над scripts/run_extraction.py
# та eval/evaluate.py. Повний опис параметрів дивіться в README.md.
#
# Типовий порядок дій:
#   make setup              (один раз)
#   # відредагувати .env, зробити ollama pull
#   make run                (локальна модель на golden set + метрики)
#   make extract-local-all  (локальна модель, усі 30 договорів)
#   make extract-cloud      (хмарна модель, коли є ключ)

PYTHON := .venv/bin/python

.PHONY: help setup run extract-local extract-local-all extract-cloud eval test cost clean

help:
	@echo "Доступні команди:"
	@echo "  make setup              — створити .venv (uv), встановити залежності, згенерувати .env з .env.example"
	@echo "  make run                — локальна модель, обидві конфігурації семплінгу (a,b), golden set (10 договорів) + перерахунок метрик"
	@echo "  make extract-local      — те саме, що перша половина 'run': лише прогін локальної моделі на golden set, без перерахунку метрик"
	@echo "  make extract-local-all  — локальна модель, baseline-конфігурація (a), ВСІ 30 договорів (крок 1: 'проженіть усі тексти')"
	@echo "  make extract-cloud      — хмарна модель (CLOUD_MODEL з .env), обидві конфігурації, golden set; потребує API-ключ у .env"
	@echo "  make eval               — перерахувати метрики (valid %, accuracy по полях, latency p50/p95, $$/1000 докс) за ВСІМА файлами в data/results/*/*.jsonl і записати eval/reports/stage1_2.md"
	@echo "  make test               — юніт-тести для функцій порівняння в eval/evaluate.py (pytest)"
	@echo "  make cost               — сумарні витрати $$ за весь час з журналу data/results/llm_calls.jsonl (бюджетний ledger, COST_LIMIT_USD)"
	@echo "  make clean              — прибрати __pycache__, .pytest_cache, egg-info (НЕ чіпає .venv і data/results)"

# Створює віртуальне середовище (uv, Python 3.11), ставить проєкт у editable-режимі
# (щоб `import contractlens` працював без переустановки після правок коду),
# і готує .env з шаблону, якщо його ще немає.
setup:
	uv venv --python 3.11
	uv pip install -e .
	@test -f .env || cp .env.example .env
	@echo "Done. Edit .env with your cloud API key, then: ollama pull llama3.2:3b"

# Швидка демонстрація: прогін локальної моделі (extract-local) одразу з
# перерахунком метрик (eval). Саме це варто запускати першим після setup.
run: extract-local eval

# Крок 2 домашнього завдання: локальна модель через Ollama, ДВІ конфігурації
# семплінгу (a_deterministic: temp=0/top_p=1 та b_creative: temp=0.7/top_p=0.9),
# лише на 10 golden-договорах — бо тільки для них є ручна розмітка (ground_truth.json)
# і можна порахувати accuracy по полях, а не тільки % валідного JSON.
extract-local:
	$(PYTHON) scripts/run_extraction.py --model local --config a,b --docs golden

# Крок 1 домашнього завдання: baseline-конфігурація, але вже на ВСІХ 30
# договорах (вимога "проженіть усі тексти та збережіть результати").
# Метрики якості по полях рахуються лише там, де є golden-розмітка
# (10 з 30), решта враховується тільки у % валідного JSON.
extract-local-all:
	$(PYTHON) scripts/run_extraction.py --model local --config a --docs all

# Той самий прогін, що extract-local, але через CLOUD_MODEL з .env
# (наприклад gemini/gemini-flash-latest). Падає з поясненням, якщо в .env
# немає відповідного API-ключа — щоб не спалювати бюджет даремно.
extract-cloud:
	$(PYTHON) scripts/run_extraction.py --model cloud --config a,b --docs golden

# Бере всі сирі результати прогонів (data/results/<model>/<config>.jsonl),
# звіряє з golden-розміткою і друкує/зберігає таблицю: valid %, accuracy по
# кожному полю схеми, latency p50/p95, вартість за документ і за 1000 документів.
# Можна запускати повторно будь-коли — вона нічого не перераховує з нуля,
# тільки читає вже збережені .jsonl.
eval:
	$(PYTHON) eval/evaluate.py "data/results/*/*.jsonl" --report eval/reports/stage1_2.md

# Юніт-тести для допоміжних функцій порівняння (fuzzy-match дат/тексту,
# F1 по сторонах договору тощо) з eval/evaluate.py — не чіпають жодну модель,
# працюють миттєво й безкоштовно.
test:
	$(PYTHON) -m pytest tests/ -q

# Сумує поле cost_usd з кожного рядка data/results/llm_calls.jsonl — це
# журнал АБСОЛЮТНО КОЖНОГО виклику LLM (успішного чи ні), який веде
# src/contractlens/llm.py і за яким перевіряється COST_LIMIT_USD.
cost:
	@$(PYTHON) -c "import json; total=sum(json.loads(l).get('cost_usd',0) for l in open('data/results/llm_calls.jsonl')); print(f'Total spent so far: \$${total:.4f}')"

# Прибирає тимчасові артефакти Python (кеш байткоду, кеш pytest, egg-info).
# НЕ видаляє .venv і НЕ видаляє data/results — це вже отримані результати,
# а не сміття.
clean:
	rm -rf .pytest_cache src/contractlens_hw1.egg-info
	find . -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +
