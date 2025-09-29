import os
import time
import requests
import schedule
from threading import Thread
from flask import Flask
import feedparser
from scholarly import scholarly

# ---- Telegram bot setup ----
TOKEN = os.getenv("8197734769:AAE7H4C9NKBSOfhawzWlkAUU-aR7SprkdEg")
CHAT_ID = os.getenv("-4957516199")
NEWS_API_KEY = os.getenv("9e868126e0bf4be880d84539d58e15e8")

# Comma-separated search queries
TOPIC_QUERIES = os.getenv("TOPIC", "BSF research,BSF companies,Black Soldier Fly news").split(",")

# Keywords to prioritize research
RESEARCH_KEYWORDS = ["research", "journal", "study", "paper", "academic", "experiment", "scientific"]

# Optional RSS feeds (company or industry news)
RSS_FEEDS = os.getenv("RSS_FEEDS", "").split(",")  # e.g. "https://www.bsf-company.com/rss,https://www.industrynews.com/rss"

posted_urls = set()  # track posted URLs

def send_message(text: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    r = requests.post(url, data=payload)
    print("📤 Sent message:", r.json())

# --- NewsAPI ---
def get_newsapi(query, max_results=5):
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
        text_to_check = (a.get("title","") + " " + a.get("description","")).lower()
        is_research = any(k.lower() in text_to_check for k in RESEARCH_KEYWORDS)
        prefix = "🧪" if is_research else "📰"
        news_list.append(f"{prefix} {a['title']} \n🔗 {a['url']}")
        posted_urls.add(a['url'])
    return news_list

# --- Google Scholar ---
def get_scholar(query, max_results=3):
    news_list = []
    search = scholarly.search_pubs(query)
    for i in range(max_results):
        try:
            paper = next(search)
            url = paper.get("pub_url") or paper.get("eprint_url") or paper.get("bib", {}).get("url")
            if not url or url in posted_urls:
                continue
            title = paper.get("bib", {}).get("title", "Untitled")
            news_list.append(f"📚 {title} \n🔗 {url}")
            posted_urls.add(url)
        except StopIteration:
            break
    return news_list

# --- RSS feeds ---
def get_rss():
    news_list = []
    for feed_url in RSS_FEEDS:
        if not feed_url.strip():
            continue
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:3]:
            url = entry.link
            if url in posted_urls:
                continue
            title = entry.title
            news_list.append(f"📰 {title} \n🔗 {url}")
            posted_urls.add(url)
    return news_list

# --- Job to run every hour ---
def job():
    all_news = []

    for query in TOPIC_QUERIES:
        all_news.extend(get_newsapi(query.strip()))
        all_news.extend(get_scholar(query.strip()))

    all_news.extend(get_rss())

    if all_news:
        send_message("\n\n".join(all_news))
    else:
        print("⚠️ No new news to post at this time.")

# ---- Scheduler ----
schedule.every(1).hours.do(job)

def run_schedule():
    job()  # send immediately
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
