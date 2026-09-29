from unittest.mock import MagicMock, patch

from bot.handlers import is_authorized

AUTHORIZED_ID = 12345


def make_update(chat_id: int) -> MagicMock:
    update = MagicMock()
    update.effective_chat.id = chat_id
    return update


class TestIsAuthorized:
    def test_matching_chat_id_is_authorized(self):
        update = make_update(AUTHORIZED_ID)
        with patch("bot.handlers.ALLOWED_CHAT_ID", AUTHORIZED_ID):
            assert is_authorized(update) is True

    def test_different_chat_id_is_rejected(self):
        update = make_update(99999)
        with patch("bot.handlers.ALLOWED_CHAT_ID", AUTHORIZED_ID):
            assert is_authorized(update) is False

    def test_falls_back_to_callback_query_chat_when_no_effective_chat(self):
        update = MagicMock()
        update.effective_chat = None
        update.callback_query.message.chat.id = AUTHORIZED_ID
        with patch("bot.handlers.ALLOWED_CHAT_ID", AUTHORIZED_ID):
            assert is_authorized(update) is True
