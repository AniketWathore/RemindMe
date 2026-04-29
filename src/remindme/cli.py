import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time

try:
    import curses
except Exception:
    curses = None


today = dt.date.today()
tomorrow = today + dt.timedelta(days=1)


def resolve_date(date_str: str) -> dt.date:
    lowered = date_str.lower()
    if lowered == "today":
        return today
    if lowered == "tomorrow":
        return tomorrow
    if "/" in date_str:
        day_str, month_str = date_str.split("/", 1)
    else:
        day_str, month_str = date_str.split()
    return dt.date(today.year, int(month_str), int(day_str))


def get_data_dir() -> str:
    home = os.path.expanduser("~")
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("APPDATA", home), "RemindMe")
    if sys.platform == "darwin":
        return os.path.join(home, "Library", "Application Support", "RemindMe")
    return os.path.join(home, ".local", "share", "remindme")


def get_data_path() -> str:
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "reminders.json")


def get_pid_path() -> str:
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "remindme.pid")


def load_reminders() -> dict:
    data_path = get_data_path()
    try:
        with open(data_path, "r") as file_handle:
            data = json.load(file_handle)
    except FileNotFoundError:
        data = {"reminders": []}
    except json.JSONDecodeError:
        data = {"reminders": []}
    if "reminders" not in data or not isinstance(data["reminders"], list):
        data["reminders"] = []
    return data


def save_reminders(data: dict) -> None:
    data_path = get_data_path()
    with open(data_path, "w") as file_handle:
        json.dump(data, file_handle, indent=4)


def get_next_id(existing_data: dict) -> int:
    max_id = 0
    for item in existing_data.get("reminders", []):
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("id"), int):
            max_id = max(max_id, item["id"])
            continue
        for value in item.values():
            if isinstance(value, dict) and isinstance(value.get("id"), int):
                max_id = max(max_id, value["id"])
    return max_id + 1


def get_reminder_entries(existing_data: dict) -> list:
    entries = []
    for index, item in enumerate(existing_data.get("reminders", [])):
        if isinstance(item, dict) and len(item) == 1:
            message, details = next(iter(item.items()))
        elif isinstance(item, dict) and "message" in item:
            message = item.get("message", "(no message)")
            details = item
        else:
            continue
        entries.append({"index": index, "message": message, "details": details})
    return entries


def parse_date_label(date_str: str) -> dt.date | None:
    lowered = date_str.strip().lower()
    if lowered == "today":
        return today
    if lowered == "tomorrow":
        return tomorrow
    if "/" in date_str:
        parts = date_str.split("/")
    else:
        parts = date_str.split()

    if len(parts) == 2:
        day_str, month_str = parts
        year = today.year
    elif len(parts) == 3:
        day_str, month_str, year_str = parts
        year = int(year_str)
    else:
        return None
    return dt.date(year, int(month_str), int(day_str))


def build_target_datetime(details: dict) -> dt.datetime | None:
    date_str = details.get("date", "")
    date_value = parse_date_label(date_str)
    if not date_value:
        return None
    hour = int(details.get("hour", 0))
    minute = int(details.get("minute", 0))
    return dt.datetime(
        date_value.year,
        date_value.month,
        date_value.day,
        hour,
        minute,
    )


def send_notification(title: str, message: str) -> bool:
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", title, message], check=False)
        return True
    if sys.platform == "darwin" and shutil.which("osascript"):
        script = (
            f'display notification "{message}" with title "{title}"'
        )
        subprocess.run(["osascript", "-e", script], check=False)
        return True
    if sys.platform.startswith("win") and shutil.which("powershell"):
        command = (
            "$title = '{0}'; $msg = '{1}'; "
            "[reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null; "
            "[reflection.assembly]::loadwithpartialname('System.Drawing') | Out-Null; "
            "$n = New-Object System.Windows.Forms.NotifyIcon; "
            "$n.Icon = [System.Drawing.SystemIcons]::Information; "
            "$n.BalloonTipTitle = $title; $n.BalloonTipText = $msg; "
            "$n.Visible = $true; $n.ShowBalloonTip(10000); "
            "Start-Sleep -Seconds 5; $n.Dispose();"
        ).format(title.replace("'", "''"), message.replace("'", "''"))
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", command], check=False
        )
        return True
    return False


def open_terminal_message(title: str, message: str) -> bool:
    terminals = [
        ("x-terminal-emulator", ["x-terminal-emulator", "-e"]),
        ("gnome-terminal", ["gnome-terminal", "--"]),
        ("konsole", ["konsole", "-e"]),
        ("xterm", ["xterm", "-e"]),
    ]
    for binary, prefix in terminals:
        if shutil.which(binary):
            cmd = prefix + [
                "bash",
                "-lc",
                f"echo '{title}: {message}'; read -r -p 'Press Enter to close'",
            ]
            subprocess.Popen(cmd)
            return True
    return False


