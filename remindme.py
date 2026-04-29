import datetime as dt
import re
import json
import curses
import os
import shutil
import subprocess
import sys
import time


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


def load_reminders() -> dict:
    try:
        with open("reminders.json", "r") as file_handle:
            data = json.load(file_handle)
    except FileNotFoundError:
        data = {"reminders": []}
    except json.JSONDecodeError:
        data = {"reminders": []}
    if "reminders" not in data or not isinstance(data["reminders"], list):
        data["reminders"] = []
    return data


def save_reminders(data: dict) -> None:
    with open("reminders.json", "w") as file_handle:
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
    if shutil.which("notify-send") is None:
        return False
    subprocess.run(["notify-send", title, message], check=False)
    return True


def open_terminal_message(title: str, message: str) -> bool:
    terminals = [
        ("x-terminal-emulator", ["x-terminal-emulator", "-e"]),
        ("gnome-terminal", ["gnome-terminal", "--"]),
        ("konsole", ["konsole", "-e"]),
        ("xterm", ["xterm", "-e"]),
    ]
    for binary, prefix in terminals:
        if shutil.which(binary):
            cmd = prefix + ["bash", "-lc", f"echo '{title}: {message}'; read -r -p 'Press Enter to close'" ]
            subprocess.Popen(cmd)
            return True
    return False


def run_scheduler(poll_seconds: int = 30) -> None:
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
    script_path = os.path.abspath(__file__)
    args = [sys.executable, script_path, "--daemon"]
    subprocess.Popen(
        args,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def install_autostart() -> None:
    autostart_dir = os.path.expanduser("~/.config/autostart")
    os.makedirs(autostart_dir, exist_ok=True)
    desktop_path = os.path.join(autostart_dir, "remindme.desktop")
    script_path = os.path.abspath(__file__)
    exec_cmd = f"{sys.executable} {script_path} --daemon"

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
    print(f"Autostart entry written to {desktop_path}")


def remove_autostart() -> None:
    desktop_path = os.path.expanduser("~/.config/autostart/remindme.desktop")
    if os.path.exists(desktop_path):
        os.remove(desktop_path)
        print("Autostart entry removed.")
    else:
        print("Autostart entry not found.")


def select_reminders_with_curses(entries: list) -> list | None:
    if not entries:
        return []

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

def mainScreen():
    print('REMINDME!')
    
    print("\n REMINDER COMMANDS:")
    print("1. -set <date> at <hour> <minute> as <message> - Set a reminder")
    print("   Date: today | tomorrow | DD/MM | DD MM")
    print("   Time: HH MM or HH:MM")
    print("2. -list - List all reminders")
    print("3. -delete - Delete reminders")
    print("4. -install-autostart - Run reminders on login")
    print("5. -remove-autostart - Disable autostart")
    print("6. -daemon - Run scheduler in background now")
    print("7. -exit - Exit the application")

    cmd = input()
    if cmd.startswith("-set"):
        try:
            remindersDict = setReminder(cmd)
            for message, details in remindersDict.items():
                date_str = details["date"]
                hour = details["hour"]
                minute = details["minute"]

                print(
                    f"Setting reminder for {date_str} at {hour:02d}:{minute:02d} with message: '{message}'"
                )
        except ValueError as e:
            print(e)
    elif cmd.lower() == "-list":
        listReminders(cmd)
    elif cmd.lower() == "-delete":
        deleteReminder()
    elif cmd.lower() == "-install-autostart":
        install_autostart()
    elif cmd.lower() == "-remove-autostart":
        remove_autostart()
    elif cmd.lower() in ("-daemon", "daemon"):
        start_background_daemon()
        print("Scheduler started in background.")
    elif cmd.lower() == "-exit":
        print("Exiting the application...")
    else:
        print("Unknown command. Please try again.")


def print_help() -> None:
    print("RemindMe - command line reminder tool")
    print("")
    print("Usage:")
    print("  remindme -set <date> at <hour> <minute> as <message>")
    print("  remindme -list")
    print("  remindme -delete")
    print("  remindme -daemon")
    print("  remindme -install-autostart")
    print("  remindme -remove-autostart")
    print("")
    print("Date formats:")
    print("  today | tomorrow | DD/MM | DD MM")
    print("Time formats:")
    print("  HH MM or HH:MM")


def run_cli(argv: list) -> None:
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
    if command in ("-daemon", "daemon"):
        start_background_daemon()
        print("Scheduler started in background.")
        return
    if command == "-install-autostart":
        install_autostart()
        return
    if command == "-remove-autostart":
        remove_autostart()
        return

    print("Unknown command.")
    print_help()

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_scheduler()
    else:
        run_cli(sys.argv)