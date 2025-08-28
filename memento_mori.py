import json
import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Iterable

# ============================ Config ============================
APP_TITLE = "Memento Mori – 01/09/2025 → 01/12/2025"
START_DATE = date(2025, 9, 1)   # inclus
END_DATE   = date(2025, 12, 1)  # inclus

ROOT_DIR    = Path(__file__).parent.resolve()
SAVES_DIR   = ROOT_DIR / "saves"
LATEST_F    = SAVES_DIR / "latest.json"
HISTORY_DIR = SAVES_DIR / "history"   # <-- nouvelles archives ici
MAX_HISTORY = 60                      # nombre de fichiers d’archives à conserver

# Lisibilité
USER_SCALE = 1.2
# Use Apple's SF Pro Text font when available to give the interface a
# macOS look. Tk falls back to the default font if the family is missing
# which keeps the app functional on other platforms.
FONT_FAMILY   = "SF Pro Text"
FONT_BASE     = (FONT_FAMILY, int(13 * USER_SCALE))
FONT_MUTED    = (FONT_FAMILY, int(12 * USER_SCALE))
FONT_DAYNUM   = (FONT_FAMILY, int(16 * USER_SCALE), "bold")
FONT_TITLE    = (FONT_FAMILY, int(24 * USER_SCALE), "bold")
FONT_SUBTITLE = (FONT_FAMILY, int(13 * USER_SCALE))
FONT_NOTE_HDR = (FONT_FAMILY, int(16 * USER_SCALE), "bold")

# Apple inspired dark palette
COLOR_BG        = "#1c1c1e"  # system background
COLOR_PANEL     = "#2c2c2e"  # secondary background
COLOR_TEXT      = "#f2f2f7"  # primary label
COLOR_MUTED     = "#8e8e93"  # secondary label
COLOR_PAST      = "#3a3a3c"
COLOR_TODAY     = "#0a84ff"  # system blue
COLOR_FUTURE    = "#2c2c2e"
COLOR_NOTE_DOT  = "#ff9f0a"  # system orange
COLOR_GRID_LINE = "#3a3a3c"

WEEKDAYS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


