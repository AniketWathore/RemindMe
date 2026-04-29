import datetime as dt
import re
import json


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
    with open("reminders.json", "w") as file_handle:
        json.dump(existing_data, file_handle, indent=4)
    return remindersDict

def listReminders(raw_text: str):
    pattern_list = re.compile(r"^(?:remind\s+)?-list\s*$", re.IGNORECASE)
    match = pattern_list.match(raw_text.strip())
    if not match:
        raise ValueError("Invalid command format. Please use 'list'.")
    with open("reminders.json", "r") as file_handle:
        data = json.load(file_handle)
    reminders = data.get("reminders", [])
    if not reminders:
        print("No reminders found.")
        return
    print("Your Reminders:")
    for reminder in reminders:
        if not isinstance(reminder, dict):
            continue
        for message, details in reminder.items():
            date_str = details.get("date", "Unknown date")
            hour = details.get("hour", "Unknown hour")
            minute = details.get("minute", "Unknown minute")
            print(f"- {message} at {date_str} {hour:02d}:{minute:02d}")

def deleteReminder():
    print("Deleting a reminder...")

def mainScreen():
    print('REMINDME!')
    
    print("\n REMINDER COMMANDS:")
    print("1. -set <date> at <hour> <minute> as <message> - Set a reminder")
    print("   Date: today | tomorrow | DD/MM | DD MM")
    print("   Time: HH MM or HH:MM")

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
    elif cmd.lower() == "-exit":
        print("Exiting the application...")
    else:
        print("Unknown command. Please try again.")

if __name__ == "__main__":
    mainScreen()