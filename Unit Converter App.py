#!/usr/bin/env python3
"""
Measurements
A Tkinter GUI app for converting between common units (length, weight,
temperature, volume) and live currency exchange rates.

Currency rates are fetched from the free, no-API-key Frankfurter API
(https://www.frankfurter.app/), which sources rates from the European
Central Bank. An internet connection is required for currency conversion;
unit conversions (length/weight/temperature/volume) work fully offline.

Run with:  python measurements.py
Requires:  Python 3.8+ (uses only the standard library)
"""

import json
import threading
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta

APP_TITLE = "Measurements"
CURRENCY_API_BASE = "https://api.frankfurter.app"


# --------------------------------------------------------------------------
# Unit definitions
# --------------------------------------------------------------------------
# Each entry maps a unit name to a multiplier relative to a base unit for
# that category. Conversion is value_in_base = value * factor, then
# result = value_in_base / target_factor. Temperature is handled specially
# since it isn't a simple multiplicative relationship.

LENGTH_UNITS = {
    "Millimeters (mm)": 0.001,
    "Centimeters (cm)": 0.01,
    "Meters (m)": 1.0,
    "Kilometers (km)": 1000.0,
    "Inches (in)": 0.0254,
    "Feet (ft)": 0.3048,
    "Yards (yd)": 0.9144,
    "Miles (mi)": 1609.344,
    "Nautical Miles (nmi)": 1852.0,
}

WEIGHT_UNITS = {
    "Milligrams (mg)": 0.001,
    "Grams (g)": 1.0,
    "Kilograms (kg)": 1000.0,
    "Metric Tons (t)": 1_000_000.0,
    "Ounces (oz)": 28.349523125,
    "Pounds (lb)": 453.59237,
    "Stone (st)": 6350.29318,
    "US Tons": 907_184.74,
}

VOLUME_UNITS = {
    "Milliliters (mL)": 0.001,
    "Liters (L)": 1.0,
    "Cubic Meters (m^3)": 1000.0,
    "Teaspoons (tsp)": 0.00492892,
    "Tablespoons (tbsp)": 0.0147868,
    "Fluid Ounces (US fl oz)": 0.0295735,
    "Cups (US cup)": 0.236588,
    "Pints (US pt)": 0.473176,
    "Quarts (US qt)": 0.946353,
    "Gallons (US gal)": 3.78541,
    "Imperial Gallons": 4.54609,
}

TEMPERATURE_UNITS = ["Celsius (°C)", "Fahrenheit (°F)", "Kelvin (K)"]


def convert_linear(value, units_dict, from_unit, to_unit):
    base_value = value * units_dict[from_unit]
    return base_value / units_dict[to_unit]


def convert_temperature(value, from_unit, to_unit):
    # Normalize to Celsius first
    if from_unit.startswith("Celsius"):
        celsius = value
    elif from_unit.startswith("Fahrenheit"):
        celsius = (value - 32) * 5.0 / 9.0
    elif from_unit.startswith("Kelvin"):
        celsius = value - 273.15
    else:
        raise ValueError("Unknown temperature unit")

    if to_unit.startswith("Celsius"):
        return celsius
    elif to_unit.startswith("Fahrenheit"):
        return celsius * 9.0 / 5.0 + 32
    elif to_unit.startswith("Kelvin"):
        return celsius + 273.15
    else:
        raise ValueError("Unknown temperature unit")


# --------------------------------------------------------------------------
# Currency rate fetching (with simple in-memory caching)
# --------------------------------------------------------------------------

class CurrencyRates:
    """Fetches and caches exchange rates from the Frankfurter API."""

    CACHE_LIFETIME = timedelta(minutes=10)

    def __init__(self):
        self._currencies = None  # dict: code -> full name
        self._rate_cache = {}    # base_currency -> (timestamp, {code: rate})

    def get_currency_list(self):
        """Returns dict of currency code -> name, fetching once and caching."""
        if self._currencies is not None:
            return self._currencies
        url = f"{CURRENCY_API_BASE}/currencies"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self._currencies = data
        return data

    def get_rates(self, base_currency):
        """Returns dict of currency code -> rate relative to base_currency."""
        now = datetime.utcnow()
        cached = self._rate_cache.get(base_currency)
        if cached and (now - cached[0]) < self.CACHE_LIFETIME:
            return cached[1]

        url = f"{CURRENCY_API_BASE}/latest?from={base_currency}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rates = data.get("rates", {})
        rates[base_currency] = 1.0
        self._rate_cache[base_currency] = (now, rates)
        return rates

    def convert(self, amount, from_currency, to_currency):
        if from_currency == to_currency:
            return amount
        rates = self.get_rates(from_currency)
        if to_currency not in rates:
            raise ValueError(f"No rate available for {to_currency}")
        return amount * rates[to_currency]


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------

