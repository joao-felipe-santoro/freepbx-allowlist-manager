import os

TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_TOKEN")
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0"))
ASTERISK_BIN    = "/usr/sbin/asterisk"
DB_FAMILY       = "allowlist"
SPEEDDIAL_GROUP = 2  # contactmanager_groups.id — verify per FreePBX instance

DB_CONFIG = {
    "host":    os.environ.get("DB_HOST", "localhost"),
    "user":    os.environ.get("DB_USER", "freepbxuser"),
    "passwd":  os.environ.get("DB_PASS"),
    "db":      os.environ.get("DB_NAME", "asterisk"),
    "charset": "utf8mb4",
}
