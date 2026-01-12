# Contributing to Vestigo

Thanks for wanting to contribute! This document explains how to make
changes, what to test, and how to submit improvements so maintainers can
review them quickly.

## Quick checklist

- Fork the repository and create a topic branch for your change
- Run tests and linters (see below) and make sure your change is small and focused
- Open a PR describing the problem, the change, and any manual verification steps

## Code style

- Python: follow PEP8. Use black/isort where appropriate. Keep functions small and well-documented.
- JavaScript/TypeScript (frontend): follow the project ESLint/Prettier rules in `frontend/`.

## How to run the common tools

1. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run unit-style checks (if present):

   ```bash
   # example: run pytest if you add tests
   pytest -q
   # run flake8 or black to check style
   flake8 . || true
   black --check . || true
   ```

3. Running major scripts for manual verification

   - Generate a small dataset (use `--limit` to avoid long runs):

     ```bash
     python3 generate_dataset.py --input-dir ghidra_output --output test_dataset.csv --limit 5
     ```

   - Run a small Qiling batch extractor locally:

     ```bash
     python3 qiling_analysis/batch_extract_features.py --dataset-dir ./dataset_binaries --output-dir ./batch_results --limit 2
     ```

   - Start backend locally for integration testing:

     ```bash
     cd backend
     pip install -r requirements.txt
     uvicorn main:app --reload
     ```

## Tests

- This repository contains scripts but has limited structured unit tests. When
  adding functionality, include at least one unit test for the main logic and
  one integration-style test where possible.

- Put Python tests under `tests/` and name them `test_*.py`. Use pytest.

## Pull request process

1. Open a PR against `main` with a clear title and description. Explain why the
   change is needed and list any manual steps used to verify it.
2. Keep PRs small and focused; large architectural changes should be discussed
   via an issue before implementation.
3. Maintain backward compatibility where practical and document breaking changes.

## Issues and feature requests

- Use the issue templates (`Bug report` or `Feature request`) so items are labeled
  automatically for triage.
- Include a clear summary, steps to reproduce (if a bug), and expected vs actual
  behaviour. For features, include rough UX and acceptance criteria.

## Security disclosures

- If you find a security bug, please open a private issue and mark it as
  confidential or contact the maintainers directly. Do not post public PoCs
  until the issue is addressed.

## Thank you

We welcome any contribution — from fixes and tests to documentation and new
pipeline components. If you're unsure where to start, check open issues labeled
`good first issue` or ask in an issue thread for guidance.
