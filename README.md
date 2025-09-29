# Telegram News Bot

A simple Python bot that fetches news from [NewsAPI](https://newsapi.org) and posts to a Telegram group automatically.

## Setup

1. Create a Telegram bot with [BotFather](https://core.telegram.org/bots#botfather).
2. Get your group chat ID.
3. Get a free API key from [NewsAPI](https://newsapi.org).

## Customizing the topic

In `news_bot.py`, look for this line:

```python
news_text = get_news("BSF companies research", max_results=3)