# ============================ Utils ============================
def atomic_write_json(path: Path, payload: dict):
    """Écrit un JSON de manière atomique (temp + replace)."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def cleanup_history(directory: Path, pattern: str = "memento_*.json", keep: int = MAX_HISTORY):
    """Garde seulement les N plus récents fichiers d’archive."""
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink(missing_ok=True)
        except Exception:
            pass


# ============================ UI ================================
class DayCell(ttk.Frame):
    def __init__(self, master, day_date: date, parent_app, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.day_date = day_date
        self.app = parent_app
        self.configure(style="Card.TFrame", padding=0)

        self.bg = tk.Frame(self, bd=0, highlightthickness=0, bg=self._bg_color_by_status())
        self.bg.pack(fill="both", expand=True)

        self.border = tk.Frame(self.bg, bd=0, highlightthickness=self._today_border_thickness(),
                               highlightbackground=COLOR_TODAY, highlightcolor=COLOR_TODAY,
                               bg=self.bg["bg"])
        self.border.pack(fill="both", expand=True)

        top = tk.Frame(self.border, bg=self.bg["bg"])
        top.pack(fill="x", padx=10, pady=(8, 0))
        dnum = tk.Label(top, text=str(self.day_date.day), fg=COLOR_TEXT, bg=self.bg["bg"],
                        font=FONT_DAYNUM)
        dnum.pack(side="left")

        self.note_dot = tk.Canvas(top, width=int(12*USER_SCALE), height=int(12*USER_SCALE),
                                  highlightthickness=0, bg=self.bg["bg"])
        self.note_dot.pack(side="right")
        self._render_note_dot()

        center = tk.Frame(self.border, bg=self.bg["bg"])
        center.pack(fill="both", expand=True, padx=10, pady=8)
        status_lbl = tk.Label(center, text=self._status_label(), fg=COLOR_MUTED, bg=self.bg["bg"],
                              font=FONT_MUTED)
        status_lbl.pack(anchor="w")

        for widget in (self.bg, self.border, top, dnum, center, status_lbl, self.note_dot):
            widget.bind("<Button-1>", self._open_editor)
        for widget in (self.bg, self.border, top, dnum, center, status_lbl):
            widget.configure(cursor="hand2")

        # hauteur visuelle minimum
        self.border.configure(height=int(84*USER_SCALE))

    def _today_border_thickness(self) -> int:
        return 2 if self.day_date == date.today() else 0

    def _bg_color_by_status(self) -> str:
        if self.day_date < date.today():
            return COLOR_PAST
        elif self.day_date == date.today():
            return COLOR_PANEL
        else:
            return COLOR_FUTURE

    def _status_label(self) -> str:
        if self.day_date < date.today():
            return "Jour écoulé"
        elif self.day_date == date.today():
            return "Aujourd’hui"
        return "Jour à venir"

    def _render_note_dot(self):
        self.note_dot.delete("all")
        key = self.day_date.isoformat()
        if key in self.app.notes and str(self.app.notes[key]).strip():
            self.note_dot.create_oval(2, 2, int(10*USER_SCALE), int(10*USER_SCALE),
                                      fill=COLOR_NOTE_DOT, outline=COLOR_NOTE_DOT)

    def refresh(self):
        self.bg.configure(bg=self._bg_color_by_status())
        self.border.configure(highlightthickness=self._today_border_thickness(),
                              highlightbackground=COLOR_TODAY, highlightcolor=COLOR_TODAY,
                              bg=self.bg["bg"])
        self._render_note_dot()

    def _open_editor(self, _event=None):
        self.app.show_note_editor(self.day_date)


class MementoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            self.call('tk', 'scaling', USER_SCALE)
        except tk.TclError:
            pass

        self.title(APP_TITLE)
        self.configure(bg=COLOR_BG)
        self.geometry("1000x680+120+80")
        self.minsize(int(880*USER_SCALE), int(560*USER_SCALE))

        # Style ttk
        style = ttk.Style(self)
        # Try to use the native macOS theme when available, otherwise
        # gracefully fall back to generic themes.
        for candidate in ("aqua", "vista", "clam", "alt", "default"):
            try:
                style.theme_use(candidate)
                break
            except tk.TclError:
                continue
        style.configure("TLabel", foreground=COLOR_TEXT, background=COLOR_BG, font=FONT_BASE)
        style.configure("Muted.TLabel", foreground=COLOR_MUTED, background=COLOR_BG, font=FONT_MUTED)
        style.configure("Card.TFrame", background=COLOR_PANEL)
        style.configure("TFrame", background=COLOR_BG)
        style.configure("TButton", padding=6, font=FONT_BASE)
        # Accent button used for primary actions
        style.configure(
            "Accent.TButton",
            padding=6,
            font=FONT_BASE,
            background=COLOR_TODAY,
            foreground="white",
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", COLOR_TODAY)],
            foreground=[("disabled", COLOR_MUTED)],
        )

        # FS
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)

        # State
        self.notes: dict[str, str] = {}
        self._load_last_save()

        # Container "pages"
        self.container = ttk.Frame(self, style="TFrame")
        self.container.pack(fill="both", expand=True)

        self.page_calendar = None
        self.page_editor = None

        # Affichage : construire hors-écran pour un rendu plus vif
        self.withdraw()
        self.show_calendar()
        self.deiconify()
        self.lift()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- Pages ----------
    def clear_container(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _legend_badge(self, parent, color, text, dot=False):
        item = ttk.Frame(parent, style="TFrame")
        item.pack(side="left", padx=12)
        if dot:
            c = tk.Canvas(item, width=int(16*USER_SCALE), height=int(16*USER_SCALE),
                          highlightthickness=0, bg=COLOR_BG)
            c.create_oval(4, 4, int(12*USER_SCALE), int(12*USER_SCALE), fill=color, outline=color)
            c.pack(side="left")
        else:
            sw = tk.Frame(item, width=int(22*USER_SCALE), height=int(14*USER_SCALE), bg=color)
            sw.pack(side="left")
        ttk.Label(item, text="  " + text, style="Muted.TLabel", font=FONT_MUTED).pack(side="left")

    def show_calendar(self):
        self.clear_container()
        self.page_calendar = ttk.Frame(self.container, style="TFrame")
        self.page_calendar.pack(fill="both", expand=True)

        header = ttk.Frame(self.page_calendar, style="TFrame")
        header.pack(fill="x", pady=(10, 6))
        ttk.Label(header, text="Memento Mori", font=FONT_TITLE).pack(anchor="w", padx=16)
        ttk.Label(header, text="Cliquez sur un jour pour ajouter une note · Sauvegarde auto",
                  style="Muted.TLabel", font=FONT_SUBTITLE).pack(anchor="w", padx=16, pady=(4, 0))

        legend = ttk.Frame(self.page_calendar, style="TFrame")
        legend.pack(fill="x", pady=(0, 10))
        self._legend_badge(legend, COLOR_PAST, "Jour écoulé")
        self._legend_badge(legend, COLOR_PANEL, "Aujourd’hui (bordure bleue)")
        self._legend_badge(legend, COLOR_FUTURE, "Jour à venir")
        self._legend_badge(legend, COLOR_NOTE_DOT, "Note présente", dot=True)

        # Grille scrollable
        outer = ttk.Frame(self.page_calendar, style="TFrame")
        outer.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        canvas = tk.Canvas(outer, bg=COLOR_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas, style="TFrame")
        frame_id = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Construction SANS recalcul continu du scrollregion
        def header_row(parent):
            hdr = ttk.Frame(parent, style="TFrame")
            hdr.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 8))
            for col, name in enumerate(WEEKDAYS):
                ttk.Label(hdr, text=name, style="Muted.TLabel", font=FONT_MUTED).grid(row=0, column=col, padx=8, pady=4)

        header_row(frame)

        start = START_DATE
        last_sunday = END_DATE + timedelta(days=(6 - END_DATE.weekday()))
        if last_sunday < END_DATE:
            last_sunday += timedelta(days=7)

        row_idx, cur = 1, start
        while cur <= last_sunday:
            week_frame = ttk.Frame(frame, style="TFrame")
            week_frame.grid(row=row_idx, column=0, sticky="ew", padx=4, pady=6)
            for col in range(7):
                day = cur + timedelta(days=col)
                container = ttk.Frame(week_frame, style="TFrame")
                container.grid(row=0, column=col, padx=8, pady=6, sticky="nsew")
                if day < START_DATE or day > END_DATE:
                    tk.Frame(container, width=int(110*USER_SCALE), height=int(82*USER_SCALE), bg=COLOR_BG,
                             highlightthickness=1, highlightbackground=COLOR_GRID_LINE).pack(fill="both", expand=True)
                else:
                    cell = DayCell(container, day, self)
                    cell.pack(fill="both", expand=True)
            cur += timedelta(days=7)
            row_idx += 1

        # Un seul calcul de scrollregion à la fin
        frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.yview_moveto(0.0)

    def show_note_editor(self, day_date: date):
        self.clear_container()
        self.page_editor = ttk.Frame(self.container, style="TFrame")
        self.page_editor.pack(fill="both", expand=True)

        header = ttk.Frame(self.page_editor, style="TFrame")
        header.pack(fill="x", pady=(10, 6))
        ttk.Label(header, text=day_date.strftime("%A %d %B %Y"), font=FONT_NOTE_HDR).pack(anchor="w", padx=16)

        text = tk.Text(
            self.page_editor,
            wrap="word",
            bg=COLOR_PANEL,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            relief="flat",
            font=FONT_BASE,
        )
        text.pack(fill="both", expand=True, padx=16, pady=8)

        key = day_date.isoformat()
        if key in self.notes:
            text.insert("1.0", str(self.notes[key]))

        btns = ttk.Frame(self.page_editor, style="TFrame")
        btns.pack(fill="x", padx=16, pady=10)
        save_btn = ttk.Button(
            btns,
            text="Sauvegarder",
            style="Accent.TButton",
            command=lambda: self._save_and_back(day_date, text),
        )
        save_btn.pack(side="left")
        close_btn = ttk.Button(btns, text="Annuler", command=self.show_calendar)
        close_btn.pack(side="right")

        # Raccourci clavier (scopé à l'éditeur)
        def on_ctrl_s(event=None):
            self._save_and_back(day_date, text)
            return "break"
        text.bind("<Control-s>", on_ctrl_s)

    # ---------- Save ----------
    def _payload(self) -> dict:
        return {
            "meta": {
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "range": {"start": START_DATE.isoformat(), "end": END_DATE.isoformat()},
                "app": "memento-mori-tk",
                "version": "1.3.0"
            },
            "notes": self.notes
        }

    def _save_and_back(self, day_date: date, text_widget: tk.Text):
        content = text_widget.get("1.0", "end").rstrip()
        key = day_date.isoformat()
        if content:
            self.notes[key] = content
        elif key in self.notes:
            self.notes.pop(key)

        self.autosave()
        self.show_calendar()

    def autosave(self):
        """Écrit latest.json + archive dans saves/history/ + cleanup."""
        payload = self._payload()

        # latest.json atomique
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_json(LATEST_F, payload)

        # archive horodatée
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        roll_file = HISTORY_DIR / f"memento_{ts}.json"
        atomic_write_json(roll_file, payload)

        # ménage
        cleanup_history(HISTORY_DIR, keep=MAX_HISTORY)

    def _load_last_save(self):
        if LATEST_F.exists():
            try:
                with open(LATEST_F, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data.get("notes"), dict):
                    self.notes = {k: str(v) for k, v in data["notes"].items()}
            except Exception as e:
                print("Erreur chargement latest.json:", e, file=sys.stderr)

    def _on_close(self):
        self.autosave()
        self.destroy()


# ============================ Main ==============================
if __name__ == "__main__":
    app = MementoApp()
    app.mainloop()
