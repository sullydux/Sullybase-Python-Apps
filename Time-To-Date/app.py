#!/usr/bin/env python3
import os
import datetime
from datetime import datetime as dt
import rumps

# ── persistence (plain text, no pickle fragility) ────────────────────────────
DATA_DIR = os.path.expanduser("~/Library/Application Support/PY-timer")
DATE_FILE = os.path.join(DATA_DIR, "target_datetime.txt")
ALARM_FILE = os.path.join(DATA_DIR, "alarm_mode.txt")
TIMER_FILE = os.path.join(DATA_DIR, "timer_running.txt")
ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.png")
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def load_target():
    try:
        with open(DATE_FILE) as f:
            return dt.strptime(f.read().strip(), DATE_FMT)
    except Exception:
        return dt.now() + datetime.timedelta(hours=1)


def save_target(target):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATE_FILE, "w") as f:
        f.write(target.strftime(DATE_FMT))


def load_alarm_mode():
    try:
        with open(ALARM_FILE) as f:
            return f.read().strip().lower() == "true"
    except Exception:
        return False


def save_alarm_mode(enabled):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(ALARM_FILE, "w") as f:
        f.write("true" if enabled else "false")


def load_timer_state():
    try:
        with open(TIMER_FILE) as f:
            return f.read().strip().lower() == "true"
    except Exception:
        return True


def save_timer_state(running):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TIMER_FILE, "w") as f:
        f.write("true" if running else "false")


# ── formatting ────────────────────────────────────────────────────────────────
def fmt(delta):
    s = int(abs(delta.total_seconds()))
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    if d:
        return f"{d}d {h:02d}h {m:02d}m {s:02d}s"
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


