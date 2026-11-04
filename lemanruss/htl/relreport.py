"""Markdown report of `lemanruss verify` JSON files (docs/results-release-v2.0-rc1.md)."""

from __future__ import annotations

import json
from pathlib import Path

Json = dict[str, object]


def _d(x: object) -> Json:
    assert isinstance(x, dict)
    return x


def _one(rep: Json) -> list[str]:
    a, e, b = _d(rep["a_integrity"]), _d(rep["e_separation"]), _d(rep["b_leak"])
    c, d = _d(rep["c_function"]), _d(rep["d_rareness"])
    res = d["results"]
    assert isinstance(res, list)
    leaks = b["leaks"]
    odd = b["odd_names"]
    assert isinstance(leaks, list) and isinstance(odd, list)
    pats = _d(b["inserter_name_patterns_scrubbed"])
    words = b["words"]
    assert isinstance(words, list)
    out = [
        f"## {rep['release']}: {'PASS' if rep['ok'] else 'FAIL'}",
        "",
        f"- (a) integrity: {a['files']} files in SHA256SUMS, {a['circuits']} circuits in the "
        f"manifest; hashes, sizes, counts per base and per restructuring: "
        f"{'all equal' if a['ok'] else 'PROBLEMS ' + str(a['problems'])}.",
        f"- (b) label leak: {b['circuits_scanned']} circuits scanned for "
        f"{', '.join(str(w) for w in words)}; leaks {len(leaks)}, infected-only names not in "
        f"the clean style {len(odd)}, hits native to a base (also in its clean circuit, not "
        f"counted) {b['native_hits']}; circuits or manifest holding `odin3_edit` event text "
        f"{b['odin3_edit_circuits']} + {b['odin3_edit_manifest']}. "
        f"Result: {'NO LEAK' if b['ok'] else 'LEAK'}.",
        f"- (c) function: {c['infected']} infected circuits: witness found {c['witness']}, "
        f"Odin III confirms trigger high and payload changes the output {c['odin_fired']}; ABC "
        f"equivalence to the clean twin with the trigger held at 0: {c['forced_off_cec']}; "
        f"{c['restructured']} restructured circuits against their source: "
        f"{c['restructured_cec']}; unproven: {c['restructured_unproven']}.",
        f"- (d) rareness: {len(res)} infected circuits re-measured (strata "
        f"{d['strata']}); within tolerance {sum(1 for r in res if _d(r)['ok'])}/{len(res)}.",
        f"- (e) separation: {e['clean']} clean, {e['infected']} infected labels in "
        f"`answer_key/labels.json` only; "
        f"{'no problems' if e['ok'] else 'PROBLEMS ' + str(e['problems'])}.",
        "",
        "Inserter name patterns that were scrubbed (digits as N, count of names in the key):",
        "",
        *[f"- `{k}`: {v}" for k, v in pats.items()],
        "",
    ]
    return out


def render_reports(paths: list[Path], title: str = "Release v2.0-rc1: verify report "
                   "(2026-10-31)") -> str:
    lines = [f"# {title}", "",
             "Produced by `lemanruss verify` (spec section 10.3) on the packaged release "
             "directories; every number comes from the files on disk.", ""]
    for p in paths:
        lines += _one(_d(json.loads(p.read_text(encoding="utf-8"))))
    return "\n".join(lines)
