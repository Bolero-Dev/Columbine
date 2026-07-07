"""Tests for ManifestManager: load, dedupe, run-manifest prep, persistence."""

import json
import sys

sys.path.insert(0, ".")
from manifest_manager import ManifestManager
from test_data import TestData


def write_manifest(path, cases):
    path.write_text(json.dumps({"version": 1, "cases": cases}))


def manager():
    return ManifestManager(TestData())


class TestLoad:
    def test_loads_cases_into_model(self, tmp_path):
        m = manager()
        path = tmp_path / "m.json"
        write_manifest(path, [
            {"id": "a", "name": "A", "suite": "Smoke"},
            {"id": "b", "name": "B", "suite": "Regression"},
        ])
        cases = m.load(str(path))
        assert {c["id"] for c in cases} == {"a", "b"}

    def test_duplicate_ids_last_definition_wins(self, tmp_path):
        m = manager()
        path = tmp_path / "m.json"
        write_manifest(path, [
            {"id": "a", "name": "old", "suite": "Skip"},
            {"id": "a", "name": "new", "suite": "Smoke"},
        ])
        cases = m.load(str(path))
        assert len(cases) == 1
        assert cases[0]["name"] == "new"

    def test_missing_file_returns_empty_list(self):
        assert manager().load("/nonexistent/manifest.json") == []

    def test_malformed_json_returns_empty_list(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not json")
        assert manager().load(str(path)) == []

    def test_non_dict_entries_are_skipped(self, tmp_path):
        m = manager()
        path = tmp_path / "m.json"
        write_manifest(path, ["junk", 42, {"id": "a", "name": "A"}])
        cases = m.load(str(path))
        assert [c["id"] for c in cases] == ["a"]


class TestRunManifest:
    def test_prepare_filters_to_requested_suite(self, tmp_path):
        m = manager()
        path = tmp_path / "m.json"
        write_manifest(path, [
            {"id": "a", "name": "A", "suite": "Smoke"},
            {"id": "b", "name": "B", "suite": "Regression"},
        ])
        m.load(str(path))
        run = m.prepare_run_manifest("Smoke")
        assert [c["id"] for c in run["cases"]] == ["a"]
        assert run["suite"] == "Smoke"

    def test_empty_suite_returns_none(self):
        assert manager().prepare_run_manifest("Smoke") is None

    def test_write_run_manifest_round_trips(self, tmp_path):
        m = manager()
        run = {"version": 1, "suite": "Smoke", "cases": []}
        out = tmp_path / "run.json"
        assert m.write_run_manifest(run, str(out)) == str(out)
        assert json.loads(out.read_text()) == run


class TestWorkingSetPersistence:
    def test_save_and_reload_preserves_triage(self, tmp_path):
        m = manager()
        src = tmp_path / "m.json"
        write_manifest(src, [
            {"id": "a", "name": "A", "suite": "Untriaged"},
        ])
        m.load(str(src))
        m.test_data.set_case_suite("a", "Smoke")

        out = tmp_path / "saved.json"
        m.save_working_set(str(out))

        reloaded = manager()
        cases = reloaded.load(str(out))
        assert cases[0]["suite"] == "Smoke"
