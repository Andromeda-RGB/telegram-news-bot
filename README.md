# Telegram News Bot (RSS + NewsAPI)

A Telegram bot that scrapes latest news and articles from RSS feeds and NewsAPI, and sends them to your Telegram chat.

## Features
- Fetches latest news/articles from:
  - NewsAPI (keyword-based queries)
  - RSS feeds (company or industry news)
- Avoids duplicate posts
- Sends updates periodically (every hour)
- Hosted on Render with Flask + scheduler

## Setup

1. **Clone the repo**
```bash
git clone <repo-url>
cd <repo-folder>
