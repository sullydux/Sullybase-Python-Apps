"""
Sullybase Filament Cost Finder
A professional dark-mode macOS app for tracking 3D printing filament costs.
Python 3.14+ with tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import sys
import webbrowser
import platform
from pathlib import Path


# ─────────────────────────────────────────────
#  DATA PATH  (~/Library/Application Support/Sullybase_Filament)
# ─────────────────────────────────────────────
def get_data_path() -> Path:
    if platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "Sullybase_Filament"
    elif platform.system() == "Windows":
        base = Path(os.getenv("APPDATA", Path.home())) / "Sullybase_Filament"
    else:
        base = Path.home() / ".config" / "Sullybase_Filament"
    base.mkdir(parents=True, exist_ok=True)
    return base / "filaments.json"


DATA_FILE = get_data_path()


# ─────────────────────────────────────────────
#  COLOUR PALETTE  (dark mode)
# ─────────────────────────────────────────────
C = {
    "bg":           "#0D1B2A",   # deep navy base
    "surface":      "#152438",   # card surface
    "surface2":     "#1C2E45",   # slightly lighter
    "accent":       "#2E6EA6",   # saturated navy blue accent
    "accent_hover": "#3D85C2",
    "accent2":      "#1E8FA6",   # saturated teal-blue for cost
    "text":         "#DCE8F5",
    "text_dim":     "#6A8BAD",
    "border":       "#1E3A56",
    "danger":       "#C0392B",
    "success":      "#1A7A4A",
    "input_bg":     "#101E2E",
    "row_even":     "#152438",
    "row_odd":      "#101E2E",
    "row_hover":    "#1C2E45",
    "header_bg":    "#091420",
}


# ─────────────────────────────────────────────
#  FILAMENT MODEL
# ─────────────────────────────────────────────
class Filament:
    def __init__(self, fid: str, name: str, amazon_link: str,
                 total_grams: float | None, total_meters: float | None,
                 total_price: float, notes: str = ""):
        self.id = fid
        self.name = name
        self.amazon_link = amazon_link
        self.total_grams = total_grams      # None if not set
        self.total_meters = total_meters    # None if not set
        self.total_price = total_price      # full spool/roll price
        self.notes = notes

    def cost_for(self, grams: float | None, meters: float | None) -> float | None:
        """Return cost based on whichever unit has both a total and a used value."""
        if grams is not None and self.total_grams:
            return (grams / self.total_grams) * self.total_price
        if meters is not None and self.total_meters:
            return (meters / self.total_meters) * self.total_price
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "amazon_link": self.amazon_link,
            "total_grams": self.total_grams,
            "total_meters": self.total_meters,
            "total_price": self.total_price,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Filament":
        return cls(
            fid=d["id"],
            name=d["name"],
            amazon_link=d.get("amazon_link", ""),
            total_grams=d.get("total_grams"),
            total_meters=d.get("total_meters"),
            total_price=d.get("total_price", 0.0),
            notes=d.get("notes", ""),
        )


# ─────────────────────────────────────────────
#  DATA LAYER
# ─────────────────────────────────────────────
def load_filaments() -> list[Filament]:
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            return [Filament.from_dict(d) for d in data]
        except Exception:
            pass
    return []


def save_filaments(filaments: list[Filament]) -> None:
    DATA_FILE.write_text(
        json.dumps([f.to_dict() for f in filaments], indent=2),
        encoding="utf-8",
    )


# ─────────────────────────────────────────────
#  CUSTOM WIDGETS
# ─────────────────────────────────────────────
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text="", command=None, width=120, height=36,
                 bg=None, fg=None, hover_bg=None, radius=10, font_size=12, **kw):
        self._bg = bg or C["accent"]
        self._hover_bg = hover_bg or C["accent_hover"]
        self._fg = fg or C["text"]
        super().__init__(parent, width=width, height=height,
                         bg=C["bg"], highlightthickness=0, **kw)
        self._radius = radius
        self._text = text
        self._command = command
        self._font = ("SF Pro Display", font_size, "bold") if platform.system() == "Darwin" else ("Segoe UI", font_size, "bold")
        self._draw(self._bg)
        self.bind("<Enter>", lambda e: self._draw(self._hover_bg))
        self.bind("<Leave>", lambda e: self._draw(self._bg))
        self.bind("<ButtonRelease-1>", lambda e: command() if command else None)
        self.bind("<ButtonPress-1>", lambda e: self._draw(C["accent"]))

    def _draw(self, color):
        self.delete("all")
        r = self._radius
        w, h = int(self["width"]), int(self["height"])
        self.create_rounded_rect(0, 0, w, h, r, fill=color, outline="")
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=self._fg, font=self._font)

    def create_rounded_rect(self, x1, y1, x2, y2, r, **kw):
        pts = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r,
            x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r,
            x1, y1+r, x1, y1
        ]
        return self.create_polygon(pts, smooth=True, **kw)


class PlaceholderEntry(tk.Entry):
    def __init__(self, parent, placeholder="", **kw):
        kw.setdefault("bg", C["input_bg"])
        kw.setdefault("fg", C["text"])
        kw.setdefault("insertbackground", C["text"])
        kw.setdefault("relief", "flat")
        kw.setdefault("bd", 0)
        kw.setdefault("highlightthickness", 1)
        kw.setdefault("highlightbackground", C["border"])
        kw.setdefault("highlightcolor", C["accent"])
        super().__init__(parent, **kw)
        self._placeholder = placeholder
        self._showing_ph = False
        self._real_fg = kw.get("fg", C["text"])
        self._show_placeholder()
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _show_placeholder(self):
        if not self.get():
            self._showing_ph = True
            self.insert(0, self._placeholder)
            self.config(fg=C["text_dim"])

    def _on_focus_in(self, _=None):
        if self._showing_ph:
            self.delete(0, tk.END)
            self.config(fg=self._real_fg)
            self._showing_ph = False

    def _on_focus_out(self, _=None):
        if not self.get():
            self._show_placeholder()

    def get_value(self) -> str:
        return "" if self._showing_ph else self.get()

    def set_value(self, val: str):
        self._on_focus_in()
        self.delete(0, tk.END)
        self.insert(0, val)
        if not val:
            self._show_placeholder()


# ─────────────────────────────────────────────
#  ADD / EDIT DIALOG
# ─────────────────────────────────────────────
class FilamentDialog(tk.Toplevel):
    def __init__(self, parent, filament: Filament | None = None):
        super().__init__(parent)
        self.result: Filament | None = None
        self._editing = filament

        title = "Edit Filament" if filament else "Add Filament"
        self.title(title)
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.grab_set()

        if platform.system() == "Darwin":
            self.tk.call("::tk::unsupported::MacWindowStyle", "style", self._w, "moveableModal", "")

        self._build_ui(filament)
        self.update_idletasks()
        # Centre over parent
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        dw, dh = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px+(pw-dw)//2}+{py+(ph-dh)//2}")

    # ── layout ──────────────────────────────
    def _build_ui(self, f: Filament | None):
        FONT_LBL = ("SF Pro Display", 12) if platform.system() == "Darwin" else ("Segoe UI", 11)
        FONT_HDR = ("SF Pro Display", 16, "bold") if platform.system() == "Darwin" else ("Segoe UI", 14, "bold")
        PAD = {"padx": 20, "pady": 6}

        outer = tk.Frame(self, bg=C["bg"], padx=30, pady=24)
        outer.pack(fill="both", expand=True)

        tk.Label(outer, text="Edit Filament" if f else "New Filament",
                 bg=C["bg"], fg=C["text"], font=FONT_HDR).grid(
                     row=0, column=0, columnspan=2, pady=(0, 18), sticky="w")

        fields = [
            ("Name (brand, colour, etc.)", "name"),
            ("Amazon Link", "amazon_link"),
            ("Total Grams (leave blank if unknown)", "total_grams"),
            ("Total Meters (leave blank if unknown)", "total_meters"),
            ("Total Amazon Price ($)", "total_price"),
            ("Notes", "notes"),
        ]

        self._entries: dict[str, PlaceholderEntry] = {}
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(outer, text=label, bg=C["bg"], fg=C["text_dim"],
                     font=FONT_LBL, anchor="w").grid(
                         row=i, column=0, sticky="w", pady=(6, 1), columnspan=2)
            width = 46 if key in ("name", "amazon_link", "notes") else 20
            ent = PlaceholderEntry(outer, placeholder=label, width=width,
                                   font=FONT_LBL)
            ent.grid(row=i+len(fields), column=0, columnspan=2, sticky="ew",
                     pady=(0, 4))
            self._entries[key] = ent

        # Re-lay using pack inside a sub-frame for cleaner feel
        for w in outer.winfo_children():
            w.grid_forget()
        outer.grid_slaves()

        # Use pack approach instead
        for w in outer.winfo_children():
            w.destroy()

        tk.Label(outer, text="Edit Filament" if f else "New Filament",
                 bg=C["bg"], fg=C["text"], font=FONT_HDR).pack(anchor="w", pady=(0, 16))

        self._entries = {}
        for label, key in fields:
            tk.Label(outer, text=label, bg=C["bg"], fg=C["text_dim"],
                     font=FONT_LBL, anchor="w").pack(fill="x", pady=(8, 2))
            ent = PlaceholderEntry(outer, placeholder=label, width=48,
                                   font=FONT_LBL)
            ent.pack(fill="x", ipady=6)
            self._entries[key] = ent

        # Pre-fill if editing
        if f:
            self._entries["name"].set_value(f.name)
            self._entries["amazon_link"].set_value(f.amazon_link)
            if f.total_grams is not None:
                self._entries["total_grams"].set_value(str(f.total_grams))
            if f.total_meters is not None:
                self._entries["total_meters"].set_value(str(f.total_meters))
            self._entries["total_price"].set_value(str(f.total_price))
            self._entries["notes"].set_value(f.notes)

        # Buttons
        btn_frame = tk.Frame(outer, bg=C["bg"])
        btn_frame.pack(fill="x", pady=(22, 0))

        cancel_btn = RoundedButton(btn_frame, text="Cancel", command=self.destroy,
                                   width=110, height=36,
                                   bg=C["surface2"], hover_bg=C["border"])
        cancel_btn.pack(side="left")

        save_lbl = "Save Changes" if f else "Add Filament"
        save_btn = RoundedButton(btn_frame, text=save_lbl, command=self._save,
                                 width=140, height=36)
        save_btn.pack(side="right")

    # ── save ────────────────────────────────
    def _save(self):
        name = self._entries["name"].get_value().strip()
        if not name:
            messagebox.showerror("Missing Field", "Name is required.", parent=self)
            return

        link = self._entries["amazon_link"].get_value().strip()

        raw_g = self._entries["total_grams"].get_value().strip()
        raw_m = self._entries["total_meters"].get_value().strip()
        raw_p = self._entries["total_price"].get_value().strip()
        notes = self._entries["notes"].get_value().strip()

        total_grams = None
        total_meters = None
        total_price = 0.0

        if raw_g:
            try:
                total_grams = float(raw_g)
            except ValueError:
                messagebox.showerror("Invalid Input", "Total Grams must be a number.", parent=self)
                return

        if raw_m:
            try:
                total_meters = float(raw_m)
            except ValueError:
                messagebox.showerror("Invalid Input", "Total Meters must be a number.", parent=self)
                return

        if not total_grams and not total_meters:
            messagebox.showerror("Missing Field",
                                 "Enter at least one of: Total Grams or Total Meters.", parent=self)
            return

        if raw_p:
            try:
                total_price = float(raw_p)
            except ValueError:
                messagebox.showerror("Invalid Input", "Total Price must be a number.", parent=self)
                return
        else:
            messagebox.showerror("Missing Field", "Total Amazon Price is required.", parent=self)
            return

        import uuid
        fid = self._editing.id if self._editing else str(uuid.uuid4())[:8]
        self.result = Filament(fid, name, link, total_grams, total_meters, total_price, notes)
        self.destroy()


# ─────────────────────────────────────────────
#  FILAMENT ROW WIDGET
# ─────────────────────────────────────────────
class FilamentRow(tk.Frame):
    ROW_H = 58

    def __init__(self, parent, filament: Filament, row_index: int,
                 on_edit, on_delete, **kw):
        bg = C["row_even"] if row_index % 2 == 0 else C["row_odd"]
        super().__init__(parent, bg=bg, height=self.ROW_H, **kw)
        self.pack_propagate(False)
        self._fil = filament
        self._bg = bg
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._grams_var = tk.StringVar()
        self._meters_var = tk.StringVar()
        self._cost_var = tk.StringVar(value="—")
        self._grams_var.trace_add("write", self._recalc)
        self._meters_var.trace_add("write", self._recalc)
        self._build()
        self._setup_hover()

    # ── build ────────────────────────────────
    def _build(self):
        FONT = ("SF Pro Display", 12) if platform.system() == "Darwin" else ("Segoe UI", 11)
        FONT_SM = ("SF Pro Display", 10) if platform.system() == "Darwin" else ("Segoe UI", 9)
        FONT_B = ("SF Pro Display", 12, "bold") if platform.system() == "Darwin" else ("Segoe UI", 11, "bold")

        # ── Left: name link + notes ──────────
        left = tk.Frame(self, bg=self._bg)
        left.place(relx=0, rely=0, relwidth=0.38, relheight=1)

        name_lbl = tk.Label(left, text=self._fil.name, bg=self._bg,
                            fg=C["accent"], font=FONT_B,
                            anchor="w", cursor="hand2")
        name_lbl.pack(side="top", fill="x", padx=(14, 4), pady=(10, 0))
        if self._fil.amazon_link:
            name_lbl.bind("<ButtonRelease-1>",
                          lambda e: webbrowser.open(self._fil.amazon_link))
            name_lbl.bind("<Enter>", lambda e: name_lbl.config(fg=C["accent_hover"]))
            name_lbl.bind("<Leave>", lambda e: name_lbl.config(fg=C["accent"]))

        sub_parts = []
        if self._fil.total_grams:
            sub_parts.append(f"{self._fil.total_grams:.0f}g")
        if self._fil.total_meters:
            sub_parts.append(f"{self._fil.total_meters:.0f}m")
        sub_parts.append(f"${self._fil.total_price:.2f}")
        if self._fil.notes:
            sub_parts.append(f"· {self._fil.notes[:30]}")
        sub_text = "  ·  ".join(sub_parts)
        tk.Label(left, text=sub_text, bg=self._bg,
                 fg=C["text_dim"], font=FONT_SM,
                 anchor="w").pack(side="top", fill="x", padx=(14, 4))

        # ── Middle: input fields ─────────────
        mid = tk.Frame(self, bg=self._bg)
        mid.place(relx=0.38, rely=0, relwidth=0.38, relheight=1)

        def make_input(parent, label, var, show):
            if not show:
                return
            col = tk.Frame(parent, bg=self._bg)
            col.pack(side="left", padx=8, pady=8)
            tk.Label(col, text=label, bg=self._bg, fg=C["text_dim"],
                     font=FONT_SM).pack(anchor="w")
            ent = tk.Entry(col, textvariable=var, width=9,
                           bg=C["input_bg"], fg=C["text"],
                           insertbackground=C["text"], relief="flat",
                           highlightthickness=1,
                           highlightbackground=C["border"],
                           highlightcolor=C["accent"],
                           font=FONT)
            ent.pack(ipady=4)

        make_input(mid, "Grams used", self._grams_var, bool(self._fil.total_grams))
        make_input(mid, "Meters used", self._meters_var, bool(self._fil.total_meters))

        # ── Right: cost + actions ────────────
        right = tk.Frame(self, bg=self._bg)
        right.place(relx=0.76, rely=0, relwidth=0.24, relheight=1)

        cost_lbl = tk.Label(right, textvariable=self._cost_var,
                            bg=self._bg, fg=C["accent2"],
                            font=("SF Pro Display", 18, "bold") if platform.system() == "Darwin"
                            else ("Segoe UI", 15, "bold"))
        cost_lbl.pack(side="top", pady=(8, 0))

        action_frame = tk.Frame(right, bg=self._bg)
        action_frame.pack(side="top")

        edit_lbl = tk.Label(action_frame, text="✏", bg=self._bg,
                            fg=C["text_dim"], font=("Arial", 13), cursor="hand2")
        edit_lbl.pack(side="left", padx=4)
        edit_lbl.bind("<ButtonRelease-1>", lambda e: self._on_edit(self._fil))
        edit_lbl.bind("<Enter>", lambda e: edit_lbl.config(fg=C["text"]))
        edit_lbl.bind("<Leave>", lambda e: edit_lbl.config(fg=C["text_dim"]))

        del_lbl = tk.Label(action_frame, text="🗑", bg=self._bg,
                           fg=C["text_dim"], font=("Arial", 13), cursor="hand2")
        del_lbl.pack(side="left", padx=4)
        del_lbl.bind("<ButtonRelease-1>", lambda e: self._on_delete(self._fil))
        del_lbl.bind("<Enter>", lambda e: del_lbl.config(fg=C["danger"]))
        del_lbl.bind("<Leave>", lambda e: del_lbl.config(fg=C["text_dim"]))

        # separator line
        sep = tk.Frame(self, bg=C["border"], height=1)
        sep.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

    # ── hover highlight ──────────────────────
    def _setup_hover(self):
        def enter(_=None):
            self._set_bg(C["row_hover"])
        def leave(_=None):
            self._set_bg(self._bg)
        self.bind("<Enter>", enter)
        self.bind("<Leave>", leave)
        for child in self.winfo_children():
            child.bind("<Enter>", enter)
            child.bind("<Leave>", leave)

    def _set_bg(self, color):
        try:
            self.config(bg=color)
            for child in self.winfo_children():
                child.config(bg=color)
                for sub in child.winfo_children():
                    sub.config(bg=color)
        except Exception:
            pass

    # ── cost recalculation ───────────────────
    def _recalc(self, *_):
        g_str = self._grams_var.get().strip()
        m_str = self._meters_var.get().strip()
        g = None
        m = None
        try:
            if g_str:
                g = float(g_str)
        except ValueError:
            pass
        try:
            if m_str:
                m = float(m_str)
        except ValueError:
            pass

        cost = self._fil.cost_for(g, m)
        if cost is not None:
            self._cost_var.set(f"${cost:.2f}")
        else:
            self._cost_var.set("—")


# ─────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────
class SullybaseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sullybase Filament Cost Finder")
        self.configure(bg=C["bg"])
        self.geometry("960x680")
        self.minsize(780, 500)

        # macOS title bar colour hint
        if platform.system() == "Darwin":
            try:
                self.tk.call("::tk::unsupported::MacWindowStyle",
                             "appearance", self._w, "NSAppearanceNameDarkAqua")
            except Exception:
                pass

        self._filaments: list[Filament] = load_filaments()
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._refresh_list())
        self._row_widgets: list[FilamentRow] = []

        self._build_ui()
        self._refresh_list()

    # ── UI skeleton ──────────────────────────
    def _build_ui(self):
        FONT_TITLE = ("SF Pro Display", 20, "bold") if platform.system() == "Darwin" else ("Segoe UI", 17, "bold")
        FONT_SUB = ("SF Pro Display", 11) if platform.system() == "Darwin" else ("Segoe UI", 10)

        # ── Top bar ──────────────────────────
        top = tk.Frame(self, bg=C["header_bg"], height=64)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        tk.Label(top, text="Sullybase", bg=C["header_bg"],
                 fg=C["accent"], font=FONT_TITLE).pack(side="left", padx=(20, 4), pady=14)
        tk.Label(top, text="Filament Cost Finder", bg=C["header_bg"],
                 fg=C["text_dim"], font=FONT_SUB).pack(side="left", pady=20)

        # Plus button (top right)
        plus_btn = RoundedButton(top, text="＋ Add Filament",
                                 command=self._add_filament,
                                 width=148, height=36)
        plus_btn.pack(side="right", padx=18, pady=14)

        # ── Search bar ───────────────────────
        search_bar = tk.Frame(self, bg=C["surface"], pady=10)
        search_bar.pack(fill="x", side="top")

        search_wrap = tk.Frame(search_bar, bg=C["input_bg"],
                               highlightthickness=1,
                               highlightbackground=C["border"],
                               highlightcolor=C["accent"])
        search_wrap.pack(side="left", fill="x", expand=True, padx=20)

        tk.Label(search_wrap, text="🔍", bg=C["input_bg"],
                 fg=C["text_dim"], font=("Arial", 13)).pack(side="left", padx=(10, 4))

        search_ent = tk.Entry(search_wrap, textvariable=self._search_var,
                              bg=C["input_bg"], fg=C["text"],
                              insertbackground=C["text"], relief="flat",
                              font=("SF Pro Display", 12) if platform.system() == "Darwin"
                              else ("Segoe UI", 11),
                              width=40)
        search_ent.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
        search_ent.insert(0, "Search filaments…")
        search_ent.config(fg=C["text_dim"])

        def sf_focus_in(_):
            if search_ent.get() == "Search filaments…":
                search_ent.delete(0, tk.END)
                search_ent.config(fg=C["text"])
        def sf_focus_out(_):
            if not search_ent.get():
                search_ent.insert(0, "Search filaments…")
                search_ent.config(fg=C["text_dim"])
        search_ent.bind("<FocusIn>", sf_focus_in)
        search_ent.bind("<FocusOut>", sf_focus_out)

        # ── Column headers ───────────────────
        header = tk.Frame(self, bg=C["header_bg"], height=32)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        FONT_H = ("SF Pro Display", 10, "bold") if platform.system() == "Darwin" else ("Segoe UI", 9, "bold")
        for text, rx, rw in [
            ("FILAMENT", 0.0, 0.38),
            ("USAGE INPUT", 0.38, 0.38),
            ("PRINT COST", 0.76, 0.24),
        ]:
            tk.Label(header, text=text, bg=C["header_bg"],
                     fg=C["text_dim"], font=FONT_H,
                     anchor="w").place(relx=rx, rely=0,
                                       relwidth=rw, relheight=1,
                                       x=14)

        # ── Scrollable list ──────────────────
        list_outer = tk.Frame(self, bg=C["bg"])
        list_outer.pack(fill="both", expand=True, side="top")

        canvas = tk.Canvas(list_outer, bg=C["bg"],
                           highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(list_outer, orient="vertical",
                                  command=canvas.yview,
                                  bg=C["surface2"],
                                  troughcolor=C["bg"],
                                  activebackground=C["accent"])
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._list_frame = tk.Frame(canvas, bg=C["bg"])
        self._list_window = canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw")

        def on_configure(_):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def on_canvas_resize(e):
            canvas.itemconfig(self._list_window, width=e.width)

        self._list_frame.bind("<Configure>", on_configure)
        canvas.bind("<Configure>", on_canvas_resize)

        # Mouse wheel
        def on_mousewheel(e):
            delta = -1 * (e.delta // 120) if platform.system() == "Windows" \
                else -1 * e.delta
            canvas.yview_scroll(delta, "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        self._canvas = canvas

        # ── Status bar ───────────────────────
        status = tk.Frame(self, bg=C["header_bg"], height=28)
        status.pack(fill="x", side="bottom")
        status.pack_propagate(False)
        self._status_var = tk.StringVar(value="")
        tk.Label(status, textvariable=self._status_var,
                 bg=C["header_bg"], fg=C["text_dim"],
                 font=("SF Pro Display", 10) if platform.system() == "Darwin"
                 else ("Segoe UI", 9)).pack(side="left", padx=16)

        data_path_lbl = tk.Label(status, text=f"Data: {DATA_FILE}",
                                  bg=C["header_bg"], fg=C["text_dim"],
                                  font=("SF Pro Display", 9) if platform.system() == "Darwin"
                                  else ("Segoe UI", 8),
                                  cursor="hand2")
        data_path_lbl.pack(side="right", padx=16)
        data_path_lbl.bind("<ButtonRelease-1>",
                            lambda e: self._reveal_data_folder())

    # ── refresh list ─────────────────────────
    def _refresh_list(self):
        raw = self._search_var.get().strip()
        query = "" if raw == "Search filaments…" else raw.lower()

        for w in self._row_widgets:
            w.destroy()
        self._row_widgets.clear()

        filtered = [
            f for f in self._filaments
            if query in f.name.lower() or query in f.notes.lower()
        ] if query else self._filaments[:]

        if not filtered:
            msg = "No filaments found. Click ＋ Add Filament to get started." \
                if not self._filaments else "No results match your search."
            lbl = tk.Label(self._list_frame, text=msg,
                           bg=C["bg"], fg=C["text_dim"],
                           font=("SF Pro Display", 13) if platform.system() == "Darwin"
                           else ("Segoe UI", 12),
                           pady=40)
            lbl.pack(fill="x")
            self._row_widgets.append(lbl)  # type: ignore
        else:
            for i, fil in enumerate(filtered):
                row = FilamentRow(
                    self._list_frame, fil, i,
                    on_edit=self._edit_filament,
                    on_delete=self._delete_filament,
                )
                row.pack(fill="x")
                self._row_widgets.append(row)

        count = len(self._filaments)
        self._status_var.set(f"{count} filament{'s' if count != 1 else ''}")

    # ── actions ──────────────────────────────
    def _add_filament(self):
        dlg = FilamentDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._filaments.append(dlg.result)
            save_filaments(self._filaments)
            self._refresh_list()

    def _edit_filament(self, filament: Filament):
        dlg = FilamentDialog(self, filament)
        self.wait_window(dlg)
        if dlg.result:
            idx = next((i for i, f in enumerate(self._filaments)
                        if f.id == filament.id), None)
            if idx is not None:
                self._filaments[idx] = dlg.result
            save_filaments(self._filaments)
            self._refresh_list()

    def _delete_filament(self, filament: Filament):
        if messagebox.askyesno(
            "Delete Filament",
            f"Delete '{filament.name}'?\nThis cannot be undone.",
            parent=self
        ):
            self._filaments = [f for f in self._filaments if f.id != filament.id]
            save_filaments(self._filaments)
            self._refresh_list()

    def _reveal_data_folder(self):
        folder = str(DATA_FILE.parent)
        if platform.system() == "Darwin":
            os.system(f'open "{folder}"')
        elif platform.system() == "Windows":
            os.startfile(folder)
        else:
            os.system(f'xdg-open "{folder}"')


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = SullybaseApp()
    app.mainloop()
