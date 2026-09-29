# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FreePBX allowlist management system with two components that work together to control which callers can reach a PBX extension:

1. **`agi/allow_ivr.agi`** — An Asterisk AGI script called by FreePBX's Dynamic Route module after DTMF code validation. It adds the caller's number to the AstDB allowlist and sends a Telegram notification, then returns `SUCCESS`/`ERROR` to the dialplan.

2. **`telegram-bot/allowlist_bot.py`** — A Telegram bot (python-telegram-bot v20+) for human operators to manage the allowlist and FreePBX Contact Manager speed dials remotely. It talks to both AstDB (via `asterisk -rx` shell commands) and the FreePBX MySQL database.

## Runtime Environment

Both scripts run on the FreePBX server itself. The AGI script uses the shebang `/var/lib/asterisk/venv/bin/python3`, meaning they expect a virtualenv at that path with `python-telegram-bot` and `pymysql` installed.

## Configuration

All secrets are injected via environment variables — never hardcoded:
- `TELEGRAM_TOKEN` — bot token for both the AGI notifier and the bot
- `TELEGRAM_CHAT_ID` / `ALLOWED_CHAT_ID` — restricts bot access to a single chat ID
- `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` — MySQL connection for the bot (defaults: `localhost`, `freepbxuser`, `asterisk`)

## Data Architecture

The allowlist has two storage layers that must stay in sync:

- **AstDB** (`allowlist/<E164_number>` → label) — checked in real-time by Asterisk dialplan. Managed via `asterisk -rx "database put/del/show allowlist ..."`. Also `allowlist-settings/paused` controls global bypass.
- **FreePBX Contact Manager** (MySQL tables: `contactmanager_group_entries`, `contactmanager_entry_numbers`, `contactmanager_entry_speeddials`) — used only for speed dials. Speed dials are also mirrored to AstDB under `CM/speeddial/<id>`.

Number normalization: `normalize()` ensures all numbers are stored as E164 without `+` (e.g., `5511999990001`). `strip_country()` removes the `55` prefix for Contact Manager storage.

## Speed Dial Convention

Speed dials use IDs `01`–`99` (zero-padded), exposed on phones as `*10XX`. The `SPEEDDIAL_GROUP = 2` constant is the `contactmanager_groups.id` for the "Speed Dials" group — verify this value matches the target FreePBX instance.

## Project Layout

```
freepbx-allowlist-system/
├── agi/allow_ivr.agi       # standalone AGI script (deployed to /var/lib/asterisk/agi-bin/)
├── bot/
│   ├── config.py           # env vars + constants
│   ├── asterisk.py         # AstDB helpers (normalize, db_add/remove/list, is_paused)
│   ├── speeddials.py       # MySQL Contact Manager helpers (sd_add/remove/link/list)
│   ├── handlers.py         # all Telegram command + callback handlers
│   └── __main__.py         # entry point (ApplicationBuilder, run_polling)
├── pyproject.toml
└── .env.example
```

## Setup

```bash
pip install -e .
cp .env.example .env  # fill in real values
```

## Running the Bot

```bash
python -m bot
```

Or via the installed script: `allowlist-bot`

The bot uses `run_polling()` (long-polling). For production it should run as a systemd service.

## Deploying the AGI Script

Copy `agi/allow_ivr.agi` to `/var/lib/asterisk/agi-bin/` on the FreePBX server and make it executable. Point the FreePBX Dynamic Route to call it after DTMF validation. The script reads `agi_callerid` from the AGI environment and sets `DYNAMIC_ROUTE_RESULT` to `SUCCESS` or `ERROR`.
