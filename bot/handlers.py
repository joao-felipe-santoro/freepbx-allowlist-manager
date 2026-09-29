from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .config import ALLOWED_CHAT_ID
from .asterisk import db_list, db_add, db_remove, is_paused, asterisk_cmd, normalize
from .speeddials import sd_list, sd_next_id, sd_id_exists, sd_add, sd_link, sd_remove


def is_authorized(update: Update) -> bool:
    chat_id = (
        update.effective_chat.id
        if update.effective_chat
        else update.callback_query.message.chat.id
    )
    return chat_id == ALLOWED_CHAT_ID


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(
        "🔐 *Allowlist Manager v3*\n\n"
        "*Allowlist:*\n"
        "/list — listar e remover números\n"
        "/add \\+55119999 Nome — adicionar\n"
        "/remove \\+55119999 — remover\n"
        "/pause — pausar allowlist\n"
        "/resume — reativar allowlist\n"
        "/status — status atual\n\n"
        "*Speed Dials:*\n"
        "/sdlist — listar speed dials\n"
        "/sdadd \\+55119999 Nome XX — criar speed dial \\*10XX\n"
        "/sdlink \\+55119999 XX — vincular speed dial a contato existente",
        parse_mode="MarkdownV2"
    )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    entries = db_list()
    if not entries:
        await update.message.reply_text("📋 Allowlist vazia.")
        return
    keyboard = []
    lines = ["📋 *Números autorizados:*\n"]
    for number, label in sorted(entries, key=lambda x: x[1]):
        lines.append(f"• `+{number}` — {label}")
        keyboard.append([InlineKeyboardButton(
            text=f"🗑 {label} (+{number[-4:]})",
            callback_data=f"remove:{number}"
        )])
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Uso:\n"
            "`/add +5511999990001 Nome` — só allowlist\n"
            "`/add +5511999990001 Nome 05` — allowlist + speed dial \\*1005",
            parse_mode="Markdown"
        )
        return

    number = args[0]

    sd_id = None
    if len(args) >= 3 and args[-1].isdigit():
        sd_id = f"{int(args[-1]):02d}"
        label = " ".join(args[1:-1]) or "Sem nome"
    else:
        label = " ".join(args[1:]) if len(args) > 1 else "Sem nome"

    ok = db_add(number, label)
    if not ok:
        await update.message.reply_text("❌ Erro ao adicionar número na allowlist.")
        return

    msg = f"✅ `+{normalize(number)}` adicionado como *{label}*"

    if sd_id:
        if sd_id_exists(sd_id):
            msg += f"\n\n⚠️ Speed dial `*10{sd_id}` já existe — use /sdlist para ver os cadastrados."
        else:
            sd_ok = sd_add(number, label, sd_id)
            if sd_ok:
                msg += f"\n📞 Speed dial `*10{sd_id}` criado automaticamente."
            else:
                msg += f"\n⚠️ Allowlist OK, mas erro ao criar speed dial `*10{sd_id}`."
    else:
        next_id = sd_next_id()
        keyboard = [[
            InlineKeyboardButton(
                f"📞 Criar speed dial *10{next_id}",
                callback_data=f"sdprompt:{normalize(number)}:{label}:{next_id}"
            ),
            InlineKeyboardButton("❌ Não", callback_data="noop")
        ]]
        await update.message.reply_text(
            msg + "\n\nDeseja criar um speed dial para este contato?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = context.args
    if not args:
        await update.message.reply_text("❌ Uso: /remove +5511999990001")
        return
    ok = db_remove(args[0])
    if ok:
        await update.message.reply_text(f"🗑️ `+{normalize(args[0])}` removido.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Erro ao remover número.")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    asterisk_cmd("database put allowlist-settings paused 1")
    await update.message.reply_text("⏸️ Allowlist *pausada*.", parse_mode="Markdown")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    asterisk_cmd("database put allowlist-settings paused 0")
    await update.message.reply_text("▶️ Allowlist *reativada*.", parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    entries = db_list()
    paused = is_paused()
    status = "⏸️ PAUSADA" if paused else "✅ ATIVA"
    await update.message.reply_text(
        f"*Status da Allowlist*\n\nEstado: {status}\nNúmeros autorizados: {len(entries)}",
        parse_mode="Markdown"
    )


async def cmd_sdlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    entries = sd_list()
    if not entries:
        await update.message.reply_text("📋 Nenhum speed dial cadastrado.")
        return
    keyboard = []
    lines = ["📞 *Speed Dials:*\n"]
    for sd_id, name, number, e164 in entries:
        lines.append(f"• `*10{sd_id}` — {name} (`{e164 or number}`)")
        keyboard.append([InlineKeyboardButton(
            text=f"🗑 *10{sd_id} {name}",
            callback_data=f"sdremove:{sd_id}"
        )])
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def cmd_sdadd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("❌ Uso: /sdadd +5511999990001 Nome XX\nExemplo: /sdadd +5511999990001 João 05")
        return
    number = args[0]
    sd_id  = f"{int(args[-1]):02d}"
    name   = " ".join(args[1:-1])

    if sd_id_exists(sd_id):
        await update.message.reply_text(f"❌ Speed dial `*10{sd_id}` já existe! Use /sdlist para ver os cadastrados.", parse_mode="Markdown")
        return

    ok = sd_add(number, name, sd_id)
    if ok:
        await update.message.reply_text(
            f"✅ Speed dial `*10{sd_id}` criado para *{name}* (`+{normalize(number)}`)",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Erro ao criar speed dial.")


async def cmd_sdlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ Uso: /sdlink +5511999990001 XX\nExemplo: /sdlink +5511999990001 05")
        return
    number = args[0]
    sd_id  = f"{int(args[1]):02d}"

    if sd_id_exists(sd_id):
        await update.message.reply_text(f"❌ Speed dial `*10{sd_id}` já existe!", parse_mode="Markdown")
        return

    ok = sd_link(number, sd_id)
    if ok:
        await update.message.reply_text(
            f"✅ Speed dial `*10{sd_id}` vinculado a `+{normalize(number)}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Contato não encontrado ou já tem speed dial.")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.message.chat.id != ALLOWED_CHAT_ID:
        return

    data = query.data

    if data == "noop":
        await query.edit_message_reply_markup(reply_markup=None)
        return

    if data.startswith("remove:"):
        number = data.split(":", 1)[1]
        ok = db_remove(number)
        if ok:
            entries = db_list()
            if not entries:
                await query.edit_message_text("📋 Allowlist vazia.")
                return
            keyboard = []
            lines = ["📋 *Números autorizados:*\n"]
            for n, label in sorted(entries, key=lambda x: x[1]):
                lines.append(f"• `+{n}` — {label}")
                keyboard.append([InlineKeyboardButton(
                    text=f"🗑 {label} (+{n[-4:]})",
                    callback_data=f"remove:{n}"
                )])
            await query.edit_message_text(
                "\n".join(lines) + f"\n\n✅ `+{number}` removido.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data.startswith("sdprompt:"):
        parts = data.split(":")
        number  = parts[1]
        name    = parts[2]
        next_id = parts[3] if len(parts) > 3 else sd_next_id()

        sd_ok = sd_add(number, name, next_id)
        if sd_ok:
            await query.edit_message_text(
                f"✅ `+{number}` adicionado como *{name}*\n"
                f"📞 Speed dial `*10{next_id}` criado automaticamente.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"✅ `+{number}` adicionado como *{name}*\n"
                f"⚠️ Erro ao criar speed dial `*10{next_id}`.",
                parse_mode="Markdown"
            )

    elif data.startswith("sdremove:"):
        sd_id = data.split(":", 1)[1]
        ok = sd_remove(sd_id)
        if ok:
            entries = sd_list()
            if not entries:
                await query.edit_message_text("📋 Nenhum speed dial cadastrado.")
                return
            keyboard = []
            lines = ["📞 *Speed Dials:*\n"]
            for sid, name, number, e164 in entries:
                lines.append(f"• `*10{sid}` — {name} (`{e164 or number}`)")
                keyboard.append([InlineKeyboardButton(
                    text=f"🗑 *10{sid} {name}",
                    callback_data=f"sdremove:{sid}"
                )])
            await query.edit_message_text(
                "\n".join(lines) + f"\n\n✅ Speed dial `*10{sd_id}` removido.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
