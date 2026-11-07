# lemanruss (Leman Russ III)

Leman Russ III: Hardware Trojan Library (HTL), insertion at HDL and netlist level, and Seeker's
Dilemma style benchmark generation, on Odin III. Part of Yggdrasil III. Defensive benchmark
research (Trust-Hub / Seeker's Dilemma style): this repo builds Trojans to detect, not to deploy.

Spec: `docs/specs/2026-10-31-htl-design.md`. Plan: `docs/plans/2026-10-31-htl-plan.md`.

The base install is `odin3` only (never on PyPI; installed `--no-deps -e .` from the Odin III
checkout's `plugins/python`). No LLM calls anywhere in this repo.

## Setup

    python3 -m venv .venv && .venv/bin/pip install ruff mypy cffi
    export ODIN3_ROOT=<odin3 checkout> ODIN3_LIB=$ODIN3_ROOT/build/rel-main3/libodin3.so
    export PYTHONPATH=$ODIN3_ROOT/plugins/python
    export MYPYPATH=$ODIN3_ROOT/plugins/python  # else mypy --strict treats odin3 as an untyped install

## Build, test, lint

    .venv/bin/python -m unittest discover -s tests -t . -v
    .venv/bin/ruff check .
    .venv/bin/mypy --strict lemanruss tests

Run all three before every push (CI runs the same three jobs).

## Benchmark build

    .venv/bin/lemanruss build --base-dir <designs> --out work/htl-out --manifest work/htl-out/manifest.json

## Rules

- Never edit the Odin III repo. Leman Russ depends on the `odin3` package only; a missing Odin III
  API (e.g. netlist mutation beyond `read_blif`/`write_blif`/`run_script`) is an open question for
  the controller, not a workaround here, and is logged in the spec's gap notes.
- Until the Odin III `scoap` pass merges, rare-net site selection uses signal probability from
  Odin III `sim` random vectors only; say so in any output that depends on it.
- Python 3.11+, no 3.12-only syntax. ruff and `mypy --strict` clean, line length 100. No
  `# noqa`/`# type: ignore` without Peter's approval. Tests are `unittest` under `tests/`; Odin III
  tests use `skipUnless(odin_available())`.
- Labels (clean/infected, trigger id, payload id) are the answer key: keep them in a separate file
  from the circuit the detector sees (manifest's `labels.json`, never embedded in the netlist/RTL).
- Never commit to `main`. Branch, PR, squash merge on green CI. Commit and push after each green
  step (`git push origin HEAD:<branch>`, never a bare push).
- Never delete files: no `rm`, no `git clean`, no `git worktree remove`.
- No `cd X && ...` compounds; use `git -C` / absolute paths.
- Merge, never rebase; no force push.
- No LLM calls, no VPR, in this round.
