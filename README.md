# Citronella — Test Triage & Run

> Named after the citronella plant — it keeps the bugs away.

A small desktop tool for sorting test cases into suites and running them.
Import a manifest of test cases, triage them into **Smoke / Regression /
Skip**, then run a suite on a background thread and watch pass/fail land live.
Results come out as **JUnit XML**, which any CI system already understands.

No external binaries. No proprietary anything. `python main.py` and it runs.

> **Where it comes from:** Citronella is a public rebuild of internal QA tooling
> I built during hardware/software validation work. The proprietary parts
> couldn't come with me — encoded manifest formats, device-control binaries —
> so I replaced them with open equivalents: plain JSON manifests and a
> subprocess runner. The architecture and the workflow are the parts worth
> showing, and those are intact.

## Run it

```bash
python main.py                # loads the bundled demo_tests.json
python main.py my_tests.json  # loads your own manifest
```

Python 3.8+ and Tk (`python3-tk` on Debian/Ubuntu; bundled with the python.org
installers on Windows/macOS).

## Run the tests

```bash
pip install pytest
pytest
```

The suite covers the runner (execution outcomes, timeouts, dry run, JUnit
output), the manifest pipeline (load, dedupe, persistence round-trips), and the
model layer (normalization, suite transitions, observer notifications). CI runs
it on every push.

## How a test case works

Each case is self-describing JSON:

```json
{"id": "checkout_card", "name": "Checkout with card",
 "command": "pytest tests/checkout.py::test_card", "suite": "Smoke",
 "tags": ["payments"], "timeout_s": 60}
```

- A case **with a command** runs as a subprocess. Exit 0 is a pass, anything
  else is a fail, a timeout is a fail, a command that won't even launch is
  blocked.
- A case **without a command** is simulated — so the demo works with zero
  setup.

## Workflow

1. **Load Manifest** (or use the bundled demo).
2. Select cases in any column and use **→ Smoke / → Regression / → Skip** to
   triage them.
3. **Run Smoke** or **Run Regression**. The run happens off the UI thread;
   rows recolour green/red/amber as each case finishes.
4. A `run_manifest.json` (what ran) and `results.xml` (JUnit) land next to
   the app.
5. **Save Working Set** writes your triage back to `manifest.json`.

**Dry Run** turns execution off but still writes the run manifest — so you can
see exactly what *would* run before you commit to running it.

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

The layering is deliberate: the model knows nothing about Tk, the runner knows
nothing about the UI, and styling is separated from interaction. One
`notify_observers()` keeps every column consistent with a single source of
truth. I like tools where you can tell what talks to what by reading the file
list — this is one of them.

---

Built by Liza Sloane — [github.com/Bolero-Dev](https://github.com/Bolero-Dev)
