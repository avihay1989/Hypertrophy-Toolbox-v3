"""Run summary regression checks via MCP Puppeteer server.

This script talks to `@modelcontextprotocol/server-puppeteer` over stdio
JSON-RPC and executes browser-level checks for:
1) Effective/raw set columns render together without a counting-mode switch.
2) Session summary inflation when multiple workout_log rows exist for one plan row.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List


BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:5001")


def nearly_equal(a: float, b: float, epsilon: float = 0.05) -> bool:
    return abs(a - b) <= epsilon


@dataclass
class TestResult:
    name: str
    passed: bool
    details: List[Dict[str, Any]]


class PuppeteerMcpClient:
    def __init__(self) -> None:
        self._proc = subprocess.Popen(
            ["cmd", "/c", "npx", "-y", "@modelcontextprotocol/server-puppeteer"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._next_id = 1
        self._initialize()

    def _initialize(self) -> None:
        init_resp = self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "summary-regression-mcp", "version": "1.0"},
            },
        )
        if "error" in init_resp:
            raise RuntimeError(f"MCP initialize failed: {init_resp['error']}")
        self.notify("notifications/initialized", {})

    def notify(self, method: str, params: Dict[str, Any]) -> None:
        obj = {"jsonrpc": "2.0", "method": method, "params": params}
        if not self._proc.stdin:
            raise RuntimeError("MCP stdin is unavailable")
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        obj = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        request_id = self._next_id
        self._next_id += 1

        if not self._proc.stdin or not self._proc.stdout:
            raise RuntimeError("MCP pipes are unavailable")
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

        line = self._proc.stdout.readline()
        if not line:
            stderr = ""
            if self._proc.stderr:
                try:
                    stderr = self._proc.stderr.read()
                except Exception:
                    stderr = ""
            raise RuntimeError(f"No response from MCP server. stderr={stderr[:1000]}")

        resp = json.loads(line)
        if resp.get("id") != request_id and "method" in resp:
            # Ignore out-of-band notifications and read the next response.
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("Expected response after notification but got EOF")
            resp = json.loads(line)
        return resp

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.request("tools/call", {"name": name, "arguments": arguments})
        if "error" in resp:
            raise RuntimeError(f"Tool call failed ({name}): {resp['error']}")
        return resp["result"]

    def navigate(self, url: str) -> None:
        self.call_tool("puppeteer_navigate", {"url": url})

    def select(self, selector: str, value: str) -> None:
        self.call_tool("puppeteer_select", {"selector": selector, "value": value})

    def evaluate(self, script: str) -> str:
        result = self.call_tool("puppeteer_evaluate", {"script": script})
        content = result.get("content") or []
        if not content:
            raise RuntimeError("Evaluate returned no content")
        text = content[0].get("text", "")
        match = re.search(r"Execution result:\n([\s\S]*?)\n\nConsole output:", text)
        if not match:
            raise RuntimeError(f"Unexpected evaluate output format: {text[:500]}")
        return match.group(1).strip()

    def evaluate_json(self, script_returning_json_string: str) -> Any:
        raw = self.evaluate(script_returning_json_string)
        first = json.loads(raw)
        if isinstance(first, str):
            return json.loads(first)
        return first

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


def weekly_capture_script() -> str:
    return """
    (async () => {
      const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline) {
        const rows = Array.from(document.querySelectorAll('#weekly-summary-table tr'))
          .map((row) => Array.from(row.querySelectorAll('td')).map((td) => (td.textContent || '').trim()))
          .filter((cells) => cells.length >= 5);
        if (rows.length > 0) {
          return JSON.stringify(rows.map((cells) => ({
            muscle: cells[0],
            effective: Number.parseFloat(cells[1]) || 0,
            raw: Number.parseFloat(cells[2]) || 0,
            routines: Number.parseInt(cells[3], 10) || 0
          })));
        }
        await sleep(150);
      }
      return JSON.stringify([]);
    })()
    """.strip()


def session_capture_script() -> str:
    return """
    (async () => {
      const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
      const deadline = Date.now() + 15000;
      while (Date.now() < deadline) {
        const rows = Array.from(document.querySelectorAll('#session-summary-table tr'))
          .map((row) => Array.from(row.querySelectorAll('td')).map((td) => (td.textContent || '').trim()))
          .filter((cells) => cells.length >= 6);
        if (rows.length > 0) {
          return JSON.stringify(rows.map((cells) => ({
            routine: cells[0],
            muscle: cells[1],
            effective: Number.parseFloat(cells[2]) || 0,
            raw: Number.parseFloat(cells[3]) || 0
          })));
        }
        await sleep(150);
      }
      return JSON.stringify([]);
    })()
    """.strip()


def session_api_script() -> str:
    return """
    (async () => {
      const response = await fetch('/session_summary?counting_mode=effective&contribution_mode=total', {
        headers: { Accept: 'application/json' }
      });
      const data = await response.json();
      return JSON.stringify(data);
    })()
    """.strip()


def test_weekly_effective_raw_columns_present(client: PuppeteerMcpClient) -> TestResult:
    client.navigate(f"{BASE_URL}/weekly_summary")
    rows = client.evaluate_json(weekly_capture_script())

    diffs: List[Dict[str, Any]] = []
    for row in rows:
        if row["effective"] <= 0 or row["raw"] <= 0:
            diffs.append(
                {
                    "muscle": row["muscle"],
                    "effective": row["effective"],
                    "raw": row["raw"],
                }
            )

    return TestResult(
        name="weekly_effective_raw_columns_present",
        passed=len(rows) > 0 and len(diffs) == 0,
        details=diffs,
    )


def test_session_effective_raw_columns_present(client: PuppeteerMcpClient) -> TestResult:
    client.navigate(f"{BASE_URL}/session_summary")
    rows = client.evaluate_json(session_capture_script())

    diffs: List[Dict[str, Any]] = []
    for row in rows:
        if row["effective"] <= 0 or row["raw"] <= 0:
            diffs.append(
                {
                    "routine": row["routine"],
                    "muscle": row["muscle"],
                    "effective": row["effective"],
                    "raw": row["raw"],
                }
            )

    return TestResult(
        name="session_effective_raw_columns_present",
        passed=len(rows) > 0 and len(diffs) == 0,
        details=diffs,
    )


def test_session_not_inflated_by_logs(client: PuppeteerMcpClient) -> TestResult:
    client.navigate(f"{BASE_URL}/session_summary")
    payload = client.evaluate_json(session_api_script())
    rows = payload.get("session_summary", [])

    target = None
    for row in rows:
        if row.get("routine") == "Seed Routine" and row.get("muscle_group") == "Chest":
            target = row
            break

    if not target:
        return TestResult(
            name="session_sets_not_multiplied_by_log_rows",
            passed=False,
            details=[{"error": "Seed row not found in /session_summary payload"}],
        )

    expected_effective_sets = 10.2
    observed = float(target.get("effective_sets", 0))
    passed = nearly_equal(observed, expected_effective_sets)
    return TestResult(
        name="session_sets_not_multiplied_by_log_rows",
        passed=passed,
        details=[
            {
                "routine": "Seed Routine",
                "muscle": "Chest",
                "expected_effective_sets": expected_effective_sets,
                "observed_effective_sets": observed,
                "session_count": target.get("session_count"),
            }
        ],
    )


def main() -> int:
    client = PuppeteerMcpClient()
    try:
        results = [
            test_weekly_effective_raw_columns_present(client),
            test_session_effective_raw_columns_present(client),
            test_session_not_inflated_by_logs(client),
        ]
    finally:
        client.close()

    output = {
        "baseUrl": BASE_URL,
        "results": [
            {"name": r.name, "passed": r.passed, "details": r.details} for r in results
        ],
    }
    print(json.dumps(output, indent=2))
    return 1 if any(not r.passed for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