def run_scheduler(poll_seconds: int = 30) -> None:
    pid_path = get_pid_path()
    with open(pid_path, "w") as file_handle:
        file_handle.write(str(os.getpid()))
    while True:
        data = load_reminders()
        entries = get_reminder_entries(data)
        changed = False
        now = dt.datetime.now()

        for entry in entries:
            details = entry["details"]
            if details.get("fired") is True:
                continue
            target_dt = build_target_datetime(details)
            if not target_dt:
                continue
            if now >= target_dt:
                title = "Reminder"
                message = entry["message"]
                notified = send_notification(title, message)
                if not notified:
                    open_terminal_message(title, message)
                details["fired"] = True
                changed = True

        if changed:
            save_reminders(data)

        time.sleep(poll_seconds)


def start_background_daemon() -> None:
    pid_path = get_pid_path()
    if os.path.exists(pid_path):
        try:
            with open(pid_path, "r") as file_handle:
                pid = int(file_handle.read().strip())
            if pid > 0:
                if sys.platform.startswith("win"):
                    return
                os.kill(pid, 0)
                return
        except (OSError, ValueError):
            pass
    args = [sys.executable, "-m", "remindme.cli", "--daemon"]
    subprocess.Popen(
        args,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def install_autostart() -> None:
    if sys.platform.startswith("win"):
        return
    if sys.platform == "darwin":
        return
    autostart_dir = os.path.expanduser("~/.config/autostart")
    os.makedirs(autostart_dir, exist_ok=True)
    desktop_path = os.path.join(autostart_dir, "remindme.desktop")
    exec_cmd = "remindme --daemon"

    content = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=RemindMe\n"
        "Comment=Run RemindMe in the background\n"
        f"Exec={exec_cmd}\n"
        "X-GNOME-Autostart-enabled=true\n"
    )
    with open(desktop_path, "w") as file_handle:
        file_handle.write(content)


def remove_autostart() -> None:
    if sys.platform.startswith("win"):
        return
    if sys.platform == "darwin":
        return
    desktop_path = os.path.expanduser("~/.config/autostart/remindme.desktop")
    if os.path.exists(desktop_path):
        os.remove(desktop_path)
    else:
        return


def select_reminders_with_curses(entries: list) -> list | None:
    if not entries:
        return []
    if curses is None:
        return None

    def run(stdscr):
        curses.use_default_colors()
        stdscr.bkgd(" ", curses.A_NORMAL)
        curses.curs_set(0)
        stdscr.keypad(True)
        selected = set()
        position = 0

        while True:
            stdscr.erase()
            header = "Delete Reminders (Up/Down, Space to toggle, Enter to confirm, q to cancel)"
            stdscr.addstr(0, 0, header[: max(0, curses.COLS - 1)])

            for idx, entry in enumerate(entries):
                details = entry["details"]
                date_str = details.get("date", "Unknown date")
                hour = details.get("hour", 0)
                minute = details.get("minute", 0)
                msg = entry["message"]
                marker = "[x]" if idx in selected else "[ ]"
                pointer = ">" if idx == position else " "
                line = f"{pointer} {marker} {msg} - {date_str} {int(hour):02d}:{int(minute):02d}"
                stdscr.addstr(idx + 2, 0, line[: max(0, curses.COLS - 1)])

            key = stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                position = max(0, position - 1)
            elif key in (curses.KEY_DOWN, ord("j")):
                position = min(len(entries) - 1, position + 1)
            elif key == ord(" "):
                if position in selected:
                    selected.remove(position)
                else:
                    selected.add(position)
            elif key in (10, 13):
                return list(selected)
            elif key in (ord("q"), 27):
                return None

    return curses.wrapper(run)


def select_reminders_fallback(entries: list) -> list | None:
    if not entries:
        return []
    print("Select reminders to delete (comma-separated numbers, blank to cancel):")
    for idx, entry in enumerate(entries, start=1):
        details = entry["details"]
        date_str = details.get("date", "Unknown date")
        hour = details.get("hour", 0)
        minute = details.get("minute", 0)
        print(f"  {idx}. {entry['message']} - {date_str} {int(hour):02d}:{int(minute):02d}")
    raw = input("> ").strip()
    if not raw:
        return None
    selections = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk.isdigit():
            continue
        num = int(chunk)
        if 1 <= num <= len(entries):
            selections.add(num - 1)
    return list(selections)


