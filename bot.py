import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import asyncio

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
ADMIN_ID =1048694959  # замени на свой Telegram ID

# ==== Состояния ====
BROADCAST_WAITING = 1

# ==== Работа с БД ====
def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def init_db():
    with get_conn() as conn, conn.cursor() as cur:
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
    print("✅ Таблица users готова")

def save_user(user):
    with get_conn() as conn, conn.cursor() as cur:
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

def get_all_users():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT chat_id FROM users WHERE subscribed = TRUE;")
        return [row["chat_id"] for row in cur.fetchall()]

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
            "✅ 4 ключевых принципа, которые нужно учитывать при создании персонажа;\n"
            "✅ Как придумать образ, который зацепит;\n"
            "✅ Как такие проекты монетизируются.\n\n"
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
            "🔥 Рекламные креативы, экспертные ролики, Reels на любую тему — делаем с душой и качеством."
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
            "Такой формат идеально подходит для продвижения бренда!"
        )
        keyboard = [
            [InlineKeyboardButton("✉️ Написать в личку", url="https://t.me/ManagerNeyroph")],
            [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "promo":
        text = (
            "🎮 Создание reels с вашим брендом\n\n"
            "Ты хочешь, чтобы о твоём продукте не просто знали — ты хочешь, чтобы им восхищались, сохраняли и покупали.\n\n"
            "Мы умеем делать Reels, которые не выглядят как реклама. Это мини‑сюжет, где бренд — часть истории, который идеально интегрирован в тематику и концепцию профиля.\n\n"
            "📦 Что входит:\n"
            "✅ Сценарий под вашу цель\n"
            "✅ Интеграция продукта — через эмоции и сторителлинг\n"
            "✅ Озвучка от лица Фаины\n"
            "✅ Публикация в ленту (с соавторством, если необходимо) + сторис\n\n"
            "🌟 Это подойдёт, если:\n"
            "— У тебя классный продукт и ты хочешь, чтобы весь мир о нём узнал\n"
            "— Тебе важна эмоция, стиль и глубина подачи\n\n"
            "А теперь 👇"
        )
        keyboard = [
            [InlineKeyboardButton("📊 Посмотреть статистику", callback_data="stats")],
            [InlineKeyboardButton("💰 Узнать цены", callback_data="pricing")],
            [InlineKeyboardButton("✉️ Написать в личку", url="https://t.me/ManagerNeyroph")],
            [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == "stats":
        with open("stat1.jpg", "rb") as img1, open("stat2.jpg", "rb") as img2, open("stat3.jpg", "rb") as img3:
            media = [InputMediaPhoto(img1), InputMediaPhoto(img2), InputMediaPhoto(img3)]
            await query.message.reply_media_group(media)

    elif query.data == "pricing":
        text = (
            "💰 СТОИМОСТЬ: от 35 000 рублей\n"
            "(зависит от задачи, длительности ролика)\n\n"
            "📌 Как работаем:\n"
            "▪️ Ты пишешь в личку — кто ты и что продвигаешь\n"
            "▪️ Мы изучаем продукт и задаем вопросы\n"
            "▪️ Даем точную цену\n"
            "▪️ Предлагаем идею, которая будет органично вписываться в профиль\n"
            "▪️ Создаем и монтируем ролик\n"
            "▪️ Публикуем Reels\n"
            "▪️ Ты получаешь не просто просмотры, а заявки и клиентов\n\n"
            "Важно: мы берем на рекламу не всех. Только те бренды, в которых уверены и которые не противоречат этическим принципам."
        )
        keyboard = [
            [InlineKeyboardButton("✉️ Написать в личку", url="https://t.me/ManagerNeyroph")],
            [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    text = update.message.text
    users = get_all_users()
    sent, failed = 0, 0

    with get_conn() as conn, conn.cursor() as cur:
        for cid in users:
            try:
                await context.bot.send_message(cid, text)
                sent += 1
                await asyncio.sleep(0.05)
            except Forbidden:
                cur.execute("UPDATE users SET subscribed = FALSE WHERE chat_id = %s;", (cid,))
                failed += 1
            except Exception as e:
                print(f"Ошибка {cid}: {e}")
                failed += 1

    await update.message.reply_text(f"✅ Рассылка завершена.\nУспешно: {sent}, Ошибок: {failed}")
    return ConversationHandler.END

async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Рассылка отменена")
    return ConversationHandler.END
def main():
    init_db()
    defaults = Defaults(parse_mode=constants.ParseMode.HTML)
    app = ApplicationBuilder().token(TOKEN).defaults(defaults).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^broadcast_start$")],
        states={
            BROADCAST_WAITING: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)]
        },
        fallbacks=[CommandHandler("cancel", broadcast_cancel)],
    )
    app.add_handler(conv_handler)

    print("🚀 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()


