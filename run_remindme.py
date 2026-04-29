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
    """Compatibility wrapper for the installed CLI."""

    from remindme.cli import main


    if __name__ == "__main__":
        main()