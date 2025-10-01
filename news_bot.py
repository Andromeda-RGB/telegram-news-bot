def get_newsapi(query, max_results=5):
    news_list = []
    if not NEWS_API_KEY:
        print("⚠️ NEWS_API_KEY not set, skipping NewsAPI fetch.")
        send_message("⚠️ NEWS_API_KEY not set — cannot fetch news.")
        return news_list

    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}&sortBy=publishedAt&apiKey={NEWS_API_KEY}&pageSize={max_results}"
    )

    try:
        print(f"🔍 Querying NewsAPI for: {query}")
        response = requests.get(url, timeout=10).json()
        print("   Raw NewsAPI response:", response)  # 👈 Added debug

        articles = response.get("articles", [])
        print(f"   → Got {len(articles)} articles back")

        if not articles:
            # Always push Telegram message so you know job ran
            send_message(f"✅ Job ran for '{query}' but no articles found.")

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
        print(f"⚠️ NewsAPI error: {e}")
        send_message(f"⚠️ NewsAPI request failed for '{query}': {e}")  # 👈 Push error to Telegram

    return news_list


def job():
    print("🔄 Running scheduled job...")
    all_news = []

    for query in TOPIC_QUERIES:
        results = get_newsapi(query.strip())
        all_news.extend(results)

    rss_news = get_rss()
    all_news.extend(rss_news)

    if all_news:
        print(f"✅ Sending {len(all_news)} news items")
        send_message("\n\n".join(all_news[:5]))
    else:
        # 👇 Now it will still notify Telegram even if empty
        print("⚠️ No new news to post at this time.")
        send_message("✅ Job ran, but no new news found this time.")
