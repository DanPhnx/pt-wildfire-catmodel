"""Reproducibility entry point for the Portuguese wildfire catastrophe loss model.

Runs each phase notebook top to bottom on a fresh kernel via nbconvert, in
order, and reports what ran. A phase whose functions still raise
NotImplementedError (see notebooks/0N_*.ipynb) is a stub, not a bug, and is
skipped with a clear message rather than executed into a confusing
traceback; skip that phase in the notebook to see the exact function.

Per the PRD's reproducibility criterion: `pip install -r requirements.txt`
then `python main.py` on a fresh clone should produce the same results,
because notebook cell outputs are pinned in git and every stochastic step
(the Monte Carlo simulation, once implemented) uses a fixed random seed.

Usage
-----
    python main.py            # run every implemented phase
    python main.py --phase 1  # run one phase only (1-5)
"""

import argparse
import subprocess
import sys
from pathlib import Path

NOTEBOOKS_DIR = Path(__file__).parent / "notebooks"

PHASES = [
    (1, "01_eda.ipynb", "Data & EDA"),
    (2, "02_distribution_fitting.ipynb", "Distribution Fitting"),
    (3, "03_monte_carlo.ipynb", "Monte Carlo Simulation"),
    (4, "04_validation.ipynb", "Validation & Sensitivity"),
]

STUB_MARKER = "NotImplementedError"


def is_stub(notebook_path: Path) -> bool:
    """True if the notebook's code cells still raise NotImplementedError anywhere.

    A cheap source-text check rather than an executed check, so a stub phase
    can be detected and skipped without running it first.
    """
    import json

    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    return any(
        STUB_MARKER in "".join(cell.get("source", []))
        for cell in nb["cells"]
        if cell.get("cell_type") == "code"
    )


def run_notebook(notebook_path: Path) -> bool:
    """Execute a notebook in place via nbconvert. Returns True on success."""
    result = subprocess.run(
        [
            sys.executable, "-m", "nbconvert",
            "--to", "notebook", "--execute", "--inplace",
            "--ExecutePreprocessor.timeout=600",
            str(notebook_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stderr[-4000:], file=sys.stderr)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", type=int, choices=[p for p, _, _ in PHASES], help="run a single phase (1-5)")
    args = parser.parse_args()

    phases = [p for p in PHASES if p[0] == args.phase] if args.phase else PHASES

    print(f"Portuguese wildfire catastrophe loss model - running {len(phases)} phase(s)\n")
    ran, skipped, failed = [], [], []
    for number, filename, title in phases:
        path = NOTEBOOKS_DIR / filename
        if not path.exists():
            print(f"Phase {number} ({title}): SKIPPED - {filename} not found")
            skipped.append(number)
            continue
        if is_stub(path):
            print(f"Phase {number} ({title}): SKIPPED - not yet implemented (see {filename})")
            skipped.append(number)
            continue
        print(f"Phase {number} ({title}): running {filename} ...")
        if run_notebook(path):
            print(f"Phase {number} ({title}): done")
            ran.append(number)
        else:
            print(f"Phase {number} ({title}): FAILED - see traceback above")
            failed.append(number)

    print(f"\nSummary: ran {ran}, skipped (not implemented) {skipped}, failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
