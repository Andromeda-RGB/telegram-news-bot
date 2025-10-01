import os
import time
import requests
import schedule
from threading import Thread
from flask import Flask
import feedparser

# ---- Telegram bot setup ----
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Comma-separated search queries
TOPIC_QUERIES = os.getenv(
    "TOPIC",
    "Black soldier fly research,black soldier fly companies,Black Soldier Fly news, hermetia illucens, black soldier fly protein, black soldier fly frass, black soldier fly oil"
).split(",")

# Optional RSS feeds
RSS_FEEDS = os.getenv("RSS_FEEDS", "").split(",")

posted_urls = set()  # track posted URLs

def send_message(text: str, chat_id: str = None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id or CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        print(f"👉 Sending message to {chat_id or CHAT_ID}: {text[:80]}...")
        r = requests.post(url, data=payload, timeout=10)
        print("📤 Telegram response:", r.json())
    except Exception as e:
        print("⚠️ Error sending message:", e)

# --- NewsAPI ---
RELEVANT_KEYWORDS = [
    "black soldier fly", "insect protein", "black soldier fly larvae",
    "black soldier fly protein", "black soldier fly oil", "black soldier fly feed",
    "black soldier fly fat", "black soldier fly frass", "black soldier fly substrate",
    "black soldier fly alternate protein", "black soldier fly fertilizer",
    "black soldier fly egg", "hermetia illucens", "black soldier fly research"
]

def get_newsapi(query, max_results=5):
    news_list = []
    if not NEWS_API_KEY:
        print("⚠️ NEWS_API_KEY not set, skipping NewsAPI fetch.")
        return news_list

    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize={max_results}"
    )

    try:
        print(f"🔍 Querying NewsAPI for: {query}")
        response = requests.get(url, timeout=10).json()
        print("   Raw NewsAPI response:", response)

        if response.get("status") != "ok":
            code = response.get("code", "unknown")
            msg = response.get("message", "")
            print(f"⚠️ NewsAPI error: {code} - {msg}")
            return news_list

        articles = response.get("articles", [])
        print(f"   → Got {len(articles)} articles back")
        for a in articles:
            text_to_check = (a.get("title", "") + " " + a.get("description", "")).lower()
            if a['url'] in posted_urls:
                print(f"   ↩️ Skipping duplicate: {a['title']}")
                continue
            if not any(k.lower() in text_to_check for k in RELEVANT_KEYWORDS):
                print(f"   ❌ Skipping unrelated: {a['title']}")
                continue
            news_item = f"📰 {a['title']} \n🔗 {a['url']}"
            news_list.append(news_item)
            posted_urls.add(a['url'])
            print(f"   ✅ Added: {a['title']}")

    except Exception as e:
        print(f"⚠️ NewsAPI exception: {e}")

    return news_list

# --- RSS feeds ---
def get_rss():
    news_list = []
    print("🔍 RSS_FEEDS:", RSS_FEEDS)
    for feed_url in RSS_FEEDS:
        feed_url = feed_url.strip()
        if not feed_url:
            continue
        try:
            print(f"📡 Fetching RSS: {feed_url}")
            feed = feedparser.parse(feed_url)
            print(f"   → {len(feed.entries)} entries found in RSS")
            for entry in feed.entries[:5]:
                url = entry.link
                title = entry.title
                text_to_check = title.lower()

                if url in posted_urls:
                    print(f"   ↩️ Skipping duplicate RSS: {title}")
                    continue
                if not any(k.lower() in text_to_check for k in RELEVANT_KEYWORDS):
                    print(f"   ❌ Skipping unrelated RSS: {title}")
                    continue
                news_item = f"📰 {title} \n🔗 {url}"
                news_list.append(news_item)
                posted_urls.add(url)
                print(f"   ✅ Added RSS: {title}")

        except Exception as e:
            print(f"⚠️ RSS error ({feed_url}): {e}")

    return news_list

# --- Job to run periodically ---
def job():
    print("🔄 Running scheduled job...")
    all_news = []

    newsapi_count = 0
    for query in TOPIC_QUERIES:
        results = get_newsapi(query.strip())
        all_news.extend(results)
        newsapi_count += len(results)

    rss_news = get_rss()
    all_news.extend(rss_news)
    rss_count = len(rss_news)

    summary_msg = f"✅ Job finished.\nNewsAPI articles: {newsapi_count}\nRSS articles: {rss_count}"
    if all_news:
        send_message("\n\n".join(all_news[:10]) + "\n\n" + summary_msg)
    else:
        send_message(summary_msg + "\nNo new articles found.")

# ---- Scheduler ----
schedule.every(1).hours.do(job)

def run_schedule():
    job()  # send immediately on start
    while True:
        schedule.run_pending()
        time.sleep(60)

# ---- Telegram Bot Listener ----
def run_bot():
    last_update_id = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            if last_update_id:
                url += f"?offset={last_update_id + 1}"
            resp = requests.get(url, timeout=10).json()

            for update in resp.get("result", []):
                last_update_id = update["update_id"]
                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "").lower()
                print(f"💬 Received message: {text} from chat {chat_id}")

                if text == "/start":
                    send_message(
                        "👋 Hello! I will keep you updated with Black Soldier Fly news. Type /news anytime to fetch the latest.",
                        chat_id
                    )
                elif text == "/news":
                    results = []
                    for query in TOPIC_QUERIES:
                        results.extend(get_newsapi(query.strip()))
                    results.extend(get_rss())
                    if results:
                        send_message("\n\n".join(results[:10]), chat_id)
                    else:
                        send_message("⚠️ No fresh news found right now.", chat_id)

        except Exception as e:
            print("⚠️ Bot polling error:", e)

        time.sleep(5)

# ---- Flask server (keeps Render alive) ----
app = Flask("")

@app.route("/")
def home():
    return "Bot is running ✅"

@app.route("/run-job")
def run_job():
    job()
    return "Job executed ✅"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# ---- Start all threads ----
if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=run_schedule).start()
    Thread(target=run_bot).start()
