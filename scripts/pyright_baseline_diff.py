"""Baseline-allowlist gate for pyright (`--outputjson`).

Compares the current pyright run against a committed baseline and fails only on
*net-new* diagnostics — every diagnostic already present in the baseline is
allowed through, so the existing backlog never reds the build while a regression
does. This is the typing analog of the flake8 rule-flip (leftovers A8 / A9).

Keying: each diagnostic is keyed by `(file, severity, rule, message)`, where
`file` is normalized to a repo-relative POSIX path so a Windows dev box and a
Linux CI runner produce identical keys. Diagnostics are counted as a **multiset**
(not a set), so N identical diagnostics in the baseline allow exactly N in the
current run — the (N+1)th is a regression. A key whose current count is <= its
baseline count passes; resolved baseline diagnostics simply lower the count and
never fail.

Usage:
    # Gate the current run against the committed baseline (exit 1 on regression):
    python scripts/pyright_baseline_diff.py \
        --current pyright.json --baseline docs/ci_cd_phase3/pyright-baseline.json

    # (Re)generate the committed baseline from a current run:
    python scripts/pyright_baseline_diff.py \
        --current pyright.json --baseline docs/ci_cd_phase3/pyright-baseline.json \
        --write-baseline

Stdlib only — runs under any Python the CI job already has on PATH.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

# Severities the gate tracks. Pyright also emits "information"; those are hints,
# not backlog, and are excluded so they can never red the build.
TRACKED_SEVERITIES = ("error", "warning")

REPO_ROOT = Path(__file__).resolve().parents[1]


def _normalize_path(raw: str, repo_root: Path) -> str:
    """Return ``raw`` as a repo-relative POSIX path when it lives under the repo.

    Pyright emits absolute OS-native paths in the ``file`` field. Normalizing to
    a repo-relative POSIX string makes keys identical across Windows and Linux.
    Paths outside the repo (rare — third-party) fall back to their POSIX form.
    """
    try:
        p = Path(raw)
    except (TypeError, ValueError):
        return str(raw)
    try:
        return p.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        # Not under the repo root; keep a stable POSIX rendering.
        return p.as_posix()


def _diag_key(diag: dict, repo_root: Path) -> tuple[str, str, str, str]:
    """Build the multiset key: (file, severity, rule, message)."""
    file_ = _normalize_path(diag.get("file", ""), repo_root)
    severity = str(diag.get("severity", ""))
    rule = str(diag.get("rule", ""))
    message = str(diag.get("message", ""))
    return (file_, severity, rule, message)


def counts_from_diagnostics(diagnostics: list[dict], repo_root: Path) -> Counter:
    """Counter of tracked-severity diagnostics keyed by :func:`_diag_key`."""
    counter: Counter = Counter()
    for diag in diagnostics:
        if str(diag.get("severity", "")) not in TRACKED_SEVERITIES:
            continue
        counter[_diag_key(diag, repo_root)] += 1
    return counter


def load_pyright_diagnostics(path: Path) -> list[dict]:
    """Read a pyright ``--outputjson`` file and return ``generalDiagnostics``."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("generalDiagnostics", [])


def _key_to_record(key: tuple[str, str, str, str], count: int) -> dict:
    file_, severity, rule, message = key
    return {
        "file": file_,
        "severity": severity,
        "rule": rule,
        "message": message,
        "count": count,
    }


def _record_to_key(record: dict) -> tuple[str, str, str, str]:
    return (
        str(record.get("file", "")),
        str(record.get("severity", "")),
        str(record.get("rule", "")),
        str(record.get("message", "")),
    )


def counts_to_baseline(counter: Counter) -> dict:
    """Serialize a Counter into the committed baseline structure (sorted)."""
    records = [_key_to_record(key, counter[key]) for key in counter]
    records.sort(key=lambda r: (r["file"], r["severity"], r["rule"], r["message"]))
    return {
        "_meta": {
            "tool": "pyright",
            "note": (
                "Baseline-allowlist for the typecheck CI gate (leftovers A9). "
                "Generated under the committed pyrightconfig.json "
                "(pythonVersion 3.11, pythonPlatform Windows). Regenerate with "
                "scripts/pyright_baseline_diff.py --write-baseline. Do NOT edit "
                "by hand to silence a real regression."
            ),
            "total_diagnostics": sum(counter.values()),
            "distinct_keys": len(counter),
        },
        "diagnostics": records,
    }


def baseline_to_counts(baseline: dict) -> Counter:
    """Rebuild a Counter from the committed baseline structure."""
    counter: Counter = Counter()
    for record in baseline.get("diagnostics", []):
        counter[_record_to_key(record)] += int(record.get("count", 0))
    return counter


def find_regressions(baseline: Counter, current: Counter) -> list[dict]:
    """Keys whose current count exceeds the baseline count, with the delta."""
    regressions = []
    for key, cur_count in current.items():
        base_count = baseline.get(key, 0)
        if cur_count > base_count:
            regressions.append(
                {
                    "key": key,
                    "baseline": base_count,
                    "current": cur_count,
                    "new": cur_count - base_count,
                }
            )
    regressions.sort(key=lambda r: r["key"])
    return regressions


def _print_regressions(regressions: list[dict]) -> None:
    total_new = sum(r["new"] for r in regressions)
    print(
        f"pyright baseline gate: FAIL — {total_new} net-new diagnostic instance(s) "
        f"across {len(regressions)} key(s) not in the baseline:",
        file=sys.stderr,
    )
    for r in regressions:
        file_, severity, rule, message = r["key"]
        first_line = message.splitlines()[0] if message else ""
        print(
            f"  +{r['new']} (baseline {r['baseline']} -> current {r['current']}) "
            f"[{severity}:{rule}] {file_}: {first_line}",
            file=sys.stderr,
        )
    print(
        "\nIf this is an intentional, reviewed change, regenerate the baseline:\n"
        "  python scripts/pyright_baseline_diff.py --current pyright.json "
        "--baseline docs/ci_cd_phase3/pyright-baseline.json --write-baseline",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--current",
        required=True,
        type=Path,
        help="Path to the current pyright --outputjson file.",
    )
    parser.add_argument(
        "--baseline",
        required=True,
        type=Path,
        help="Path to the committed baseline JSON.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Regenerate the baseline from --current and write it to --baseline.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repo root for path normalization (default: this script's repo).",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    current_counts = counts_from_diagnostics(
        load_pyright_diagnostics(args.current), repo_root
    )

    if args.write_baseline:
        baseline = counts_to_baseline(current_counts)
        args.baseline.write_text(
            json.dumps(baseline, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(
            f"Wrote baseline: {args.baseline} "
            f"({baseline['_meta']['total_diagnostics']} diagnostics, "
            f"{baseline['_meta']['distinct_keys']} distinct keys)."
        )
        return 0

    baseline_counts = baseline_to_counts(
        json.loads(args.baseline.read_text(encoding="utf-8"))
    )
    regressions = find_regressions(baseline_counts, current_counts)
    if regressions:
        _print_regressions(regressions)
        return 1

    print(
        f"pyright baseline gate: PASS — 0 net-new diagnostics "
        f"(baseline {sum(baseline_counts.values())}, current "
        f"{sum(current_counts.values())})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
