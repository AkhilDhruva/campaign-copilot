# Campaign Copilot. Works with GNU make on macOS/Linux and with Git Bash on Windows.
# Every target below is a plain command you can also run by hand.

PY ?= .venv/Scripts/python
ifeq ($(wildcard .venv/Scripts/python.exe),)
PY := .venv/bin/python
endif

.PHONY: setup data test lint eval dev api web check

setup:            ## create venv and install everything
	python -m venv .venv
	$(PY) -m pip install -q -e ".[dev]"

data:             ## build the synthetic Northwind database
	$(PY) -m campaign_copilot.data.generate

test: data        ## run unit tests (offline, MOCK_LLM=1)
	MOCK_LLM=1 $(PY) -m pytest -q

lint:             ## ruff
	$(PY) -m ruff check .

eval: data        ## run the 20 golden goals and print a score table
	MOCK_LLM=1 $(PY) -m evals.run

api:              ## start the FastAPI backend
	$(PY) -m uvicorn campaign_copilot.api.main:app --reload --port 8000

web:              ## start the React dev server
	cd frontend && npm run dev

check: lint test eval   ## what CI runs
