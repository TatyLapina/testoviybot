import os
import asyncio
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, WebAppInfo, constants
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, Defaults, ConversationHandler, MessageHandler, filters
)
from telegram.error import Forbidden

# ==== Настройка окружения ====
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
DB_URL = os.getenv("DATABASE_URL")

if DB_URL and "sslmode=" not in DB_URL:
    DB_URL += ("&sslmode=require" if "?" in DB_URL else "?sslmode=require")

# ==== Админ ID ====
ADMIN_ID = 759967778 # замени на свой Telegram ID

# ==== Состояния ====
BROADCAST_WAITING = 1

# ==== Работа с БД (psycopg3) ====
def get_conn():
    return psycopg.connect(DB_URL, row_factory=dict_row)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT,
                    subscribed BOOLEAN DEFAULT TRUE
                );
            """)
        conn.commit()
    print("✅ Таблица users готова")

def save_user(user):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (chat_id, username, first_name, last_name, language_code)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (chat_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    language_code = EXCLUDED.language_code,
                    subscribed = TRUE;
            """, (user.id, user.username, user.first_name, user.last_name, user.language_code))
        conn.commit()

def get_all_users():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT chat_id FROM users WHERE subscribed = TRUE;")
            rows = cur.fetchall()
            return [row["chat_id"] for row in rows]

# ==== Главное меню ====
async def send_main_menu(query):
    greeting = (
        f"Привет, {query.from_user.first_name} 🥰\n\n"
        "<b>На связи основатели студии NEYROPH и создатели Фаины Раевской — того самого AI-блогера №1 в России...</b>\n\n"
        "Мы создаем ролики, от которых вы смеётесь, узнаёте себя, собирая большие охваты и внимание к бренду 🎮\n\n"
        "Ниже варианты взаимодействия с нашей командой.\n"
        "Нажимай на кнопку, чтобы узнать подробнее ⬇️"
    )
    keyboard = [
        [InlineKeyboardButton("🎓 Обучение", callback_data="learn")],
        [InlineKeyboardButton("🎥 Заказать видео", callback_data="video")],
        [InlineKeyboardButton("🎭 Заказать персонажа", callback_data="character")],
        [InlineKeyboardButton("🤝 Сотрудничество / реклама", callback_data="promo")],
        [InlineKeyboardButton("📺 Канал студии", url="https://t.me/neyroph")]
    ]

    if query.from_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("📢 Сделать рассылку", callback_data="broadcast_start")])

    await query.message.reply_text(greeting, reply_markup=InlineKeyboardMarkup(keyboard))

# ==== /start ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    keyboard = [
        [InlineKeyboardButton("✅ Согласен", callback_data="agree")],
        [InlineKeyboardButton("❌ Не согласен", callback_data="disagree")]
    ]
    text = (
        "Привет! Прежде чем мы начнём...\n\n"
        "⚠️ Мы заботимся о твоей конфиденциальности.\n\n"
        "Нажимая кнопку «Согласен», ты подтверждаешь, что ознакомлен(-а) с "
        "[Политикой обработки персональных данных](https://docs.google.com/document/d/1XHFjqbDKYhX5am-Ni2uQOO_FaoQhOcLcq7-UiZyQNlE/edit?usp=drive_link) "
        "и даёшь согласие на обработку персональных данных.\n\n"
        "⬇️ Выбери вариант ниже:"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# ==== Обработчик кнопок ====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data in ["agree", "main_menu"]:
        await send_main_menu(query)

    elif query.data == "broadcast_start":
        if query.from_user.id != ADMIN_ID:
            return await query.message.reply_text("🚫 Нет доступа")
        await query.message.reply_text("✍️ Введи текст рассылки одним сообщением:")
        return BROADCAST_WAITING

    elif query.data == "learn":
        caption = (
            "<b>📹 Здесь — видео, с которого всё начинается.</b>\n"
            "<b>Познакомимся, расскажу, кто мы, как создаём ИИ-контент и как запустили самого популярного AI-блогера в России — Фаину Раевскую. </b> 🔥\n\n"
            "Внутри ты узнаешь:\n"
            "✅ 4 ключевых принципа, которые нужно учитывать при создании персонажа, чтобы собрать именно свою аудиторию;\n"
            "✅ Как придумать образ, который зацепит, и почему имя — это уже половина успеха;\n"
            "✅ Как такие проекты монетизируются и приносят деньги уже с первых тысяч подписчиков.\n\n"
            "<b>🧠 И главное — расскажу, чему мы будем учить на обучении🤫</b>"
        )
        keyboard = [
            [InlineKeyboardButton("📝 Запись на обучение", web_app=WebAppInfo(url="https://ai-avatar.ru/learning"))],
            [InlineKeyboardButton("🔐 Закрытый клуб", url="https://t.me/close_channel_neyroph_bot")],
            [InlineKeyboardButton("📺 Канал студии", url="https://t.me/neyroph")],
            [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
        ]
        await query.message.reply_video(
            video="BAACAgIAAxkBAAOjaJQ14sNe900dE7DPLhQygUTwxRUAAg1oAAKfAqFIVvpOlsTmj_g2BA",
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "video":
        text = (
            "🎮 Мы — студия NEYROPH. Профессионально создаём видео-контент для брендов и экспертов.\n\n"
            "🔥 Рекламные креативы, экспертные ролики, Reels на любую тему — делаем с душой и качеством.\n\n"
            "Вы можете:\n— получить готовый ролик под задачу\n— обсудить сценарий и идею\n— довериться нашей команде полностью"
        )
        keyboard = [
            [InlineKeyboardButton("📺 Канал студии", url="https://t.me/neyroph")],
            [InlineKeyboardButton("✉️ Написать в личку", url="https://t.me/ManagerNeyroph")],
            [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "character":
        text = (
            "🎭 Мы можем создать персонажа для вас или вашего бренда так же мощно, как Фаину Раневскую:\n\n"
            "💥 120 000 подписчиков за 1,5 месяца\n🎥 Десятки Reels — по млн просмотров\n\n"
            "Такой формат идеально подходит для продвижения бренда, товара, проекта или инфопродукта!\n\n"
            "Создаём как личный образ, так и бренд-персонажа.\n\n"
            "💬 Напиши нам — обсудим, какой формат подойдёт тебе!"
        )
        keyboard = [
            [InlineKeyboardButton("✉️ Написать в личку", url="https://t.me/ManagerNeyroph")],
            [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
        ]
        await query.message.reply_text(text, reply_markup