from unittest.mock import MagicMock, patch

import pytest

from bot.speeddials import sd_id_exists, sd_next_id, sd_remove


def make_mock_conn(fetchall_return=None, fetchone_return=None):
    """Return a mock pymysql connection whose cursor() works as a context manager."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = fetchall_return or []
    mock_cursor.fetchone.return_value = fetchone_return

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


class TestSdNextId:
    def test_returns_01_when_no_speed_dials(self):
        mock_conn, _ = make_mock_conn(fetchall_return=[])
        with patch("bot.speeddials.get_db", return_value=mock_conn):
            assert sd_next_id() == "01"

    def test_skips_existing_ids(self):
        mock_conn, _ = make_mock_conn(fetchall_return=[("01",), ("02",), ("03",)])
        with patch("bot.speeddials.get_db", return_value=mock_conn):
            assert sd_next_id() == "04"

    def test_zero_pads_single_digit(self):
        mock_conn, _ = make_mock_conn(fetchall_return=[])
        with patch("bot.speeddials.get_db", return_value=mock_conn):
            result = sd_next_id()
            assert len(result) == 2
            assert result == "01"

    def test_returns_none_when_all_slots_taken(self):
        all_ids = [(f"{i:02d}",) for i in range(1, 100)]
        mock_conn, _ = make_mock_conn(fetchall_return=all_ids)
        with patch("bot.speeddials.get_db", return_value=mock_conn):
            assert sd_next_id() is None


class TestSdIdExists:
    def test_returns_true_when_found(self):
        mock_conn, _ = make_mock_conn(fetchone_return=("05",))
        with patch("bot.speeddials.get_db", return_value=mock_conn):
            assert sd_id_exists("05") is True

    def test_returns_false_when_not_found(self):
        mock_conn, _ = make_mock_conn(fetchone_return=None)
        with patch("bot.speeddials.get_db", return_value=mock_conn):
            assert sd_id_exists("05") is False


class TestSdRemove:
    def test_returns_true_on_success(self):
        mock_conn, _ = make_mock_conn()
        with patch("bot.speeddials.get_db", return_value=mock_conn), \
             patch("bot.speeddials.asterisk_cmd"):
            assert sd_remove("05") is True

    def test_syncs_astdb_on_removal(self):
        mock_conn, _ = make_mock_conn()
        with patch("bot.speeddials.get_db", return_value=mock_conn), \
             patch("bot.speeddials.asterisk_cmd") as mock_cmd:
            sd_remove("05")
            mock_cmd.assert_called_once_with("database del CM speeddial/05")

    def test_returns_false_on_db_error(self):
        mock_conn, mock_cursor = make_mock_conn()
        mock_cursor.execute.side_effect = Exception("DB error")
        with patch("bot.speeddials.get_db", return_value=mock_conn), \
             patch("bot.speeddials.asterisk_cmd"):
            assert sd_remove("05") is False

    def test_rolls_back_on_db_error(self):
        mock_conn, mock_cursor = make_mock_conn()
        mock_cursor.execute.side_effect = Exception("DB error")
        with patch("bot.speeddials.get_db", return_value=mock_conn), \
             patch("bot.speeddials.asterisk_cmd"):
            sd_remove("05")
            mock_conn.rollback.assert_called_once()
