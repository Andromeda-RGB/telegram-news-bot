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

# Topics / Keywords
TOPIC_QUERIES = os.getenv(
    "TOPIC",
    "Black soldier fly research,black soldier fly companies,Black Soldier Fly news,hermetia illucens,black soldier fly protein,black soldier fly frass,black soldier fly oil"
).split(",")

# RSS Feeds (multiple categories)
RSS_FEEDS = os.getenv("RSS_FEEDS", "").split(",")
RESEARCH_FEEDS = os.getenv("RESEARCH_FEEDS", "").split(",")
COMPANY_FEEDS = os.getenv("COMPANY_FEEDS", "").split(",")
SOCIAL_FEEDS = os.getenv("SOCIAL_FEEDS", "").split(",")

posted_urls = set()
RELEVANT_KEYWORDS = [k.lower().strip() for k in TOPIC_QUERIES if k.strip()]

# ---- Telegram ----
def send_message(text: str, chat_id: str = None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id or CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        print("Telegram response:", r.json())
    except Exception as e:
        print("Error sending message:", e)

def send_long_message(text, chat_id):
    """Split long messages into multiple chunks for Telegram (max 4096 chars)."""
    MAX_LENGTH = 4000
    chunks = [text[i:i+MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]
    for chunk in chunks:
        send_message(chunk, chat_id)

# ---- NewsAPI ----
def get_newsapi(query, max_results=5):
    news_list = []
    if not NEWS_API_KEY:
        return news_list

    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize={max_results}"

    try:
        response = requests.get(url, timeout=10).json()
        if response.get("status") != "ok":
            return news_list

        for a in response.get("articles", []):
            url_link = a["url"]
            title = a.get("title", "")
            desc = a.get("description", "")
            content = a.get("content", "")
            text_check = f"{title} {desc} {content}".lower()

            if url_link in posted_urls:
                continue
            if not any(k in text_check for k in RELEVANT_KEYWORDS):
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
                content = " ".join(c.get("value", "") for c in entry.get("content", [])) if hasattr(entry, "content") else ""
                text_check = f"{title} {summary} {content}".lower()

                if url in posted_urls:
                    continue
                if not any(k in text_check for k in RELEVANT_KEYWORDS):
                    continue

                news_list.append(f"{category_name} {title}\n🔗 {url}")
                posted_urls.add(url)
        except Exception as e:
            print(f"RSS error ({feed_url}): {e}")
    return news_list

# ---- Debug Command ----
def debug_dump(chat_id):
    debug_texts = []

    # NewsAPI
    for query in TOPIC_QUERIES:
        try:
            url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize=10"
            response = requests.get(url, timeout=10).json()
            debug_texts.append(f"\n\n🔎 <b>NewsAPI Query: {query}</b>")
            for a in response.get("articles", []):
                title = a.get("title", "")
                url_link = a.get("url", "")
                desc = a.get("description", "")
                content = a.get("content", "")
                text_check = f"{title} {desc} {content}".lower()
                match = "✅" if any(k in text_check for k in RELEVANT_KEYWORDS) else "❌"
                debug_texts.append(f"{match} {title}\n🔗 {url_link}")
        except Exception as e:
            debug_texts.append(f"⚠️ NewsAPI error for {query}: {e}")

    # RSS/Research/Company/Social
    for feeds, label in [
        (RSS_FEEDS, "📰 RSS"),
        (RESEARCH_FEEDS, "📄 Research"),
        (COMPANY_FEEDS, "🏢 Company"),
        (SOCIAL_FEEDS, "💬 Social"),
    ]:
        for feed_url in feeds:
            if not feed_url.strip():
                continue
            try:
                feed = feedparser.parse(feed_url)
                debug_texts.append(f"\n\n🔎 <b>{label} Feed:</b> {feed_url}")
                for entry in feed.entries[:10]:
                    title = entry.title
                    url = entry.link
                    summary = getattr(entry, "summary", "")
                    content = " ".join(c.get("value", "") for c in entry.get("content", [])) if hasattr(entry, "content") else ""
                    text_check = f"{title} {summary} {content}".lower()
                    match = "✅" if any(k in text_check for k in RELEVANT_KEYWORDS) else "❌"
                    debug_texts.append(f"{match} {title}\n🔗 {url}")
            except Exception as e:
                debug_texts.append(f"⚠️ {label} error ({feed_url}): {e}")

    send_long_message("\n".join(debug_texts), chat_id)

# ---- Scheduled Job ----
def job():
    print("Running scheduled job...")
    all_news = []

    for query in TOPIC_QUERIES:
        all_news.extend(get_newsapi(query.strip()))

    all_news.extend(get_rss(RSS_FEEDS, "📰"))
    all_news.extend(get_rss(RESEARCH_FEEDS, "📄 Research:"))
    all_news.extend(get_rss(COMPANY_FEEDS, "🏢 Company:"))
    all_news.extend(get_rss(SOCIAL_FEEDS, "💬 Social:"))

    if all_news:
        message = "\n\n".join(all_news[:10])
        send_message(message)
    else:
        send_message("✅ Job ran, no new keyword-matching articles found.")

# ---- Scheduler ----
schedule.every(1).hours.do(job)

def run_schedule():
    job()
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
                    results.extend(get_rss(RSS_FEEDS, "📰"))
                    results.extend(get_rss(RESEARCH_FEEDS, "📄 Research:"))
                    results.extend(get_rss(COMPANY_FEEDS, "🏢 Company:"))
                    results.extend(get_rss(SOCIAL_FEEDS, "💬 Social:"))
                    if results:
                        send_message("\n\n".join(results[:10]), chat_id)
                    else:
                        send_message("✅ No new keyword-matching articles.", chat_id)
                elif text == "/debug":
                    send_message("🔍 Debugging… fetching all sources.", chat_id)
                    debug_dump(chat_id)

        except Exception as e:
            print("Bot polling error:", e)
        time.sleep(5)

# ---- Start threads ----
if __name__ == "__main__":
    Thread(target=run_schedule).start()
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=5000)
