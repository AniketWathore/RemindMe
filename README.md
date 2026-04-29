# RemindMe

RemindMe is a lightweight command line reminder tool that stores reminders locally
and sends desktop notifications when they are due.

## Features

- Simple CLI for creating, listing, and deleting reminders.
- Local JSON storage, no external services required.
- Desktop notifications on Linux, macOS, and Windows when supported.
- Optional background daemon and auto-start on Linux.

## Requirements

- Python 3.10+ recommended.
- On Linux, `notify-send` is used when available.

## Install

### pipx (recommended)

```sh
pipx install .
```

### pip

```sh
pip install .
```

## Usage

```sh
remindme --help
remindme -set today at 14 00 as drink coffee
remindme -set 29/04 at 09 30 as standup meeting
remindme -list
remindme -delete
```

## Command Reference

- `remindme -set <date> at <hour> <minute> as <message>`
- `remindme -list`
- `remindme -delete`

### Date formats

- `today`
- `tomorrow`
- `DD/MM`
- `DD MM`

### Time formats

- `HH MM`
- `HH:MM`

## Data Storage

Reminders are stored in a JSON file under your user data directory:

- Linux: `~/.local/share/remindme/reminders.json`
- macOS: `~/Library/Application Support/RemindMe/reminders.json`
- Windows: `%APPDATA%\RemindMe\reminders.json`

## Background Daemon

Running any command starts the scheduler in the background. On Linux, an
autostart entry is installed so reminders keep running after reboot. Use the
`remindme --daemon` flag to run the scheduler in the foreground.

## Development

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e .
remindme -h
```

## Troubleshooting

- If notifications do not show on Linux, ensure `notify-send` is installed.
- If the daemon does not run, remove the PID file at
	`~/.local/share/remindme/remindme.pid` and try again.

## License

MIT
