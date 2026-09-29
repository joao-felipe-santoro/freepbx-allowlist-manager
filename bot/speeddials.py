import logging
import pymysql
from .config import DB_CONFIG, SPEEDDIAL_GROUP
from .asterisk import asterisk_cmd, normalize, strip_country

logger = logging.getLogger(__name__)


def get_db():
    return pymysql.connect(**DB_CONFIG)


def sd_list() -> list:
    """Return list of (speeddial_id, displayname, number, E164)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ces.id, cge.displayname, cen.number, cen.E164
                FROM contactmanager_entry_speeddials ces
                JOIN contactmanager_group_entries cge ON ces.entryid = cge.id
                JOIN contactmanager_entry_numbers cen ON ces.numberid = cen.id
                ORDER BY ces.id
            """)
            return cur.fetchall()
    finally:
        conn.close()


def sd_next_id() -> str:
    """Return next available speed dial ID (zero-padded 2 digits)."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM contactmanager_entry_speeddials ORDER BY id")
            used = {row[0] for row in cur.fetchall()}
        for i in range(1, 100):
            candidate = f"{i:02d}"
            if candidate not in used:
                return candidate
        return None
    finally:
        conn.close()


def sd_id_exists(sd_id: str) -> bool:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM contactmanager_entry_speeddials WHERE id=%s", (sd_id,))
            return cur.fetchone() is not None
    finally:
        conn.close()


def sd_add(number: str, displayname: str, sd_id: str) -> bool:
    """
    Create a new Contact Manager entry with speed dial.
    Inserts into: group_entries, entry_numbers, entry_speeddials.
    Also syncs AstDB CM/speeddial/XX.
    """
    conn = get_db()
    try:
        n_stripped = strip_country(number)
        n_full     = normalize(number)
        e164       = f"+{n_full}"

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO contactmanager_group_entries
                  (groupid, user, displayname, fname, lname, title, company, address)
                VALUES (%s, -1, %s, '', '', '', '', '')
            """, (SPEEDDIAL_GROUP, displayname))
            entry_id = cur.lastrowid

            cur.execute("""
                INSERT INTO contactmanager_entry_numbers
                  (entryid, number, countrycode, nationalnumber, regioncode, locale, stripped, type, flags, E164, possibleshort)
                VALUES (%s, %s, '55', %s, 'BR', 'BR', %s, 'cell', '', %s, 0)
            """, (entry_id, n_stripped, n_stripped, n_full, e164))
            number_id = cur.lastrowid

            cur.execute("""
                INSERT INTO contactmanager_entry_speeddials (id, entryid, numberid)
                VALUES (%s, %s, %s)
            """, (sd_id, entry_id, number_id))

        conn.commit()
        asterisk_cmd(f"database put CM speeddial/{sd_id} {n_stripped}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"sd_add error: {e}")
        return False
    finally:
        conn.close()


def sd_link(number: str, sd_id: str) -> bool:
    """Link a speed dial ID to an existing contact that has no speed dial yet."""
    conn = get_db()
    try:
        n_full     = normalize(number)
        n_stripped = strip_country(number)

        with conn.cursor() as cur:
            cur.execute("""
                SELECT cen.id, cen.entryid
                FROM contactmanager_entry_numbers cen
                JOIN contactmanager_group_entries cge ON cen.entryid = cge.id
                WHERE cge.groupid = %s AND cen.stripped = %s
                LIMIT 1
            """, (SPEEDDIAL_GROUP, n_full))
            row = cur.fetchone()
            if not row:
                return False
            number_id, entry_id = row

            cur.execute("SELECT id FROM contactmanager_entry_speeddials WHERE numberid=%s", (number_id,))
            if cur.fetchone():
                return False  # already has a speed dial

            cur.execute("""
                INSERT INTO contactmanager_entry_speeddials (id, entryid, numberid)
                VALUES (%s, %s, %s)
            """, (sd_id, entry_id, number_id))

        conn.commit()
        asterisk_cmd(f"database put CM speeddial/{sd_id} {n_stripped}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"sd_link error: {e}")
        return False
    finally:
        conn.close()


def sd_remove(sd_id: str) -> bool:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contactmanager_entry_speeddials WHERE id=%s", (sd_id,))
        conn.commit()
        asterisk_cmd(f"database del CM speeddial/{sd_id}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"sd_remove error: {e}")
        return False
    finally:
        conn.close()
