import cmd
import datetime as dt
import re

today = dt.date.today()
tomorrow = today + dt.timedelta(days=1)

def setReminder(raw_text: str):
    text = raw_text.strip()
    pattern_set = re.compile(
        r"^(?:remind\s+)?-set\s+(?P<date>\S+)\s+at\s+(?P<hour>\d{1,2})\s+(?P<minute>\d{1,2})\s+as\s+(?P<message>.+)$",
        re.IGNORECASE
    )
    set_match = pattern_set.match(text)
    if not set_match:
        raise ValueError("Invalid command format. Please use '-set <date> at <hour>:<minute> as <message>'.")
    return set_match

def listReminders(raw_text: str):
    pattern_list = re.compile(r"^(?:remind\s+)?list\s*$", re.IGNORECASE)
    match = pattern_list.match(raw_text.strip())
    setReminder(raw_text)
    if not match:
        raise ValueError("Invalid command format. Please use 'list'.")
    print("Listing all reminders...")


def deleteReminder():
    print("Deleting a reminder...")

def mainScreen():
    print('REMINDME!')
    
    print("\n REMINDER COMMANDS:")
    print("1. -set <date> at <hour>:<minute> as <message> - Set a reminder"
          "\n   Example: -set tomorrow at 14:30 as Meeting with team"
          "\n2. list - List all reminders"
          "\n3. delete - Delete a reminder"
          "\n4. exit - Exit the application")

    cmd = input()
    if cmd.startswith("-set"):
        try:
            match = setReminder(cmd)
            date_str = match.group("date")
            hour = int(match.group("hour"))
            minute = int(match.group("minute"))
            message = match.group("message")

            if date_str.lower() == "today":
                reminder_date = today
            elif date_str.lower() == "tomorrow":
                reminder_date = tomorrow
            else:
                raise ValueError("Invalid date. Please use 'today' or 'tomorrow'.")

            print(f"Setting reminder for {reminder_date} at {hour:02d}:{minute:02d} with message: '{message}'")
        except ValueError as e:
            print(e)
    elif cmd.lower() == "list":
        listReminders(cmd)
    elif cmd.lower() == "delete":
        deleteReminder()
    elif cmd.lower() == "exit":
        print("Exiting the application...")
    else:
        print("Unknown command. Please try again.")

if __name__ == "__main__":
    mainScreen()