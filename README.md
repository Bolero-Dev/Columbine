# Columbine — Test Triage & Run

A small, standalone desktop tool for triaging test cases into suites and running
them. Import a manifest of test cases, sort them into **Smoke / Regression /
Skip**, then run a suite on a background thread and watch pass/fail land live.
Results are written as **JUnit XML** that any CI system already understands.

No external binaries. No proprietary drivers. `python main.py` and it runs.

> **Origin note:** Columbine is a public rebuild of internal QA tooling I
> developed during hardware/software validation work. The proprietary parts
> (encoded manifest formats, device-control binaries) were removed and replaced
> with open equivalents — plain JSON manifests and a subprocess runner — so the
> architecture and workflow could be shared.

## Run it

```bash
python main.py                # loads the bundled demo_tests.json
python main.py my_tests.json  # loads your own manifest
```

Requires Python 3.8+ and Tk (`python3-tk` on Debian/Ubuntu; bundled with the
python.org installers on Windows/macOS).

## Run the tests

```bash
pip install pytest
pytest
```

The suite covers the runner (execution outcomes, timeouts, dry run, JUnit
output), the manifest pipeline (load, dedupe, persistence round-trips), and the
model layer (normalization, suite transitions, observer notifications). Tests
run automatically on every push via GitHub Actions.

## How a test case works

Each case is self-describing JSON:

```json
{"id": "checkout_card", "name": "Checkout with card",
 "command": "pytest tests/checkout.py::test_card", "suite": "Smoke",
 "tags": ["payments"], "timeout_s": 60}
```

- A case **with a command** runs as a subprocess. Exit 0 = pass, anything else =
  fail, a timeout = fail, a command that won't launch = blocked.
- A case **without a command** is simulated, so the demo runs with zero setup.

## Workflow

1. **Load Manifest** (or use the bundled demo).
2. Select cases in any column and use the **→ Smoke / → Regression / → Skip**
   buttons to triage them.
3. **Run Smoke** or **Run Regression**. The run happens off the UI thread; rows
   recolour green/red/amber as each case finishes.
4. A `run_manifest.json` (what was executed) and `results.xml` (JUnit) are
   written next to the app.
5. **Save Working Set** persists your triage back to `manifest.json`.

**Dry Run** toggles execution off — it still writes the run manifest so you can
see exactly what *would* run.

## Architecture

```
main.py              entry point; builds the model + manager + window
test_data.py         the model and observer "subject"; holds the working set
observer.py          ColumnObserver — each suite column observes the model
manifest_manager.py  load / dedupe / write manifests (the data pipeline)
runner.py            executes a run manifest, emits JUnit XML (UI-agnostic)
ui_design.py         all styling and widget construction, fully decoupled
ui_manager.py        interaction logic; the threaded, lock-guarded commit
tests/               pytest suite for the non-UI layers
```

The design is deliberately layered: the model knows nothing about Tk, the
runner knows nothing about the UI, and styling is isolated from interaction.
A single `notify_observers()` keeps every column consistent with one source of
truth.

---

Built by Liza Sloane — [github.com/Bolero-Dev](https://github.com/Bolero-Dev)