class UnitConverterFrame(ttk.Frame):
    """Generic frame for a linear-multiplier unit category (length/weight/volume)."""

    def __init__(self, parent, units_dict, value_label="Value"):
        super().__init__(parent, padding=20)
        self.units_dict = units_dict
        unit_names = list(units_dict.keys())

        self.columnconfigure(1, weight=1)

        ttk.Label(self, text=value_label + ":", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="w", pady=8
        )
        self.value_var = tk.StringVar()
        value_entry = ttk.Entry(self, textvariable=self.value_var, font=("Segoe UI", 11))
        value_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=8, padx=(10, 0))
        value_entry.bind("<Return>", lambda e: self.do_convert())

        ttk.Label(self, text="From:", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="w", pady=8
        )
        self.from_var = tk.StringVar(value=unit_names[0])
        from_combo = ttk.Combobox(
            self, textvariable=self.from_var, values=unit_names, state="readonly", width=28
        )
        from_combo.grid(row=1, column=1, sticky="ew", pady=8, padx=(10, 0))

        ttk.Label(self, text="To:", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky="w", pady=8
        )
        self.to_var = tk.StringVar(value=unit_names[1] if len(unit_names) > 1 else unit_names[0])
        to_combo = ttk.Combobox(
            self, textvariable=self.to_var, values=unit_names, state="readonly", width=28
        )
        to_combo.grid(row=2, column=1, sticky="ew", pady=8, padx=(10, 0))

        swap_btn = ttk.Button(self, text="⇄ Swap", command=self.swap_units)
        swap_btn.grid(row=1, column=2, rowspan=2, padx=(10, 0), sticky="ns")

        convert_btn = ttk.Button(self, text="Convert", command=self.do_convert)
        convert_btn.grid(row=3, column=0, columnspan=3, pady=(15, 5), sticky="ew")

        self.result_var = tk.StringVar(value="Result will appear here")
        result_label = ttk.Label(
            self,
            textvariable=self.result_var,
            font=("Segoe UI", 13, "bold"),
            foreground="#1a5fb4",
            anchor="center",
        )
        result_label.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky="ew")

        value_entry.focus_set()

    def swap_units(self):
        f, t = self.from_var.get(), self.to_var.get()
        self.from_var.set(t)
        self.to_var.set(f)

    def do_convert(self):
        raw = self.value_var.get().strip()
        if not raw:
            messagebox.showwarning(APP_TITLE, "Please enter a value to convert.")
            return
        try:
            value = float(raw)
        except ValueError:
            messagebox.showerror(APP_TITLE, "Please enter a valid number.")
            return

        from_unit = self.from_var.get()
        to_unit = self.to_var.get()
        try:
            result = convert_linear(value, self.units_dict, from_unit, to_unit)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Conversion error: {exc}")
            return

        self.result_var.set(f"{value:g} {from_unit} = {result:,.6g} {to_unit}")


class TemperatureFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=20)
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Value:", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="w", pady=8
        )
        self.value_var = tk.StringVar()
        value_entry = ttk.Entry(self, textvariable=self.value_var, font=("Segoe UI", 11))
        value_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=8, padx=(10, 0))
        value_entry.bind("<Return>", lambda e: self.do_convert())

        ttk.Label(self, text="From:", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="w", pady=8
        )
        self.from_var = tk.StringVar(value=TEMPERATURE_UNITS[0])
        ttk.Combobox(
            self, textvariable=self.from_var, values=TEMPERATURE_UNITS,
            state="readonly", width=28
        ).grid(row=1, column=1, sticky="ew", pady=8, padx=(10, 0))

        ttk.Label(self, text="To:", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky="w", pady=8
        )
        self.to_var = tk.StringVar(value=TEMPERATURE_UNITS[1])
        ttk.Combobox(
            self, textvariable=self.to_var, values=TEMPERATURE_UNITS,
            state="readonly", width=28
        ).grid(row=2, column=1, sticky="ew", pady=8, padx=(10, 0))

        ttk.Button(self, text="⇄ Swap", command=self.swap_units).grid(
            row=1, column=2, rowspan=2, padx=(10, 0), sticky="ns"
        )

        ttk.Button(self, text="Convert", command=self.do_convert).grid(
            row=3, column=0, columnspan=3, pady=(15, 5), sticky="ew"
        )

        self.result_var = tk.StringVar(value="Result will appear here")
        ttk.Label(
            self, textvariable=self.result_var, font=("Segoe UI", 13, "bold"),
            foreground="#1a5fb4", anchor="center"
        ).grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky="ew")

        value_entry.focus_set()

    def swap_units(self):
        f, t = self.from_var.get(), self.to_var.get()
        self.from_var.set(t)
        self.to_var.set(f)

    def do_convert(self):
        raw = self.value_var.get().strip()
        if not raw:
            messagebox.showwarning(APP_TITLE, "Please enter a value to convert.")
            return
        try:
            value = float(raw)
        except ValueError:
            messagebox.showerror(APP_TITLE, "Please enter a valid number.")
            return

        from_unit = self.from_var.get()
        to_unit = self.to_var.get()
        try:
            result = convert_temperature(value, from_unit, to_unit)
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"Conversion error: {exc}")
            return

        self.result_var.set(f"{value:g} {from_unit} = {result:,.4f} {to_unit}")


