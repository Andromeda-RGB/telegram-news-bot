def run_bot():
    last_update_id = None
    print("Telegram polling started ✅")
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            if last_update_id:
                url += f"?offset={last_update_id + 1}"
            
            resp = requests.get(url, timeout=10).json()
            print("Raw Telegram response:", resp)  # Debug: see what Telegram returns
            
            for update in resp.get("result", []):
                last_update_id = update["update_id"]  # update offset

                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "").lower()

                print(f"Received message: {text} from chat_id: {chat_id}")  # Debug

                if text == "/start":
                    send_message("👋 Hello! I will keep you updated.", chat_id)
                elif text == "/news":
                    results = []
                    for query in TOPIC_QUERIES:
                        results.extend(get_newsapi(query.strip()))
                    results.extend(get_rss(RSS_FEEDS, "📰"))
                    results.extend(get_rss(RESEARCH_FEEDS, "📄 Research:"))
                    results.extend(get_rss(COMPANY_FEEDS, "🏢 Company"))
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
