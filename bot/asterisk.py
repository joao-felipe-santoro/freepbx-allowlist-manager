import subprocess
from .config import ASTERISK_BIN, DB_FAMILY


def asterisk_cmd(cmd: str) -> str:
    try:
        result = subprocess.run(
            [ASTERISK_BIN, "-rx", cmd],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Erro: {e}"


def normalize(number: str) -> str:
    n = number.replace("+", "").replace("-", "").replace(" ", "")
    if n.startswith("55") and len(n) >= 12:
        return n
    if len(n) in (10, 11):
        return f"55{n}"
    return n


def strip_country(number: str) -> str:
    """Remove 55 country code prefix for Contact Manager storage."""
    n = normalize(number)
    if n.startswith("55"):
        return n[2:]
    return n


def db_list() -> list:
    output = asterisk_cmd(f"database show {DB_FAMILY}")
    entries = []
    for line in output.splitlines():
        if f"/{DB_FAMILY}/" in line.lower() and "dest" not in line and "did" not in line and "settings" not in line:
            parts = line.strip().split(":")
            if len(parts) == 2:
                key = parts[0].strip().split("/")[-1]
                value = parts[1].strip()
                entries.append((key, value))
    return entries


def db_add(number: str, label: str) -> bool:
    n = normalize(number)
    out = asterisk_cmd(f"database put {DB_FAMILY} {n} {label or '1'}")
    return "error" not in out.lower()


def db_remove(number: str) -> bool:
    n = normalize(number)
    out = asterisk_cmd(f"database del {DB_FAMILY} {n}")
    return "error" not in out.lower()


def is_paused() -> bool:
    out = asterisk_cmd("database get allowlist-settings paused")
    return "1" in out
