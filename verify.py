#!/usr/bin/env python3
"""Replay a standing report from its committed evidence.

    python3 verify.py reports/<report-dir>

Reads the report's manifest, raw kernel axiom report, and claim map; checks
the report file against the hash the manifest records; re-runs the frozen
engine in ./engine; and compares the recomputed verdict to the committed
verdict.json field by field. Exit 0 = the verdict is exactly what this
evidence produces; any difference is printed and exits 1.

Python 3.10+, no dependencies beyond the standard library.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.claim_audit import ClaimMap, audit_manifest, read_report


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    d = sys.argv[1].rstrip("/\\")
    manifest = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8-sig"))
    committed = json.load(open(os.path.join(d, "verdict.json"), encoding="utf-8"))
    raw_map = json.load(open(os.path.join(d, "claim_map.json"), encoding="utf-8"))

    expected_map_id = raw_map.pop("map_id")
    cmap = ClaimMap(project=raw_map["project"], authors=tuple(raw_map["authors"]),
                    obligations={k: tuple(v) for k, v in raw_map["obligations"].items()},
                    claims=raw_map["claims"], claim_order=tuple(raw_map["claim_order"]),
                    claim_standing=raw_map["claim_standing"],
                    decl_obligations={k: tuple(v) for k, v in raw_map["decl_obligations"].items()},
                    kernel_source_suffix=raw_map["kernel_source_suffix"],
                    clean_axioms=frozenset(raw_map["clean_axioms"]))
    if cmap.map_id != expected_map_id:
        fail(f"claim map does not hash to its stated id: {cmap.map_id} != {expected_map_id}")

    rpt_name = manifest["lean"]["axioms_report"]
    rpt_path = os.path.join(d, rpt_name)
    raw = open(rpt_path, "rb").read()
    recorded = manifest["lean"].get("axioms_report_sha256")
    if recorded:
        actual = hashlib.sha256(raw).hexdigest().lower()
        if actual != recorded.lower().replace("sha256:", ""):
            fail("axiom report bytes do not match the manifest hash")
    text, _ = read_report(rpt_path)

    _, _, _, recomputed = audit_manifest(manifest, cmap, report_text=text)

    diffs = []
    for k in sorted(set(committed) | set(recomputed)):
        if committed.get(k) != recomputed.get(k):
            diffs.append(k)
    if diffs:
        for k in diffs:
            print(f"  field {k!r}:\n    committed:  {committed.get(k)}\n    recomputed: {recomputed.get(k)}")
        fail(f"{len(diffs)} verdict field(s) differ")

    print(f"OK: verdict replays exactly from the evidence")
    print(f"    project   {recomputed['project']} @ {recomputed['commit'][:12]}")
    print(f"    standing  {recomputed['standing']}")
    print(f"    claim map {recomputed['claim_map_id']}  policy {recomputed['policy_id']}")


if __name__ == "__main__":
    main()
