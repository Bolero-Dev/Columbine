"""
manifest_manager.py

Handles reading and writing test manifests. A manifest is a plain JSON file
describing a set of test cases and the suite each belongs to. This replaces
the old segment loader: same load -> dedupe -> hand-to-model -> reload-on-write
pipeline, but the on-disk format is open JSON instead of an encoded blob, so
the app has zero external-binary dependencies.

Manifest shape:
{
    "version": 1,
    "cases": [
        {"id": "...", "name": "...", "command": "...", "suite": "Smoke",
         "tags": [...], "timeout_s": 60}
    ]
}
"""

import json
import os
import logging


class ManifestManager:
    """Reads test manifests and writes run manifests."""

    MANIFEST_VERSION = 1

    def __init__(self, test_data):
        self.test_data = test_data

    def load(self, path):
        """Load a manifest from disk into the model, de-duplicating by id."""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logging.error(f"Failed to read manifest '{path}': {exc}")
            return []

        raw_cases = manifest.get("cases", [])

        # De-duplicate by id, last definition wins — mirrors the old
        # unique-by-key dictionary collapse.
        unique = {}
        for case in raw_cases:
            if not isinstance(case, dict):
                continue
            key = case.get("id") or case.get("name")
            if key:
                unique[key] = case

        cases = list(unique.values())
        self.test_data.set_cases(cases)
        logging.info(f"Loaded {len(cases)} case(s) from '{path}'.")
        return self.test_data.get_cases()

    def prepare_run_manifest(self, suite):
        """Build the manifest of cases that a run of `suite` will execute."""
        cases = [c for c in self.test_data.get_cases() if c["suite"] == suite]
        if not cases:
            logging.warning(f"No cases in suite '{suite}'; nothing to run.")
            return None
        return {
            "version": self.MANIFEST_VERSION,
            "suite": suite,
            "cases": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "command": c["command"],
                    "timeout_s": c["timeout_s"],
                    "tags": c["tags"],
                }
                for c in cases
            ],
        }

    def write_run_manifest(self, run_manifest, path="run_manifest.json"):
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(run_manifest, fh, indent=4)
            logging.info(f"Run manifest written to '{path}'.")
            return path
        except IOError as exc:
            logging.error(f"Failed to write run manifest: {exc}")
            return None

    def save_working_set(self, path="manifest.json"):
        """Persist the full triaged working set back to a manifest."""
        manifest = {
            "version": self.MANIFEST_VERSION,
            "cases": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "command": c["command"],
                    "suite": c["suite"],
                    "tags": c["tags"],
                    "timeout_s": c["timeout_s"],
                }
                for c in self.test_data.get_cases()
            ],
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh, indent=4)
            logging.info(f"Working set saved to '{os.path.abspath(path)}'.")
            return path
        except IOError as exc:
            logging.error(f"Failed to save working set: {exc}")
            return None
