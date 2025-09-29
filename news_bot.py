import os
import time
import requests
import schedule
from threading import Thread
from flask import Flask

# ---- Telegram bot setup ----
TOKEN = os.getenv("8197734769:AAE7H4C9NKBSOfhawzWlkAUU-aR7SprkdEg")
CHAT_ID = os.getenv("-4957516199")
NEWS_API_KEY = os.getenv("9e868126e0bf4be880d84539d58e15e8")
TOPIC = os.getenv("TOPIC", "BSF companies research")  # optional env variable

def send_message(text: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    r = requests.post(url, data=payload)
    print("📤 Sent message:", r.json())

def get_news(query=TOPIC, max_results=5):
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize={max_results}"
    )
    response = requests.get(url).json()
    articles = response.get("articles", [])
    if not articles:
        return f"⚠️ No news found for '{query}' today."
    news_list = [f"📰 {a['title']} \n🔗 {a['url']}" for a in articles]
    return "\n\n".join(news_list)

def job():
    news_text = get_news(TOPIC, max_results=3)
    send_message(news_text)

# ---- Scheduler ----
schedule.every(4).hours.do(job)

def run_schedule():
    job()  # send once immediately
    while True:
        schedule.run_pending()
        time.sleep(60)

# ---- Flask server (keeps Render happy) ----
app = Flask("")

@app.route("/")
def home():
    return "Bot is running ✅"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# ---- Start both threads ----
if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=run_schedule).start()
