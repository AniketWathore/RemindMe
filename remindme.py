import cmd
import datetime as dt
import re

today = dt.date.today()
tomorrow = today + dt.timedelta(days=1)


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

    remindersDict[set_match.group("message").strip()] = {
        "date": set_match.group("date").strip(),
        "hour": int(set_match.group("hour")),
        "minute": int(set_match.group("minute")),
    }
    return remindersDict

def listReminders(raw_text: str):
    pattern_list = re.compile(r"^(?:remind\s+)?-list\s*$", re.IGNORECASE)
    match = pattern_list.match(raw_text.strip())
    if not match:
        raise ValueError("Invalid command format. Please use 'list'.")
    print("Listing all reminders...")

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

            if date_str.lower() == "today":
                reminder_date = today
            elif date_str.lower() == "tomorrow":
                reminder_date = tomorrow
            else:
                if "/" in date_str:
                    day_str, month_str = date_str.split("/", 1)
                else:
                    day_str, month_str = date_str.split()
                reminder_date = dt.date(today.year, int(month_str), int(day_str))

            print(f"Setting reminder for {reminder_date} at {hour:02d}:{minute:02d} with message: '{message}'")
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