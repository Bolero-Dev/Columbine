"""Tests for TestRunner: execution outcomes, dry run, and JUnit output."""

import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, ".")
from runner import TestRunner


def make_manifest(cases):
    return {"version": 1, "suite": "Smoke", "cases": cases}


def case(id_, command="", timeout_s=60):
    return {"id": id_, "name": id_, "command": command,
            "tags": [], "timeout_s": timeout_s}


class TestCommandExecution:
    def test_exit_zero_is_pass(self):
        results = TestRunner().run(make_manifest([case("ok", "exit 0")]))
        assert results["cases"][0]["result"] == "pass"

    def test_nonzero_exit_is_fail(self):
        results = TestRunner().run(make_manifest([case("bad", "exit 3")]))
        record = results["cases"][0]
        assert record["result"] == "fail"
        assert "exit 3" in record["message"]

    def test_timeout_is_fail_with_message(self):
        results = TestRunner().run(
            make_manifest([case("slow", "sleep 5", timeout_s=1)])
        )
        record = results["cases"][0]
        assert record["result"] == "fail"
        assert "timed out" in record["message"]

    def test_failure_message_includes_output_tail(self):
        results = TestRunner().run(
            make_manifest([case("noisy", "echo boom >&2; exit 1")])
        )
        assert "boom" in results["cases"][0]["message"]


class TestDryRun:
    def test_dry_run_executes_nothing(self):
        results = TestRunner(dry_run=True).run(
            make_manifest([case("ok", "exit 0"), case("sim")])
        )
        assert all(c["result"] == "blocked" for c in results["cases"])
        assert all("dry run" in c["message"] for c in results["cases"])


class TestSimulation:
    def test_no_command_is_simulated_deterministically_with_seed(self):
        manifest = make_manifest([case(f"c{i}") for i in range(6)])
        first = TestRunner(demo_seed=42).run(manifest)
        second = TestRunner(demo_seed=42).run(manifest)
        assert first == second

    def test_simulated_results_are_valid_outcomes(self):
        results = TestRunner(demo_seed=7).run(
            make_manifest([case(f"c{i}") for i in range(10)])
        )
        assert all(
            c["result"] in ("pass", "fail", "blocked") for c in results["cases"]
        )


class TestCallbacks:
    def test_on_result_fires_per_case_in_order(self):
        seen = []
        TestRunner(demo_seed=1).run(
            make_manifest([case("a"), case("b")]),
            on_result=lambda cid, result, ms: seen.append(cid),
        )
        assert seen == ["a", "b"]


class TestJUnitOutput:
    def test_junit_xml_counts_and_structure(self, tmp_path):
        results = {
            "suite": "Smoke",
            "cases": [
                {"id": "a", "name": "a", "result": "pass",
                 "duration_ms": 100, "message": ""},
                {"id": "b", "name": "b", "result": "fail",
                 "duration_ms": 200, "message": "assertion failed"},
                {"id": "c", "name": "c", "result": "blocked",
                 "duration_ms": 50, "message": "no env"},
            ],
        }
        path = tmp_path / "results.xml"
        TestRunner.write_junit(results, str(path))

        suite = ET.parse(path).getroot().find("testsuite")
        assert suite.get("tests") == "3"
        assert suite.get("failures") == "1"
        assert suite.get("errors") == "1"

        testcases = suite.findall("testcase")
        assert len(testcases) == 3
        assert testcases[1].find("failure").get("message") == "assertion failed"
        assert testcases[2].find("error") is not None
