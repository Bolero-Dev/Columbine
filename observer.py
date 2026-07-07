"""
observer.py

The observer interface and the column observer. Each suite column on screen
is an observer of TestData. When the model changes it pushes the full working
set to every column; each column renders only the cases whose suite matches
its own title. One notify, whole UI stays coherent.
"""

import tkinter as tk
import logging

# Listbox row colours keyed by a case's last run result. Untriaged/None stays
# at the listbox default. This is the redundant-encoding-friendly mapping:
# colour PLUS a status glyph in the label, never colour alone.
RESULT_COLORS = {
    "pass": "#1f6f54",
    "fail": "#8a2b2b",
    "blocked": "#7a6a1f",
}
RESULT_GLYPH = {
    "pass": "PASS",
    "fail": "FAIL",
    "blocked": "BLOCK",
    None: "  -  ",
}


class Observer:
    """Defines the observer interface."""

    def update(self, cases):
        raise NotImplementedError


class ColumnObserver(Observer):
    """Renders the test cases belonging to one suite."""

    def __init__(self, suite_title, listbox, ui_manager):
        self._suite = suite_title
        self._listbox = listbox
        self._ui_manager = ui_manager
        self._visible_ids = []  # row index -> case id, kept in render order

    def update(self, cases):
        """Redraw this column from the shared working set."""
        self._listbox.delete(0, tk.END)
        self._visible_ids = []

        mine = sorted(
            (c for c in cases if c["suite"] == self._suite),
            key=lambda c: c["name"].lower(),
        )
        for case in mine:
            glyph = RESULT_GLYPH.get(case["last_result"], "  -  ")
            self._listbox.insert(tk.END, f"[{glyph}] {case['name']}")
            self._visible_ids.append(case["id"])
            color = RESULT_COLORS.get(case["last_result"])
            if color:
                self._listbox.itemconfig(tk.END, {"fg": "#ffffff", "bg": color})

    def get_selected_ids(self):
        """Return the case ids the user has selected in this column."""
        return [self._visible_ids[i] for i in self._listbox.curselection()]

    @property
    def suite(self):
        return self._suite