def setReminder(raw_text: str) -> dict:
    text = raw_text.strip()
    remindersDict = {}
    pattern_set = re.compile(
        r"^(?:remind\s+)?-set\s+(?P<date>today|tomorrow|\d{1,2}/\d{1,2}|\d{1,2}\s+\d{1,2})\s+at\s+(?P<hour>\d{1,2})(?:\s+|:)(?P<minute>\d{1,2})(?:\s+as)?\s+(?P<message>.+)$",
        re.IGNORECASE,
    )
    set_match = pattern_set.match(text)
    if not set_match:
        raise ValueError(
            "Invalid command format. Use '-set <date> at <hour> <minute> as <message>'."
        )
    existing_data = load_reminders()
    reminder_id = get_next_id(existing_data)

    raw_date = set_match.group("date").strip()
    reminder_date = resolve_date(raw_date)
    date_label = reminder_date.strftime("%d/%m/%Y")

    remindersDict[set_match.group("message").strip()] = {
        "id": reminder_id,
        "date": date_label,
        "hour": int(set_match.group("hour")),
        "minute": int(set_match.group("minute")),
        "message": set_match.group("message").strip(),
    }
    existing_data["reminders"].append(remindersDict)
    save_reminders(existing_data)
    return remindersDict


def listReminders(raw_text: str):
    pattern_list = re.compile(r"^(?:remind\s+)?-list\s*$", re.IGNORECASE)
    match = pattern_list.match(raw_text.strip())
    if not match:
        raise ValueError("Invalid command format. Please use 'list'.")
    data = load_reminders()
    entries = get_reminder_entries(data)
    if not entries:
        print("No reminders found.")
        return
    print("Your Reminders:")
    for entry in entries:
        details = entry["details"]
        date_str = details.get("date", "Unknown date")
        hour = details.get("hour", 0)
        minute = details.get("minute", 0)
        print(f"- {entry['message']} at {date_str} {int(hour):02d}:{int(minute):02d}")


def deleteReminder():
    data = load_reminders()
    entries = get_reminder_entries(data)
    if not entries:
        print("No reminders found.")
        return

    selections = select_reminders_with_curses(entries)
    if selections is None:
        selections = select_reminders_fallback(entries)
    if selections is None:
        print("Delete canceled.")
        return
    if not selections:
        print("No reminders selected.")
        return

    indices_to_remove = sorted(
        (entries[i]["index"] for i in selections), reverse=True
    )
    for index in indices_to_remove:
        if 0 <= index < len(data["reminders"]):
            del data["reminders"][index]

    save_reminders(data)
    print(f"Deleted {len(indices_to_remove)} reminder(s).")


def print_help() -> None:
    # print_banner()
    print("command line reminder tool by github/AniketWathore")
    print("")
    print("Usage:")
    print("  remindme -set <date> at <hour> <minute> as <message>")
    print("  remindme -list")
    print("  remindme -delete")
    print("")
    print("Date formats:")
    print("  today | tomorrow | DD/MM | DD MM")
    print("Time formats:")
    print("  HH MM or HH:MM")
    print("")
    print("For example:")
    print("  remindme -set today at 9 30 as 'Meeting with team'")


def print_banner() -> None:
    banner = r"""
  _____                _           _ __  __      
 |  __ \              (_)         | |  \/  |     
 | |__) |___ _ __ ___  _ _ __   __| | \  / | ___ 
 |  _  // _ \ '_ ` _ \| | '_ \ / _` | |\/| |/ _ \
 | | \ \  __/ | | | | | | | | | (_| | |  | |  __/
 |_|  \_\___|_| |_| |_|_|_| |_|\__,_|_|  |_|\___|
"""
    print(banner)


def run_cli(argv: list) -> None:
    start_background_daemon()
    install_autostart()
    print_banner()
    if len(argv) <= 1 or argv[1] in ("-h", "--help", "help"):
        print_help()
        return

    command = argv[1].lower()
    if command == "-set":
        if len(argv) <= 2:
            print("Missing reminder details.")
            print_help()
            return
        raw_text = "-set " + " ".join(argv[2:])
        try:
            remindersDict = setReminder(raw_text)
            for message, details in remindersDict.items():
                date_str = details["date"]
                hour = details["hour"]
                minute = details["minute"]
                print(  
                    f"Setting reminder for {date_str} at {hour:02d}:{minute:02d} with message: '{message}'"
                )
        except ValueError as exc:
            print(exc)
        return

    if command == "-list":
        listReminders(command)
        return
    if command == "-delete":
        deleteReminder()
        return
    print("Unknown command.")
    print_help()


def main() -> None:
    if "--daemon" in sys.argv:
        run_scheduler()
    else:
        run_cli(sys.argv)


if __name__ == "__main__":
    main()
