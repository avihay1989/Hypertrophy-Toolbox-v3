"""Focused tests for the pyright baseline-allowlist gate (leftovers A9).

Covers the contract the CI gate relies on: multiset counting (duplicate
diagnostics are not collapsed), resolved-baseline diagnostics never fail,
net-new / exceeded-count diagnostics do fail, repo-relative POSIX path
normalization, "information" severity exclusion, and the baseline round-trip.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.pyright_baseline_diff import (
    baseline_to_counts,
    counts_from_diagnostics,
    counts_to_baseline,
    find_regressions,
    main,
)

REPO = Path("/repo").resolve()


def _diag(file_, rule, message, severity="error"):
    return {"file": file_, "rule": rule, "message": message, "severity": severity}


def _abs(rel: str) -> str:
    """A repo-absolute path string for a repo-relative POSIX path."""
    return str(REPO / rel)


# --- multiset / duplicate-count behavior ------------------------------------


def test_duplicate_diagnostics_counted_as_multiset():
    diags = [
        _diag(_abs("utils/x.py"), "reportArgumentType", "bad arg"),
        _diag(_abs("utils/x.py"), "reportArgumentType", "bad arg"),
        _diag(_abs("utils/x.py"), "reportArgumentType", "bad arg"),
    ]
    counts = counts_from_diagnostics(diags, REPO)
    key = ("utils/x.py", "error", "reportArgumentType", "bad arg")
    assert counts[key] == 3


def test_exceeding_baseline_count_is_a_regression():
    from collections import Counter

    key = ("utils/x.py", "error", "reportArgumentType", "bad arg")
    base = Counter({key: 2})
    cur = Counter({key: 3})
    regressions = find_regressions(base, cur)
    assert len(regressions) == 1
    assert regressions[0]["new"] == 1
    assert regressions[0]["baseline"] == 2
    assert regressions[0]["current"] == 3


def test_equal_count_is_not_a_regression():
    from collections import Counter

    key = ("utils/x.py", "error", "reportArgumentType", "bad arg")
    assert find_regressions(Counter({key: 2}), Counter({key: 2})) == []


# --- resolved-baseline behavior ---------------------------------------------


def test_resolved_baseline_diagnostic_does_not_fail():
    from collections import Counter

    key = ("utils/x.py", "error", "reportArgumentType", "bad arg")
    # Baseline had 2; current run has 0 (fixed) -> no regression.
    assert find_regressions(Counter({key: 2}), Counter()) == []


def test_fewer_than_baseline_is_not_a_regression():
    from collections import Counter

    key = ("utils/x.py", "error", "reportArgumentType", "bad arg")
    assert find_regressions(Counter({key: 3}), Counter({key: 1})) == []


def test_brand_new_key_is_a_regression():
    from collections import Counter

    new_key = ("utils/new.py", "error", "reportCallIssue", "boom")
    regressions = find_regressions(Counter(), Counter({new_key: 1}))
    assert len(regressions) == 1
    assert regressions[0]["new"] == 1
    assert regressions[0]["baseline"] == 0


# --- path normalization + severity filtering --------------------------------


def test_paths_normalized_to_repo_relative_posix():
    diags = [_diag(_abs("routes/workout_plan.py"), "reportOptionalSubscript", "m")]
    counts = counts_from_diagnostics(diags, REPO)
    assert ("routes/workout_plan.py", "error", "reportOptionalSubscript", "m") in counts


def test_information_severity_excluded():
    diags = [
        _diag(_abs("utils/x.py"), "reportArgumentType", "real", severity="error"),
        _diag(_abs("utils/x.py"), "reportGeneralTypeIssues", "hint",
              severity="information"),
    ]
    counts = counts_from_diagnostics(diags, REPO)
    assert sum(counts.values()) == 1
    assert all(key[1] == "error" for key in counts)


def test_warning_severity_tracked():
    diags = [_diag(_abs("utils/x.py"), "reportSelfClsParameterName", "w",
                   severity="warning")]
    counts = counts_from_diagnostics(diags, REPO)
    assert counts[("utils/x.py", "warning", "reportSelfClsParameterName", "w")] == 1


# --- baseline round-trip -----------------------------------------------------


def test_baseline_roundtrip_preserves_counts():
    from collections import Counter

    counter = Counter(
        {
            ("utils/x.py", "error", "reportArgumentType", "a"): 3,
            ("routes/y.py", "warning", "reportSelfClsParameterName", "b"): 1,
        }
    )
    baseline = counts_to_baseline(counter)
    assert baseline["_meta"]["total_diagnostics"] == 4
    assert baseline["_meta"]["distinct_keys"] == 2
    assert baseline_to_counts(baseline) == counter


# --- main() end-to-end on temp files ----------------------------------------


def _write_pyright(path: Path, diags):
    path.write_text(
        json.dumps({"generalDiagnostics": diags, "summary": {"errorCount": len(diags)}}),
        encoding="utf-8",
    )


def test_main_write_then_pass(tmp_path):
    current = tmp_path / "pyright.json"
    baseline = tmp_path / "baseline.json"
    diags = [
        _diag(_abs("utils/x.py"), "reportArgumentType", "bad arg"),
        _diag(_abs("utils/x.py"), "reportArgumentType", "bad arg"),
    ]
    _write_pyright(current, diags)

    rc_write = main(
        ["--current", str(current), "--baseline", str(baseline),
         "--write-baseline", "--repo-root", str(REPO)]
    )
    assert rc_write == 0
    assert baseline.exists()

    rc_compare = main(
        ["--current", str(current), "--baseline", str(baseline),
         "--repo-root", str(REPO)]
    )
    assert rc_compare == 0


def test_main_detects_regression(tmp_path, capsys):
    current = tmp_path / "pyright.json"
    baseline = tmp_path / "baseline.json"
    base_diags = [_diag(_abs("utils/x.py"), "reportArgumentType", "bad arg")]
    _write_pyright(current, base_diags)
    main(["--current", str(current), "--baseline", str(baseline),
          "--write-baseline", "--repo-root", str(REPO)])

    # Now a run with an extra, brand-new diagnostic.
    regressed = base_diags + [_diag(_abs("utils/new.py"), "reportCallIssue", "boom")]
    _write_pyright(current, regressed)
    rc = main(["--current", str(current), "--baseline", str(baseline),
               "--repo-root", str(REPO)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "FAIL" in err
    assert "utils/new.py" in err


def test_main_resolved_baseline_passes(tmp_path):
    current = tmp_path / "pyright.json"
    baseline = tmp_path / "baseline.json"
    base_diags = [
        _diag(_abs("utils/x.py"), "reportArgumentType", "bad arg"),
        _diag(_abs("utils/gone.py"), "reportOptionalSubscript", "fixed me"),
    ]
    _write_pyright(current, base_diags)
    main(["--current", str(current), "--baseline", str(baseline),
          "--write-baseline", "--repo-root", str(REPO)])

    # The second diagnostic is resolved; current has only the first.
    _write_pyright(current, base_diags[:1])
    rc = main(["--current", str(current), "--baseline", str(baseline),
               "--repo-root", str(REPO)])
    assert rc == 0
