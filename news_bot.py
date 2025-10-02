import os
import time
import requests
import schedule
import difflib
from threading import Thread
from flask import Flask
import feedparser

# ---- Telegram bot setup ----
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# Topics / Keywords
TOPIC_QUERIES = os.getenv(
    "TOPIC",
    "Black soldier fly research,black soldier fly companies,Black Soldier Fly news, hermetia illucens, black soldier fly protein, black soldier fly frass, black soldier fly oil"
).split(",")

# Feeds
RSS_FEEDS = os.getenv("RSS_FEEDS", "").split(",")
RESEARCH_FEEDS = os.getenv("RESEARCH_FEEDS", "").split(",")
COMPANY_FEEDS = os.getenv("COMPANY_FEEDS", "").split(",")
SOCIAL_FEEDS = os.getenv("SOCIAL_FEEDS", "").split(",")

posted_urls = set()

# ---- Telegram ----
def send_message(text: str, chat_id: str = None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id or CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        print(f"Sending message: {text[:80]}...")
        r = requests.post(url, data=payload, timeout=10)
        print("Telegram response:", r.json())
    except Exception as e:
        print("Error sending message:", e)

# ---- Keyword Matching ----
RELEVANT_KEYWORDS = [k.lower().strip() for k in TOPIC_QUERIES]

def matches_keywords(text: str) -> bool:
    """Check if text matches any relevant keyword (fuzzy)."""
    text = text.lower()
    for kw in RELEVANT_KEYWORDS:
        if kw in text:
            return True
        # fuzzy match: similarity > 0.7
        ratio = difflib.SequenceMatcher(None, kw, text).quick_ratio()
        if ratio > 0.7:
            return True
    return False

# ---- NewsAPI ----
def get_newsapi(query, max_results=5):
    news_list = []
    if not NEWS_API_KEY:
        print("NEWS_API_KEY not set, skipping NewsAPI.")
        return news_list

    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize={max_results}"

    try:
        print(f"🔍 Querying NewsAPI for: {query}")
        response = requests.get(url, timeout=10).json()

        if response.get("status") != "ok":
            print(f"⚠️ NewsAPI error: {response}")
            return news_list

        articles = response.get("articles", [])
        print(f"   → Got {len(articles)} articles back")

        for a in articles:
            url_link = a['url']
            title = a.get('title', '')
            text_check = (title + ' ' + a.get('description', '')).lower()

            if url_link in posted_urls:
                continue
            if not matches_keywords(text_check):
                continue

            news_list.append(f"📰 {title}\n🔗 {url_link}")
            posted_urls.add(url_link)
    except Exception as e:
        print(f"Exception NewsAPI: {e}")
    return news_list

# ---- Generic RSS ----
def get_rss(feeds, category_name):
    news_list = []
    for feed_url in feeds:
        if not feed_url.strip():
            continue
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                url = entry.link
                title = entry.title
                summary = getattr(entry, "summary", "")
                text_check = (title + " " + summary).lower()

                print(f"Fetched entry: {title} -> {url}")

                if url in posted_urls:
                    continue
                if not matches_keywords(text_check):
                    continue

                news_list.append(f"{category_name} {title}\n🔗 {url}")
                posted_urls.add(url)
        except Exception as e:
            print(f"RSS error ({feed_url}): {e}")
    return news_list

# ---- Scheduled Job ----
def job():
    print("⏰ Running scheduled job...")
    all_news = []

    # NewsAPI
    for query in TOPIC_QUERIES:
        all_news.extend(get_newsapi(query.strip()))

    # RSS Feeds
    all_news.extend(get_rss(RSS_FEEDS, '📰'))
    all_news.extend(get_rss(RESEARCH_FEEDS, '📄 Research:'))
    all_news.extend(get_rss(COMPANY_FEEDS, '🏢 Company:'))
    all_news.extend(get_rss(SOCIAL_FEEDS, '💬 Social:'))

    if all_news:
        message = "\n\n".join(all_news[:10])
        send_message(message)
    else:
        send_message("✅ Job ran, no new articles found.")

# ---- Scheduler ----
schedule.every(1).hours.do(job)

def run_schedule():
    job()  # run once at startup
    while True:
        schedule.run_pending()
        time.sleep(60)

# ---- Flask ----
app = Flask("")

@app.route("/")
def home():
    return "Bot is running ✅"

@app.route("/run-job")
def run_job():
    job()
    return "Job executed ✅"

def run_flask():
    app.run(host="0.0.0.0", port=5000)

# ---- Telegram Listener ----
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

                if text == "/start":
                    send_message("👋 Hello! I will keep you updated.", chat_id)
                elif text == "/news":
                    results = []
                    for query in TOPIC_QUERIES:
                        results.extend(get_newsapi(query.strip()))
                    results.extend(get_rss(RSS_FEEDS, '📰'))
                    results.extend(get_rss(RESEARCH_FEEDS, '📄 Research:'))
                    results.extend(get_rss(COMPANY_FEEDS, '🏢 Company:'))
                    results.extend(get_rss(SOCIAL_FEEDS, '💬 Social:'))

                    if results:
                        send_message("\n\n".join(results[:10]), chat_id)
                    else:
                        send_message("✅ No new articles found.", chat_id)
        except Exception as e:
            print("Bot polling error:", e)
        time.sleep(5)

# ---- Start threads ----
if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=run_schedule).start()
    Thread(target=run_bot).start()
