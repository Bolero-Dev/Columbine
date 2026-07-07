"""
ui_design.py

Encapsulates all styling and widget construction. Kept fully decoupled from
the interaction logic in ui_manager.py — the manager never hard-codes a colour
or a font, it asks this class. Same separation as before.
"""

import tkinter as tk
from tkinter import ttk
from observer import ColumnObserver


class UIDesign:
    """Encapsulates UI styling and design elements."""

    def apply_styles(self, root):
        root.configure(bg=self.background_color())
        style = ttk.Style()
        style.configure(
            "Custom.TButton",
            foreground=self.button_foreground(),
            background=self.button_background(),
            relief="flat",
            font=self.button_font(),
        )
        style.map("Custom.TButton", background=[("active", self.button_active_background())])
        style.configure("TLabel", foreground=self.label_foreground(),
                        background=self.label_background(), font=self.label_font())
        style.configure("TEntry", foreground=self.entry_foreground(),
                        background=self.entry_background(), font=self.entry_font())
        style.configure("TFrame", background=self.frame_background())

    def enable_resizing(self, root):
        root.resizable(True, True)
        for col in range(5):
            root.columnconfigure(col, weight=1)
        root.rowconfigure(1, weight=1)

    def create_column(self, root, title, index, ui_manager):
        """Build one suite column and register its observer with the model."""
        frame = tk.Frame(root, bg=self.entry_background(),
                         highlightbackground=self.label_background(), highlightthickness=1)
        frame.grid(row=1, column=index, sticky="nsew", padx=5, pady=5)
        tk.Label(root, text=title, font=self.label_font(), fg=self.label_foreground(),
                 bg=self.label_background()).grid(row=0, column=index, sticky="nsew", pady=5)

        listbox = tk.Listbox(
            frame, selectmode=tk.MULTIPLE, height=14, width=26,
            bg=self.entry_background(), fg=self.entry_foreground(),
            selectbackground="#add9d1", selectforeground=self.entry_foreground(),
            font=("Helvetica", 10), borderwidth=1, relief="solid",
            highlightbackground="#93bcb7", exportselection=False,
        )
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=scrollbar.set)

        observer = ColumnObserver(title, listbox, ui_manager)
        ui_manager.test_data.register_observer(observer)
        return observer

    def create_button(self, frame, text, command):
        button = ttk.Button(frame, text=text, command=command, style="Custom.TButton")
        button.pack(fill="x", pady=5)
        return button

    # --- palette (unchanged from the original) -----------------------------
    def background_color(self): return "#343d45"
    def button_foreground(self): return "#212426"
    def button_background(self): return "#c0cdd6"
    def button_active_background(self): return "#add9d1"
    def button_font(self): return ("Montserrat", 10)
    def label_foreground(self): return "#d2e8e0"
    def label_background(self): return "#456268"
    def label_font(self): return ("Montserrat", 12)
    def entry_foreground(self): return "#212426"
    def entry_background(self): return "#ededed"
    def entry_font(self): return ("Montserrat", 10)
    def frame_background(self): return "#343d45"
