"""
runner.py

Executes a run manifest and produces JUnit-style XML results. This is the
component that replaces the old encode-and-bounce-the-device step: instead of
handing a blob to a proprietary binary, it actually runs the tests.

Execution model per case:
  - If the case has a `command`, it is run as a subprocess. Exit code 0 is a
    pass; any other exit code is a fail; a timeout is a fail with a timeout
    message; a command that cannot be launched at all is "blocked".
  - If the case has no command, it is simulated (demo mode) so the app is
    runnable out of the box with no external scripts.

The runner is deliberately UI-agnostic. It takes an optional `on_result`
callback so a caller (the UI) can live-update as each case finishes, but it
has no Tk imports and can be driven from a plain script or a test of its own.
"""

import subprocess
import time
import random
import logging
import xml.etree.ElementTree as ET


class TestRunner:
    """Runs the cases in a run manifest and writes JUnit XML."""

    def __init__(self, dry_run=False, demo_seed=None):
        # dry_run: build the manifest and report "would run" without executing.
        self.dry_run = dry_run
        self._rng = random.Random(demo_seed)

    def run(self, run_manifest, on_result=None):
        """
        Execute every case in `run_manifest`.

        on_result, if given, is called as on_result(case_id, result, ms) after
        each case so the UI can update incrementally.

        Returns a results dict suitable for write_junit().
        """
        suite = run_manifest["suite"]
        results = {"suite": suite, "cases": []}

        for case in run_manifest["cases"]:
            if self.dry_run:
                outcome = ("blocked", 0, "dry run — not executed")
            elif case.get("command"):
                outcome = self._run_command(case)
            else:
                outcome = self._simulate(case)

            result, duration_ms, message = outcome
            results["cases"].append(
                {
                    "id": case["id"],
                    "name": case["name"],
                    "result": result,
                    "duration_ms": duration_ms,
                    "message": message,
                }
            )
            if on_result:
                on_result(case["id"], result, duration_ms)

        return results

    def _run_command(self, case):
        start = time.monotonic()
        try:
            completed = subprocess.run(
                case["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=case.get("timeout_s", 60),
            )
        except subprocess.TimeoutExpired:
            ms = int((time.monotonic() - start) * 1000)
            return ("fail", ms, f"timed out after {case.get('timeout_s', 60)}s")
        except OSError as exc:
            ms = int((time.monotonic() - start) * 1000)
            return ("blocked", ms, f"could not launch: {exc}")

        ms = int((time.monotonic() - start) * 1000)
        if completed.returncode == 0:
            return ("pass", ms, "")
        tail = (completed.stderr or completed.stdout or "").strip()[-500:]
        return ("fail", ms, f"exit {completed.returncode}: {tail}")

    def _simulate(self, case):
        """Deterministic-ish fake run for cases with no command."""
        time.sleep(self._rng.uniform(0.02, 0.12))
        ms = self._rng.randint(40, 900)
        roll = self._rng.random()
        if roll < 0.78:
            return ("pass", ms, "")
        if roll < 0.95:
            return ("fail", ms, "simulated assertion failure")
        return ("blocked", ms, "simulated environment issue")

    @staticmethod
    def write_junit(results, path="results.xml"):
        """Write a JUnit-style XML report from a results dict."""
        cases = results["cases"]
        failures = sum(1 for c in cases if c["result"] == "fail")
        blocked = sum(1 for c in cases if c["result"] == "blocked")
        total_time = sum(c["duration_ms"] for c in cases) / 1000.0

        testsuites = ET.Element("testsuites")
        testsuite = ET.SubElement(
            testsuites,
            "testsuite",
            {
                "name": results["suite"],
                "tests": str(len(cases)),
                "failures": str(failures),
                "errors": str(blocked),
                "time": f"{total_time:.3f}",
            },
        )
        for c in cases:
            tc = ET.SubElement(
                testsuite,
                "testcase",
                {
                    "name": c["name"],
                    "classname": results["suite"],
                    "time": f"{c['duration_ms'] / 1000.0:.3f}",
                },
            )
            if c["result"] == "fail":
                fail = ET.SubElement(tc, "failure", {"message": c["message"][:200]})
                fail.text = c["message"]
            elif c["result"] == "blocked":
                err = ET.SubElement(tc, "error", {"message": c["message"][:200]})
                err.text = c["message"]

        ET.ElementTree(testsuites).write(path, encoding="utf-8", xml_declaration=True)
        logging.info(f"JUnit results written to '{path}'.")
        return path
