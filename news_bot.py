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

# Multiple search queries separated by commas
TOPIC_QUERIES = os.getenv("TOPIC", "BSF research,BSF companies,Black Soldier Fly news").split(",")

# Keywords to prioritize research articles
RESEARCH_KEYWORDS = ["research", "journal", "study", "paper", "academic", "experiment", "scientific"]

# Keep track of posted articles to avoid duplicates
posted_urls = set()

def send_message(text: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    r = requests.post(url, data=payload)
    print("📤 Sent message:", r.json())

def get_news(query, max_results=5):
    """Fetch latest news and prioritize research articles"""
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize={max_results}"
    )
    response = requests.get(url).json()
    articles = response.get("articles", [])
    news_list = []

    for a in articles:
        if a['url'] in posted_urls:
            continue

        # Check if title or description contains research keywords
        text_to_check = (a.get("title","") + " " + a.get("description","")).lower()
        is_research = any(k.lower() in text_to_check for k in RESEARCH_KEYWORDS)

        if is_research:
            news_list.insert(0, f"🧪 {a['title']} \n🔗 {a['url']}")  # research on top
        else:
            news_list.append(f"📰 {a['title']} \n🔗 {a['url']}")  # general news

        posted_urls.add(a['url'])

    return news_list

def job():
    all_news = []
    for query in TOPIC_QUERIES:
        news = get_news(query.strip())
        all_news.extend(news)
    if all_news:
        send_message("\n\n".join(all_news))
    else:
        print("⚠️ No new news to post at this time.")

# ---- Scheduler ----
schedule.every(1).hours.do(job)  # every hour

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
