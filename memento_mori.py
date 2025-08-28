from datetime import date, timedelta
import json

import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText
from tkinter import messagebox

START_DATE = date(2025, 9, 1)
END_DATE = date(2025, 12, 1)

class MementoMoriApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="flatly")
        self.title("Memento Mori")
        self.geometry("900x600")
        self.notes = {}
        self.selected_day = None

        self.style.configure("Day.TButton", font=("Segoe UI", 11), padding=10)
        self.style.configure("Note.TLabel", font=("Segoe UI", 14, "bold"))

        header = ttk.Label(self, text="Memento Mori", font=("Segoe UI", 24, "bold"))
        header.pack(pady=(15, 10))

        self.paned = ttk.PanedWindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True, padx=15, pady=15)
        self.grid_frame = ttk.Frame(self.paned, padding=10)
        self.note_frame = ttk.Frame(self.paned, padding=10)
        self.paned.add(self.grid_frame, weight=3)
        self.paned.add(self.note_frame, weight=2)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=15, pady=(0, 15))
        export_btn = ttk.Button(toolbar, text="Export JSON", bootstyle="info-outline", command=self._export_json)
        export_btn.pack(side="right")

        self._load_notes()
        self._build_grid()
        self._build_note_editor()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _load_notes(self):
        try:
            with open("notes.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            self.notes = {date.fromisoformat(k): v for k, v in data.items()}
        except OSError:
            self.notes = {}

    def _save_notes(self):
        data = {d.isoformat(): note for d, note in self.notes.items()}
        with open("notes.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _on_close(self):
        try:
            self._save_notes()
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
        self.destroy()

    def _build_grid(self):
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        current = START_DATE
        today = date.today()
        row = 0
        while current <= END_DATE:
            for col in range(7):
                if current > END_DATE:
                    break
                text = str(current.day)
                if current in self.notes:
                    text += "\n📝"
                if current < today:
                    boot = "secondary"
                elif current == today:
                    boot = "info"
                else:
                    boot = "light-outline"
                btn = ttk.Button(
                    self.grid_frame,
                    text=text,
                    width=5,
                    style="Day.TButton",
                    bootstyle=boot,
                    command=lambda d=current: self._on_day_click(d),
                )
                btn.grid(row=row, column=col, padx=4, pady=4)
                current += timedelta(days=1)
            row += 1

    def _on_day_click(self, d):
        self.selected_day = d
        self.note_label.config(text=f"Note for {d.isoformat()}")
        self.note_text.delete("1.0", "end")
        self.note_text.insert("1.0", self.notes.get(d, ""))
        self.note_text.focus_set()

    def _save_current_note(self):
        if not self.selected_day:
            return
        text = self.note_text.get("1.0", "end").strip()
        if text:
            self.notes[self.selected_day] = text
        elif self.selected_day in self.notes:
            del self.notes[self.selected_day]
        self._build_grid()

    def _build_note_editor(self):
        self.note_frame.columnconfigure(0, weight=1)
        self.note_label = ttk.Label(self.note_frame, text="Select a day to view/edit notes.", style="Note.TLabel")
        self.note_label.pack(anchor="w")
        self.note_text = ScrolledText(self.note_frame, height=12, bootstyle="light", autohide=True)
        self.note_text.pack(fill="both", expand=True, pady=5)
        save_btn = ttk.Button(self.note_frame, text="Save Note", bootstyle="success", command=self._save_current_note)
        save_btn.pack(anchor="e")

    def _export_json(self):
        try:
            self._save_notes()
            messagebox.showinfo("Export", "Notes exported to notes.json")
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))

if __name__ == "__main__":
    app = MementoMoriApp()
    app.mainloop()
