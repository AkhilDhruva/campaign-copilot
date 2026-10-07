"""Cross-platform stand-in for the Makefile. Same target names.

    python manage.py data | test | lint | eval | api | check

Use `make <target>` if GNU make is installed; this script exists because Windows
machines often do not have it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV_PY = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PY = str(VENV_PY if VENV_PY.exists() else sys.executable)


def run(*cmd: str, env: dict | None = None) -> None:
    full_env = {**os.environ, **(env or {})}
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, env=full_env, check=True)


TARGETS = {
    "data": lambda: run(PY, "-m", "campaign_copilot.data.generate"),
    "test": lambda: (TARGETS["data"](), run(PY, "-m", "pytest", "-q", env={"MOCK_LLM": "1"})),
    "lint": lambda: run(PY, "-m", "ruff", "check", "."),
    "eval": lambda: (TARGETS["data"](), run(PY, "-m", "evals.run", env={"MOCK_LLM": "1"})),
    "api": lambda: run(PY, "-m", "uvicorn", "campaign_copilot.api.main:app", "--reload", "--port", "8000"),
    "check": lambda: (TARGETS["lint"](), TARGETS["test"](), TARGETS["eval"]()),
}


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    if target not in TARGETS:
        print(__doc__)
        print("targets:", ", ".join(TARGETS))
        sys.exit(2)
    try:
        TARGETS[target]()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
