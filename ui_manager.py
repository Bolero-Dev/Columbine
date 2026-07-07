"""
ui_manager.py

Wires the model, the styling layer, and user interaction together. The shape
is intentionally the same as the original config tool:

  - columns are observers of the model
  - "move" buttons re-bucket the selected cases
  - a commit action runs on a background thread under a lock so the UI never
    freezes, and paints results back as they arrive

What changed is what "commit" means: it used to encode a segment and bounce a
device. Now it runs a suite of tests and writes JUnit XML.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging

from test_data import TestData, RUNNABLE_SUITES, SUITES
from manifest_manager import ManifestManager
from runner import TestRunner
from ui_design import UIDesign


class UIManager:
    """Manages the user interface and interactions."""

    def __init__(self, root, test_data, manifest_manager):
        self.root = root
        self.test_data = test_data
        self.manifest_manager = manifest_manager
        self.ui_design = UIDesign()

        self.columns = self._initialize_columns(root)
        self.product_name_var = tk.StringVar()
        self.command_var = tk.StringVar()

        self._create_buttons(root)
        self._create_status_bar(root)

        self.ui_design.apply_styles(root)
        self.ui_design.enable_resizing(root)

        self.dry_run = False
        self.lock = threading.Lock()

    def _initialize_columns(self, root):
        return {
            title: self.ui_design.create_column(root, title, index, self)
            for index, title in enumerate(SUITES)
        }

    # --- toolbar -----------------------------------------------------------

    def _create_buttons(self, root):
        button_frame = tk.Frame(root, bg=self.ui_design.background_color())
        button_frame.grid(row=0, column=len(SUITES), rowspan=2, sticky="nsew", padx=5, pady=5)

        # Re-bucket selected cases into a target suite.
        for suite in ["Smoke", "Regression", "Skip", "Untriaged"]:
            self.ui_design.create_button(
                button_frame, f"→ {suite}", lambda s=suite: self.move_selected(s)
            )

        # Run actions — the real commit.
        for suite in RUNNABLE_SUITES:
            self.ui_design.create_button(
                button_frame, f"Run {suite}", lambda s=suite: self.run_suite(s)
            )

        self.ui_design.create_button(button_frame, "Add Test Case", self._create_add_case_popup)
        self.ui_design.create_button(button_frame, "Load Manifest…", self._load_manifest_dialog)
        self.ui_design.create_button(button_frame, "Save Working Set", self._save_working_set)

        self.dry_run_button = self.ui_design.create_button(
            button_frame, "Dry Run: OFF", self._toggle_dry_run
        )

    def _toggle_dry_run(self):
        self.dry_run = not self.dry_run
        state = "ON" if self.dry_run else "OFF"
        self.dry_run_button.config(text=f"Dry Run: {state}")

    def _create_status_bar(self, root):
        self.status_var = tk.StringVar(value="Ready — load a manifest or add a case to begin.")
        status_bar = tk.Label(
            root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W,
            bg=self.ui_design.entry_background(), fg="#212426", font=("Montserrat", 10),
        )
        status_bar.grid(row=2, column=0, columnspan=len(SUITES) + 1, sticky="ew")

    def update_status(self, message):
        self.status_var.set(message)

    # --- triage actions ----------------------------------------------------

    def _all_selected_ids(self):
        ids = []
        for column in self.columns.values():
            ids.extend(column.get_selected_ids())
        return ids

    def move_selected(self, target_suite):
        selected = self._all_selected_ids()
        if not selected:
            self.update_status("Nothing selected — pick one or more cases first.")
            return
        for case_id in selected:
            self.test_data.set_case_suite(case_id, target_suite)
        self.update_status(f"Moved {len(selected)} case(s) → {target_suite}.")

    # --- the threaded commit ----------------------------------------------

    def run_suite(self, suite):
        threading.Thread(target=self._run_suite_task, args=(suite,), daemon=True).start()

    def _run_suite_task(self, suite):
        with self.lock:
            run_manifest = self.manifest_manager.prepare_run_manifest(suite)
            if run_manifest is None:
                self.root.after(0, self.update_status, f"Suite '{suite}' is empty — nothing to run.")
                return

            self.manifest_manager.write_run_manifest(run_manifest)
            count = len(run_manifest["cases"])
            self.root.after(0, self.update_status,
                            f"Running {suite}: 0/{count}…")

            runner = TestRunner(dry_run=self.dry_run)
            progress = {"done": 0}

            def on_result(case_id, result, ms):
                # Marshal model update + repaint back onto the Tk main thread.
                progress["done"] += 1
                self.test_data.record_result(case_id, result, ms)
                self.root.after(0, self._refresh_after_result, suite, progress["done"], count)

            results = runner.run(run_manifest, on_result=on_result)
            report_path = TestRunner.write_junit(results)

            passed = sum(1 for c in results["cases"] if c["result"] == "pass")
            failed = sum(1 for c in results["cases"] if c["result"] == "fail")
            blocked = sum(1 for c in results["cases"] if c["result"] == "blocked")
            summary = (f"{suite} done — {passed} passed, {failed} failed, "
                       f"{blocked} blocked. Report: {report_path}")
            self.root.after(0, self.update_status, summary)

    def _refresh_after_result(self, suite, done, count):
        self.test_data.notify_observers()
        self.update_status(f"Running {suite}: {done}/{count}…")

    # --- add-case dialog ---------------------------------------------------

    def _create_add_case_popup(self):
        popup = tk.Toplevel()
        popup.title("Add Test Case")
        popup.geometry("420x200")
        popup.configure(bg=self.ui_design.background_color())

        style = ttk.Style()
        style.configure("Popup.TLabel", foreground=self.ui_design.label_foreground(),
                        background=self.ui_design.background_color(), font=("Montserrat", 10))

        popup.columnconfigure(1, weight=1)

        ttk.Label(popup, text="Name:", style="Popup.TLabel").grid(
            row=0, column=0, padx=10, pady=8, sticky="w")
        ttk.Entry(popup, textvariable=self.product_name_var).grid(
            row=0, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(popup, text="Command:", style="Popup.TLabel").grid(
            row=1, column=0, padx=10, pady=8, sticky="w")
        ttk.Entry(popup, textvariable=self.command_var).grid(
            row=1, column=1, padx=10, pady=8, sticky="ew")

        ttk.Label(popup, text="(leave command blank to simulate)",
                  style="Popup.TLabel").grid(row=2, column=1, padx=10, sticky="w")

        ttk.Button(popup, text="Add",
                   command=lambda: self._submit_new_case(popup)).grid(
            row=3, column=0, columnspan=2, pady=12)

    def _submit_new_case(self, popup):
        name = self.product_name_var.get().strip()
        if not name:
            messagebox.showwarning("Add Test Case", "A name is required.")
            return
        created = self.test_data.add_case(name, self.command_var.get().strip())
        if created is None:
            messagebox.showwarning("Add Test Case", f"'{name}' already exists.")
            return
        self.update_status(f"Added '{name}'.")
        self.product_name_var.set("")
        self.command_var.set("")
        popup.destroy()

    # --- file actions ------------------------------------------------------

    def _load_manifest_dialog(self):
        path = filedialog.askopenfilename(
            title="Load test manifest",
            filetypes=[("JSON manifest", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        cases = self.manifest_manager.load(path)
        self.update_status(f"Loaded {len(cases)} case(s) from manifest.")

    def _save_working_set(self):
        path = self.manifest_manager.save_working_set()
        if path:
            self.update_status(f"Saved working set to {path}.")
        else:
            self.update_status("Save failed — see log.")
