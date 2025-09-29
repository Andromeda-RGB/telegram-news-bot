import os
import time
import requests
import schedule

# Load secrets from environment variables (Render dashboard)
TOKEN = os.getenv("8197734769:AAE7H4C9NKBSOfhawzWlkAUU-aR7SprkdEg")
CHAT_ID = os.getenv("-4957516199")
NEWS_API_KEY = os.getenv("9e868126e0bf4be880d84539d58e15e8")

def send_message(text: str):
    """Send a message to Telegram group"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    r = requests.post(url, data=payload)
    print("📤 Sent message:", r.json())

def get_news(query="BSF companies research", max_results=5):
    """Fetch latest news from NewsAPI"""
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
    """Main scheduled job"""
    # 👉 Change the search term here to customize your news feed
    news_text = get_news("BSF companies research", max_results=3)
    send_message(news_text)

# Schedule job every 4 hours
schedule.every(4).hours.do(job)

print("✅ Bot started! Will send news every 4 hours...")
job()  # send immediately once

while True:
    schedule.run_pending()
    time.sleep(60)
