"""Tests for TestData: normalization, suite transitions, observer plumbing."""

import sys

sys.path.insert(0, ".")
from test_data import TestData, SuiteTransition, SUITES


class RecordingObserver:
    def __init__(self):
        self.updates = 0
        self.last_cases = None

    def update(self, cases):
        self.updates += 1
        self.last_cases = cases


class TestNormalization:
    def test_unknown_keys_are_stripped(self):
        data = TestData()
        data.set_cases([{"id": "a", "name": "A", "evil_key": "x"}])
        assert "evil_key" not in data.get_cases()[0]

    def test_missing_id_falls_back_to_name(self):
        data = TestData()
        data.set_cases([{"name": "My Test"}])
        assert data.get_cases()[0]["id"] == "My Test"

    def test_missing_id_and_name_gets_generated_id(self):
        data = TestData()
        data.set_cases([{}])
        assert data.get_cases()[0]["id"] == "case-0"

    def test_defaults_are_applied(self):
        data = TestData()
        data.set_cases([{"id": "a", "name": "A"}])
        case = data.get_cases()[0]
        assert case["suite"] == "Untriaged"
        assert case["timeout_s"] == 60
        assert case["last_result"] is None


class TestAddCase:
    def test_add_case_appears_in_working_set(self):
        data = TestData()
        data.add_case("new_test", command="exit 0", suite="Smoke")
        assert data.find("new_test")["suite"] == "Smoke"

    def test_duplicate_add_is_refused(self):
        data = TestData()
        data.add_case("dup")
        assert data.add_case("dup") is None
        assert len(data.get_cases()) == 1


class TestSuiteTransitions:
    def test_valid_move_updates_suite(self):
        data = TestData()
        data.add_case("a")
        assert data.set_case_suite("a", "Smoke") is True
        assert data.find("a")["suite"] == "Smoke"

    def test_move_to_unknown_suite_is_refused(self):
        data = TestData()
        data.add_case("a")
        assert data.set_case_suite("a", "NotASuite") is False
        assert data.find("a")["suite"] == "Untriaged"

    def test_noop_move_is_refused(self):
        data = TestData()
        data.add_case("a")
        assert data.set_case_suite("a", "Untriaged") is False

    def test_move_of_missing_case_is_refused(self):
        assert TestData().set_case_suite("ghost", "Smoke") is False

    def test_transition_helper_does_not_mutate_original(self):
        case = {"id": "a", "suite": "Untriaged"}
        transition = SuiteTransition(case)
        transition.move_to("Smoke")
        assert case["suite"] == "Untriaged"

    def test_all_declared_suites_are_valid_targets(self):
        data = TestData()
        data.add_case("a")
        for suite in SUITES:
            if suite != "Untriaged":
                assert data.set_case_suite("a", suite) is True


class TestObservers:
    def test_observers_notified_on_set_cases(self):
        data = TestData()
        observer = RecordingObserver()
        data.register_observer(observer)
        data.set_cases([{"id": "a", "name": "A"}])
        assert observer.updates == 1
        assert observer.last_cases[0]["id"] == "a"

    def test_observers_notified_on_suite_change_only_when_moved(self):
        data = TestData()
        data.add_case("a")
        observer = RecordingObserver()
        data.register_observer(observer)

        data.set_case_suite("a", "Smoke")   # real move -> notify
        data.set_case_suite("a", "Smoke")   # no-op -> no notify
        assert observer.updates == 1

    def test_unregistered_observer_stops_receiving(self):
        data = TestData()
        observer = RecordingObserver()
        data.register_observer(observer)
        data.unregister_observer(observer)
        data.set_cases([])
        assert observer.updates == 0


class TestResultRecording:
    def test_record_result_updates_case(self):
        data = TestData()
        data.add_case("a")
        data.record_result("a", "pass", 123)
        case = data.find("a")
        assert case["last_result"] == "pass"
        assert case["last_duration_ms"] == 123

    def test_record_result_for_missing_case_is_safe(self):
        TestData().record_result("ghost", "fail", 1)
