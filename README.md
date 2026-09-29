# FreePBX Allowlist System

Manages a caller allowlist for FreePBX via an IVR self-service flow and a Telegram bot.

## How it works

```
Incoming call
    └─► FreePBX Dynamic Route (validates DTMF code)
            └─► agi/allow_ivr.agi  ──► adds caller to AstDB allowlist
                                   └─► sends Telegram notification

Operator (Telegram)
    └─► telegram-bot  ──► list / add / remove numbers in allowlist
                      └─► manage Contact Manager speed dials (MySQL)
```

**`agi/allow_ivr.agi`** — called by Asterisk after DTMF validation. Adds the caller's number to AstDB and notifies via Telegram, then sets `DYNAMIC_ROUTE_RESULT=SUCCESS` so FreePBX forwards the call.

**`bot/`** — Telegram bot for operators. Manages the same AstDB allowlist and FreePBX Contact Manager speed dials (stored in MySQL).

## Setup

**Prerequisites:** Python 3.9+, a running FreePBX instance.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in real values
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `TELEGRAM_TOKEN` | Bot token from @BotFather | required |
| `ALLOWED_CHAT_ID` | Chat ID that can control the bot | required |
| `DB_HOST` | MySQL host | `localhost` |
| `DB_USER` | MySQL user | `freepbxuser` |
| `DB_PASS` | MySQL password | required |
| `DB_NAME` | MySQL database | `asterisk` |

The AGI script also reads `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` from its environment (set these in the Asterisk service unit or `/etc/asterisk/asterisk.conf`).

## Running the bot

```bash
python -m bot
```

### Install as a systemd service

The service unit in `deploy/allowlist-bot.service` installs the bot under `/opt/freepbx-allowlist-system` and runs it as the `asterisk` user (required for `asterisk -rx` access).

```bash
# 1. Copy the project to the server
sudo cp -r . /opt/freepbx-allowlist-system
sudo chown -R asterisk:asterisk /opt/freepbx-allowlist-system

# 2. Create the virtualenv and install dependencies
sudo -u asterisk python3 -m venv /opt/freepbx-allowlist-system/.venv
sudo -u asterisk /opt/freepbx-allowlist-system/.venv/bin/pip install -e /opt/freepbx-allowlist-system

# 3. Create the env file (never commit this)
sudo cp /opt/freepbx-allowlist-system/.env.example /opt/freepbx-allowlist-system/.env
sudo chmod 600 /opt/freepbx-allowlist-system/.env
sudo nano /opt/freepbx-allowlist-system/.env   # fill in real values

# 4. Install and start the service
sudo cp /opt/freepbx-allowlist-system/deploy/allowlist-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now allowlist-bot
```

Check status and logs:

```bash
sudo systemctl status allowlist-bot
sudo journalctl -u allowlist-bot -f
```

## Deploying the AGI script

```bash
cp agi/allow_ivr.agi /var/lib/asterisk/agi-bin/
chmod +x /var/lib/asterisk/agi-bin/allow_ivr.agi
```

In FreePBX, configure a Dynamic Route to call `allow_ivr.agi` after DTMF validation and branch on `DYNAMIC_ROUTE_RESULT == SUCCESS`.

## Bot commands

| Command | Description |
|---|---|
| `/list` | List allowlisted numbers with inline remove buttons |
| `/add +5511999990001 Nome [XX]` | Add to allowlist; optionally create speed dial `*10XX` |
| `/remove +5511999990001` | Remove from allowlist |
| `/pause` / `/resume` | Temporarily disable / re-enable the allowlist check |
| `/status` | Show allowlist state and count |
| `/sdlist` | List speed dials with inline remove buttons |
| `/sdadd +5511999990001 Nome XX` | Create speed dial `*10XX` |
| `/sdlink +5511999990001 XX` | Link `*10XX` to an existing contact |

## Tests

```bash
pytest tests/ -v
```
