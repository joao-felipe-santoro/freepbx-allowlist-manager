from unittest.mock import patch

import pytest

from bot.asterisk import db_add, db_list, db_remove, is_paused, normalize, strip_country


class TestNormalize:
    def test_strips_plus(self):
        assert normalize("+5511999990001") == "5511999990001"

    def test_already_normalized(self):
        assert normalize("5511999990001") == "5511999990001"

    def test_11_digit_adds_country_code(self):
        assert normalize("11999990001") == "5511999990001"

    def test_10_digit_adds_country_code(self):
        assert normalize("1199999000") == "551199999000"

    def test_strips_hyphens_and_spaces(self):
        assert normalize("+55 11 99999-0001") == "5511999990001"


class TestStripCountry:
    def test_removes_55_prefix(self):
        assert strip_country("5511999990001") == "11999990001"

    def test_with_plus_prefix(self):
        assert strip_country("+5511999990001") == "11999990001"

    def test_11_digit_input_round_trips(self):
        # normalize adds 55, then strip_country removes it
        assert strip_country("11999990001") == "11999990001"


class TestDbList:
    def test_empty_output(self):
        with patch("bot.asterisk.asterisk_cmd", return_value=""):
            assert db_list() == []

    def test_parses_single_entry(self):
        output = "/allowlist/5511999990001                     : João"
        with patch("bot.asterisk.asterisk_cmd", return_value=output):
            assert db_list() == [("5511999990001", "João")]

    def test_parses_multiple_entries(self):
        output = (
            "/allowlist/5511111110001                     : Alice\n"
            "/allowlist/5511222220002                     : Bob"
        )
        with patch("bot.asterisk.asterisk_cmd", return_value=output):
            result = db_list()
            assert ("5511111110001", "Alice") in result
            assert ("5511222220002", "Bob") in result

    def test_skips_settings_family(self):
        output = (
            "/allowlist/5511999990001                     : João\n"
            "/allowlist-settings/paused                   : 0"
        )
        with patch("bot.asterisk.asterisk_cmd", return_value=output):
            assert db_list() == [("5511999990001", "João")]

    @pytest.mark.parametrize("keyword", ["dest", "did", "settings"])
    def test_skips_lines_with_reserved_keywords(self, keyword):
        output = f"/allowlist/{keyword}5511999990001              : 1"
        with patch("bot.asterisk.asterisk_cmd", return_value=output):
            assert db_list() == []


class TestDbAdd:
    def test_returns_true_on_success(self):
        with patch("bot.asterisk.asterisk_cmd", return_value="Updated database successfully"):
            assert db_add("+5511999990001", "João") is True

    def test_returns_false_on_error(self):
        with patch("bot.asterisk.asterisk_cmd", return_value="error: something went wrong"):
            assert db_add("+5511999990001", "João") is False

    def test_normalizes_number_before_storing(self):
        with patch("bot.asterisk.asterisk_cmd", return_value="Updated database successfully") as mock_cmd:
            db_add("+55 11 99999-0001", "João")  # mobile: 9-digit local number
            called_cmd = mock_cmd.call_args[0][0]
            assert "5511999990001" in called_cmd
            assert "+" not in called_cmd


class TestDbRemove:
    def test_returns_true_on_success(self):
        with patch("bot.asterisk.asterisk_cmd", return_value="Deleted database key"):
            assert db_remove("+5511999990001") is True

    def test_returns_false_on_error(self):
        with patch("bot.asterisk.asterisk_cmd", return_value="error: key not found"):
            assert db_remove("+5511999990001") is False


class TestIsPaused:
    def test_paused_when_value_is_1(self):
        with patch("bot.asterisk.asterisk_cmd", return_value="Value: 1"):
            assert is_paused() is True

    def test_not_paused_when_value_is_0(self):
        with patch("bot.asterisk.asterisk_cmd", return_value="Value: 0"):
            assert is_paused() is False

    def test_not_paused_when_key_missing(self):
        with patch("bot.asterisk.asterisk_cmd", return_value="Database entry not found"):
            assert is_paused() is False
