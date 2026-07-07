"""
main.py

Entry point for Columbine — a test-triage and run tool.

Sort imported test cases into suites (Smoke / Regression / Skip), then run a
suite on a background thread and watch pass/fail land live. Results are written
as JUnit XML that any CI system can read.

Run:  python main.py [optional_manifest.json]
"""

import sys
import logging
import tkinter as tk

from test_data import TestData
from manifest_manager import ManifestManager
from ui_manager import UIManager


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    root = tk.Tk()
    root.title("Columbine — Test Triage & Run")
    root.geometry("1100x520")

    test_data = TestData()
    manifest_manager = ManifestManager(test_data)
    UIManager(root, test_data, manifest_manager)

    # Load a manifest if one was passed; otherwise fall back to the bundled demo.
    manifest_path = sys.argv[1] if len(sys.argv) > 1 else "demo_tests.json"
    try:
        manifest_manager.load(manifest_path)
    except Exception as exc:  # noqa: BLE001 — startup convenience only
        logging.warning(f"Could not load '{manifest_path}': {exc}")

    root.mainloop()


if __name__ == "__main__":
    main()
