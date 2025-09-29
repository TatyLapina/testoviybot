import os, time, psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Bot

DB_URL = os.getenv("DATABASE_URL")
if DB_URL and "sslmode=" not in DB_URL:
    DB_URL += ("&sslmode=require" if "?" in DB_URL else "?sslmode=require")

bot = Bot(token=os.environ["BOT_TOKEN"])

def get_conn():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

def get_all_users():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT chat_id FROM users WHERE subscribed = TRUE;")
        return [row["chat_id"] for row in cur.fetchall()]

def send_all(text):
    for cid in get_all_users():
        try:
            bot.send_message(chat_id=cid, text=text)
            time.sleep(0.05)
        except Exception as e:
            print(f"Ошибка {cid}: {e}")

if __name__ == "__main__":
    send_all("Привет! Это тестовая рассылка 🚀")
