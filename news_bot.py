import os
import time
import requests
import schedule
from threading import Thread
from flask import Flask
import feedparser

# ---- Telegram bot setup ----
TOKEN = os.getenv("BOT_TOKEN")          # Set this in Render environment
CHAT_ID = os.getenv("CHAT_ID")          # Set this in Render environment
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Set this in Render environment

# Comma-separated search queries
TOPIC_QUERIES = os.getenv("TOPIC", "BSF research,BSF companies,Black Soldier Fly news").split(",")

# Optional RSS feeds
RSS_FEEDS = os.getenv("RSS_FEEDS", "").split(",")  # e.g., "https://www.bsf-company.com/rss,https://www.industrynews.com/rss"

posted_urls = set()  # track posted URLs

def send_message(text: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        print("📤 Sent message:", r.json())
    except Exception as e:
        print("⚠️ Error sending message:", e)

# --- NewsAPI ---
def get_newsapi(query, max_results=5):
    news_list = []
    if not NEWS_API_KEY:
        return news_list
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize={max_results}"
    )
    try:
        response = requests.get(url, timeout=10).json()
        articles = response.get("articles", [])
        for a in articles:
            if a['url'] in posted_urls:
                continue
            news_list.append(f"📰 {a['title']} \n🔗 {a['url']}")
            posted_urls.add(a['url'])
    except Exception as e:
        print(f"⚠️ NewsAPI error: {e}")
    return news_list

# --- RSS feeds ---
def get_rss():
    news_list = []
    for feed_url in RSS_FEEDS:
        if not feed_url.strip():
            continue
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                url = entry.link
                if url in posted_urls:
                    continue
                title = entry.title
                news_list.append(f"📰 {title} \n🔗 {url}")
                posted_urls.add(url)
        except Exception as e:
            print(f"⚠️ RSS error ({feed_url}): {e}")
    return news_list

# --- Job to run periodically ---
def job():
    all_news = []

    for query in TOPIC_QUERIES:
        all_news.extend(get_newsapi(query.strip()))

    all_news.extend(get_rss())

    if all_news:
        send_message("\n\n".join(all_news))
    else:
        print("⚠️ No new news to post at this time.")

# ---- Scheduler ----
schedule.every(1).hours.do(job)

def run_schedule():
    job()  # send immediately on start
    while True:
        schedule.run_pending()
        time.sleep(60)

# ---- Flask server (keeps Render alive) ----
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
