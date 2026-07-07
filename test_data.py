"""
test_data.py

The model layer and observer subject. Holds the working set of test cases
and notifies registered observers (the suite columns) whenever the data
changes. This is the spine of the app: every UI column is an observer of
this object, so a single notify() keeps the whole interface consistent.

Domain note: a "test case" is fully self-describing. It carries everything
the runner needs (an id, a name, an optional shell command, tags) plus the
suite it currently belongs to. Nothing here depends on any external tool.
"""

import logging

# A suite is just a named bucket a test case can live in. "Untriaged" is the
# landing zone for freshly imported cases. The three others are the states you
# sort into. Only RUNNABLE_SUITES actually get executed on a run; "Skip" is the
# deliberate exclusion bucket.
SUITES = ["Untriaged", "Smoke", "Regression", "Skip"]
RUNNABLE_SUITES = ["Smoke", "Regression"]

# The default shape of a test case. Importing a manifest fills these in; the
# "Add Test Case" dialog creates one from scratch.
DEFAULT_TEST_CASE = {
    "id": "",            # stable unique key
    "name": "",          # human-readable label shown in the UI
    "command": "",       # shell command to execute; empty => simulated in demo
    "suite": "Untriaged",
    "tags": [],
    "timeout_s": 60,
    "last_result": None,  # "pass" | "fail" | "blocked" | None
    "last_duration_ms": 0,
}


class SuiteTransition:
    """
    Applies a suite change to a single test case.

    This mirrors the old state-config helper: it knows the valid target
    suites and refuses no-op or invalid transitions, keeping the move logic
    out of the UI layer.
    """

    def __init__(self, test_case):
        self.case = test_case.copy()
        logging.debug(f"SuiteTransition initialized for '{self.case.get('id')}'.")

    def move_to(self, target_suite):
        if target_suite not in SUITES:
            logging.error(f"Refused move to unknown suite '{target_suite}'.")
            return False
        if self.case["suite"] == target_suite:
            return False
        previous = self.case["suite"]
        self.case["suite"] = target_suite
        logging.info(f"'{self.case['id']}' moved {previous} -> {target_suite}.")
        return True


class TestData:
    """Manages the working set of test cases and observer notifications."""

    def __init__(self):
        self._cases = []        # list of test-case dicts
        self._observers = []
        logging.info("TestData initialized (empty working set).")

    # --- observer plumbing -------------------------------------------------

    def register_observer(self, observer):
        self._observers.append(observer)
        logging.debug(f"Observer registered: {observer}")

    def unregister_observer(self, observer):
        self._observers.remove(observer)
        logging.debug(f"Observer unregistered: {observer}")

    def notify_observers(self):
        for observer in self._observers:
            observer.update(self._cases)
        logging.info("Observers notified of data change.")

    # --- data access -------------------------------------------------------

    def get_cases(self):
        return self._cases

    def set_cases(self, cases):
        """Replace the working set wholesale and refresh observers."""
        normalized = []
        for raw in cases:
            case = DEFAULT_TEST_CASE.copy()
            case.update({k: v for k, v in raw.items() if k in DEFAULT_TEST_CASE})
            if not case["id"]:
                case["id"] = case["name"] or f"case-{len(normalized)}"
            normalized.append(case)
        self._cases = normalized
        logging.info(f"Working set loaded with {len(self._cases)} test case(s).")
        self.notify_observers()

    def find(self, case_id):
        return next((c for c in self._cases if c["id"] == case_id), None)

    def add_case(self, name, command="", suite="Untriaged"):
        if any(c["id"] == name for c in self._cases):
            logging.warning(f"Test case '{name}' already exists; not adding.")
            return None
        case = DEFAULT_TEST_CASE.copy()
        case.update({"id": name, "name": name, "command": command, "suite": suite})
        self._cases.append(case)
        logging.info(f"Added test case '{name}' to suite '{suite}'.")
        self.notify_observers()
        return case

    def set_case_suite(self, case_id, target_suite):
        case = self.find(case_id)
        if not case:
            logging.error(f"Test case '{case_id}' not found.")
            return False
        transition = SuiteTransition(case)
        if transition.move_to(target_suite):
            case["suite"] = target_suite
            self.notify_observers()
            return True
        return False

    def record_result(self, case_id, result, duration_ms):
        case = self.find(case_id)
        if case:
            case["last_result"] = result
            case["last_duration_ms"] = duration_ms
            logging.debug(f"Recorded {result} for '{case_id}' ({duration_ms} ms).")