# ── app ───────────────────────────────────────────────────────────────────────
class TimeToDateApp(rumps.App):

    def __init__(self):
        super().__init__("⏱", quit_button=None)
        self.target = load_target()
        self.alarm_enabled = load_alarm_mode()
        self.timer_running = load_timer_state()
        self.prev_was_negative = None

        # Set icon when timer is off
        if not self.timer_running:
            self.icon = ICON_PATH
            self.title = ""
        else:
            self.icon = None

        self.info_item = rumps.MenuItem("", callback=None)
        self.alarm_menu_item = rumps.MenuItem(
            f"Alarm Mode: {'ON' if self.alarm_enabled else 'OFF'}",
            callback=self.toggle_alarm,
        )
        self.timer_menu_item = rumps.MenuItem(
            f"Timer: {'ON' if self.timer_running else 'OFF'}",
            callback=self.toggle_timer,
        )

        self.menu = [
            self.info_item,
            None,
            rumps.MenuItem("Set target date/time...", callback=self.set_datetime),
            rumps.MenuItem("View Target Time", callback=self.view_target),
            self.alarm_menu_item,
            self.timer_menu_item,
            None,
            rumps.MenuItem("Quick: T+0 (Now)", callback=self.quick_now),
            rumps.MenuItem("Quick: T-1 Hour", callback=self.quick_plus_one_hour),
            rumps.MenuItem("Quick: T-1 Day", callback=self.quick_plus_one_day),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        self.timer = rumps.Timer(self._tick, 1)
        self.timer.start()
        self._tick(None)

    def _tick(self, _sender):
        now = dt.now()
        diff = self.target - now
        is_negative = diff.total_seconds() < 0

        if self.timer_running:
            self.icon = None
            label = "T-" if not is_negative else "T+"
            self.title = f"{label} {fmt(diff)}"
        else:
            self.icon = ICON_PATH
            self.title = ""

        self.info_item.title = (
            f"  Target: {self.target.strftime('%Y-%m-%d  %H:%M:%S')}"
        )

        # Trigger alarm only at the exact moment of transition to T+0 (and only if timer is running)
        if self.timer_running and self.alarm_enabled and self.prev_was_negative is False and is_negative:
            self.trigger_alarm()

        self.prev_was_negative = is_negative

    def set_datetime(self, _sender):
        # Step 1: date
        w = rumps.Window(
            title="Set Target Date",
            message="Date (YYYY-MM-DD):",
            default_text=self.target.strftime("%Y-%m-%d"),
            ok="Next", cancel="Cancel",
            dimensions=(220, 24),
        )
        r = w.run()
        if not r.clicked:
            return
        date_str = r.text.strip()

        # Step 2: time
        w2 = rumps.Window(
            title="Set Target Time",
            message="Time (HH:MM or HH:MM:SS):",
            default_text=self.target.strftime("%H:%M:%S"),
            ok="Next", cancel="Cancel",
            dimensions=(220, 24),
        )
        r2 = w2.run()
        if not r2.clicked:
            return
        time_str = r2.text.strip()

        # Step 3: alarm mode choice
        alarm_choice = rumps.alert(
            title="Enable Alarm?",
            message="Should the alarm sound when target time is reached?",
            ok="Yes",
            cancel="No",
        )
        alarm_enabled = alarm_choice == 0

        # Parse — accept HH:MM or HH:MM:SS
        fmt_str = DATE_FMT if len(time_str) > 5 else "%Y-%m-%d %H:%M"
        try:
            new_target = dt.strptime(f"{date_str} {time_str}", fmt_str)
        except ValueError:
            rumps.alert(
                title="Invalid input",
                message=f'Could not parse "{date_str} {time_str}".\nUse YYYY-MM-DD and HH:MM:SS.',
            )
            return

        self.target = new_target
        self.alarm_enabled = alarm_enabled
        save_target(new_target)
        save_alarm_mode(alarm_enabled)
        self._tick(None)
        self.update_menu()
        rumps.notification(
            "TimeToDate", "Saved",
            f"Counting to {new_target.strftime('%Y-%m-%d %H:%M:%S')}\nAlarm: {'ON' if alarm_enabled else 'OFF'}",
        )

    def view_target(self, _sender):
        target_str = self.target.strftime("%A, %B %d, %Y at %H:%M:%S")
        rumps.alert(title="Target Date & Time", message=target_str)

    def quick_now(self, _sender):
        self.target = dt.now()
        save_target(self.target)
        self._tick(None)
        rumps.notification("TimeToDate", "Updated", "Target set to now!")

    def quick_plus_one_hour(self, _sender):
        self.target = dt.now() + datetime.timedelta(hours=1)
        save_target(self.target)
        self._tick(None)
        rumps.notification(
            "TimeToDate",
            "Updated",
            f"Target: {self.target.strftime('%Y-%m-%d %H:%M:%S')}",
        )

    def quick_plus_one_day(self, _sender):
        self.target = dt.now() + datetime.timedelta(days=1)
        save_target(self.target)
        self._tick(None)
        rumps.notification(
            "TimeToDate",
            "Updated",
            f"Target: {self.target.strftime('%Y-%m-%d %H:%M:%S')}",
        )

    def trigger_alarm(self):
        os.system('afplay /System/Library/Sounds/Submarine.aiff &')
        rumps.notification(
            "TimeToDate Alarm",
            "Time Reached!",
            f"Target time has been reached: {self.target.strftime('%H:%M:%S')}",
        )

    def toggle_alarm(self, _sender):
        self.alarm_enabled = not self.alarm_enabled
        save_alarm_mode(self.alarm_enabled)
        self.update_menu()
        rumps.notification(
            "TimeToDate",
            "Alarm Mode Updated",
            f"Alarm mode is now {'ON' if self.alarm_enabled else 'OFF'}",
        )

    def update_menu(self):
        self.alarm_menu_item.title = f"Alarm Mode: {'ON' if self.alarm_enabled else 'OFF'}"

    def toggle_timer(self, _sender):
        self.timer_running = not self.timer_running
        save_timer_state(self.timer_running)
        self.timer_menu_item.title = f"Timer: {'ON' if self.timer_running else 'OFF'}"
        rumps.notification(
            "TimeToDate",
            "Timer Updated",
            f"Timer is now {'ON' if self.timer_running else 'OFF'}",
        )

    def quit_app(self, _sender):
        self.timer.stop()
        rumps.quit_application()


if __name__ == "__main__":
    TimeToDateApp().run()