class CurrencyFrame(ttk.Frame):
    """Live currency conversion using the free Frankfurter API."""

    FALLBACK_CURRENCIES = {
        "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound",
        "JPY": "Japanese Yen", "CAD": "Canadian Dollar", "AUD": "Australian Dollar",
        "CHF": "Swiss Franc", "CNY": "Chinese Yuan", "INR": "Indian Rupee",
        "MXN": "Mexican Peso",
    }

    def __init__(self, parent, rates_client: CurrencyRates):
        super().__init__(parent, padding=20)
        self.rates_client = rates_client
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Amount:", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="w", pady=8
        )
        self.value_var = tk.StringVar(value="1")
        value_entry = ttk.Entry(self, textvariable=self.value_var, font=("Segoe UI", 11))
        value_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=8, padx=(10, 0))
        value_entry.bind("<Return>", lambda e: self.do_convert())

        ttk.Label(self, text="From:", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="w", pady=8
        )
        self.from_var = tk.StringVar(value="USD")
        self.from_combo = ttk.Combobox(
            self, textvariable=self.from_var, state="readonly", width=28
        )
        self.from_combo.grid(row=1, column=1, sticky="ew", pady=8, padx=(10, 0))

        ttk.Label(self, text="To:", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky="w", pady=8
        )
        self.to_var = tk.StringVar(value="EUR")
        self.to_combo = ttk.Combobox(
            self, textvariable=self.to_var, state="readonly", width=28
        )
        self.to_combo.grid(row=2, column=1, sticky="ew", pady=8, padx=(10, 0))

        ttk.Button(self, text="⇄ Swap", command=self.swap_units).grid(
            row=1, column=2, rowspan=2, padx=(10, 0), sticky="ns"
        )

        self.convert_btn = ttk.Button(self, text="Convert", command=self.do_convert)
        self.convert_btn.grid(row=3, column=0, columnspan=3, pady=(15, 5), sticky="ew")

        self.result_var = tk.StringVar(value="Result will appear here")
        ttk.Label(
            self, textvariable=self.result_var, font=("Segoe UI", 13, "bold"),
            foreground="#1a5fb4", anchor="center"
        ).grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky="ew")

        self.status_var = tk.StringVar(value="Loading currency list…")
        ttk.Label(
            self, textvariable=self.status_var, font=("Segoe UI", 9),
            foreground="#666666", anchor="center"
        ).grid(row=5, column=0, columnspan=3, pady=(8, 0), sticky="ew")

        self._currency_codes = []
        value_entry.focus_set()
        self.load_currency_list_async()

    # -- currency list loading -------------------------------------------------
    def load_currency_list_async(self):
        thread = threading.Thread(target=self._fetch_currency_list, daemon=True)
        thread.start()

    def _fetch_currency_list(self):
        try:
            currencies = self.rates_client.get_currency_list()
            codes = sorted(currencies.keys())
            self.after(0, lambda: self._populate_currency_list(codes, currencies))
        except Exception:
            # Fall back to a small built-in list if offline / API unreachable
            codes = sorted(self.FALLBACK_CURRENCIES.keys())
            self.after(0, lambda: self._populate_currency_list(
                codes, self.FALLBACK_CURRENCIES, offline=True
            ))

    def _populate_currency_list(self, codes, currencies, offline=False):
        self._currency_codes = codes
        display_values = [f"{code} – {currencies.get(code, '')}".rstrip(" –") for code in codes]
        self.from_combo["values"] = display_values
        self.to_combo["values"] = display_values

        def find_display(code):
            for d in display_values:
                if d.startswith(code):
                    return d
            return display_values[0] if display_values else ""

        self.from_var.set(find_display("USD") if "USD" in codes else (display_values[0] if display_values else ""))
        self.to_var.set(find_display("EUR") if "EUR" in codes else (display_values[1] if len(display_values) > 1 else ""))

        if offline:
            self.status_var.set("Could not reach the currency API — showing a limited offline list.")
        else:
            self.status_var.set("Rates provided by the Frankfurter API (European Central Bank data).")

    # -- conversion --------------------------------------------------------
    def swap_units(self):
        f, t = self.from_var.get(), self.to_var.get()
        self.from_var.set(t)
        self.to_var.set(f)

    @staticmethod
    def _extract_code(display_value):
        return display_value.split(" ")[0].strip() if display_value else ""

    def do_convert(self):
        raw = self.value_var.get().strip()
        if not raw:
            messagebox.showwarning(APP_TITLE, "Please enter an amount to convert.")
            return
        try:
            amount = float(raw)
        except ValueError:
            messagebox.showerror(APP_TITLE, "Please enter a valid number.")
            return

        from_code = self._extract_code(self.from_var.get())
        to_code = self._extract_code(self.to_var.get())
        if not from_code or not to_code:
            messagebox.showwarning(APP_TITLE, "Please select both currencies.")
            return

        self.convert_btn.config(state="disabled")
        self.status_var.set("Fetching live rates…")
        thread = threading.Thread(
            target=self._do_convert_async, args=(amount, from_code, to_code), daemon=True
        )
        thread.start()

    def _do_convert_async(self, amount, from_code, to_code):
        try:
            result = self.rates_client.convert(amount, from_code, to_code)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.after(0, lambda: self._show_result(amount, from_code, to_code, result, timestamp))
        except urllib.error.URLError:
            self.after(0, lambda: self._show_error(
                "Could not connect to the currency API. Check your internet connection."
            ))
        except Exception as exc:
            self.after(0, lambda: self._show_error(f"Conversion error: {exc}"))

    def _show_result(self, amount, from_code, to_code, result, timestamp):
        self.result_var.set(f"{amount:,.2f} {from_code} = {result:,.4f} {to_code}")
        self.status_var.set(f"Rates updated at {timestamp} (cached for 10 minutes).")
        self.convert_btn.config(state="normal")

    def _show_error(self, message):
        self.status_var.set(message)
        messagebox.showerror(APP_TITLE, message)
        self.convert_btn.config(state="normal")


class MeasurementsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("480x420")
        self.minsize(420, 400)

        try:
            style = ttk.Style(self)
            if "vista" in style.theme_names():
                style.theme_use("vista")
            elif "clam" in style.theme_names():
                style.theme_use("clam")
        except Exception:
            pass

        header = ttk.Frame(self, padding=(20, 16, 20, 0))
        header.pack(fill="x")
        ttk.Label(
            header, text="📐 Measurements", font=("Segoe UI", 16, "bold")
        ).pack(side="left")
        ttk.Label(
            header, text="Unit & Currency Converter", font=("Segoe UI", 9),
            foreground="#666666"
        ).pack(side="left", padx=(10, 0), pady=(6, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=15, pady=15)

        rates_client = CurrencyRates()

        notebook.add(UnitConverterFrame(notebook, LENGTH_UNITS), text="Length")
        notebook.add(UnitConverterFrame(notebook, WEIGHT_UNITS), text="Weight")
        notebook.add(TemperatureFrame(notebook), text="Temperature")
        notebook.add(UnitConverterFrame(notebook, VOLUME_UNITS), text="Volume")
        notebook.add(CurrencyFrame(notebook, rates_client), text="Currency")


def main():
    app = MeasurementsApp()
    app.mainloop()


if __name__ == "__main__":
    main()