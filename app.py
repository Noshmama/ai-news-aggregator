"""AI News Aggregator - Web App focused on AI investment and bubble indicators."""

import os
import sqlite3
import json
import threading
from datetime import datetime
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, jsonify, request

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from config import FEEDS, REFRESH_INTERVAL_MINUTES, MAX_ARTICLES_PER_FEED, ANTHROPIC_API_KEY

app = Flask(__name__)
DB_PATH = Path(__file__).parent / "data" / "news.db"

# Get API key from environment or config
API_KEY = os.environ.get("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)


# ============ Database ============

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            published_date TEXT,
            fetched_date TEXT NOT NULL,
            content TEXT,
            summary TEXT,
            category TEXT,
            sentiment TEXT,
            sentiment_score REAL,
            bubble_indicators TEXT,
            is_read INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_published ON articles(published_date DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sentiment ON articles(sentiment)")
    conn.commit()
    conn.close()


def add_article(article):
    """Add article to database. Returns ID or None if duplicate."""
    conn = get_db()
    try:
        cursor = conn.execute("""
            INSERT INTO articles (title, url, source, published_date, fetched_date, content)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            article['title'],
            article['url'],
            article['source'],
            article.get('published_date'),
            datetime.now().isoformat(),
            article.get('content')
        ))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_articles(limit=50, sentiment=None, category=None):
    """Get articles with optional filters."""
    conn = get_db()
    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if sentiment:
        query += " AND sentiment = ?"
        params.append(sentiment)
    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY published_date DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_article(article_id):
    """Get single article by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_article(article_id, updates):
    """Update an article."""
    conn = get_db()
    for key, value in updates.items():
        # Convert lists to JSON strings
        if isinstance(value, list):
            value = json.dumps(value)
        conn.execute(f"UPDATE articles SET {key} = ? WHERE id = ?", (value, article_id))
    conn.commit()
    conn.close()


def get_stats():
    """Get sentiment and category statistics."""
    conn = get_db()

    sentiment_stats = {}
    rows = conn.execute("""
        SELECT sentiment, COUNT(*) as count FROM articles
        WHERE sentiment IS NOT NULL
        GROUP BY sentiment
    """).fetchall()
    for row in rows:
        sentiment_stats[row['sentiment']] = row['count']

    category_stats = {}
    rows = conn.execute("""
        SELECT category, COUNT(*) as count FROM articles
        WHERE category IS NOT NULL
        GROUP BY category ORDER BY count DESC
    """).fetchall()
    for row in rows:
        category_stats[row['category']] = row['count']

    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    conn.close()
    return {
        'sentiment': sentiment_stats,
        'categories': category_stats,
        'total': total
    }


def get_unprocessed_articles(limit=10):
    """Get articles not yet analyzed by AI."""
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM articles WHERE summary IS NULL
        ORDER BY fetched_date DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ============ Feed Fetching ============

def fetch_feed(feed_config):
    """Fetch articles from a single RSS feed."""
    try:
        parsed = feedparser.parse(feed_config['url'])
        articles = []

        for entry in parsed.entries[:MAX_ARTICLES_PER_FEED]:
            # Get published date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6]).isoformat()
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6]).isoformat()

            # Get content
            content = ''
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].get('value', '')
            elif hasattr(entry, 'summary'):
                content = entry.summary

            # Clean HTML
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                content = soup.get_text(separator=' ', strip=True)[:3000]

            articles.append({
                'title': entry.get('title', 'Untitled'),
                'url': entry.get('link', ''),
                'source': feed_config['name'],
                'published_date': published or datetime.now().isoformat(),
                'content': content
            })

        return articles
    except Exception as e:
        print(f"Error fetching {feed_config['name']}: {e}")
        return []


def fetch_all_feeds():
    """Fetch from all configured feeds."""
    all_articles = []
    for feed in FEEDS:
        articles = fetch_feed(feed)
        all_articles.extend(articles)
    return all_articles


def refresh_feeds():
    """Fetch feeds and add new articles to database."""
    articles = fetch_all_feeds()
    new_count = 0
    for article in articles:
        if article.get('url') and add_article(article):
            new_count += 1
    return new_count


# ============ AI Processing ============

def analyze_article(article):
    """Analyze article with Claude for investment-focused insights."""
    if not API_KEY or not HAS_ANTHROPIC:
        return None

    client = anthropic.Anthropic(api_key=API_KEY)

    prompt = f"""Analyze this AI news article from an INVESTMENT perspective, focusing on AI bubble indicators.

ARTICLE TITLE: {article['title']}
CONTENT: {article.get('content', '')[:2500]}

Provide analysis in JSON format:
{{
    "summary": "2-3 bullet points summarizing key points (use bullet character •)",
    "category": "One of: AI Funding | AI Valuations | AI Layoffs | AI Products | AI Research | AI Regulation | AI Market",
    "sentiment": "Bullish (positive for AI investment), Neutral, or Bearish (bubble warning signs)",
    "sentiment_score": -1.0 to 1.0 (bearish to bullish),
    "bubble_indicators": ["list", "of", "bubble", "warning", "signs", "if", "any"],
    "investment_relevance": "Brief note on why this matters for AI investors"
}}

Focus on identifying:
- Overvaluation signals (excessive funding, unrealistic valuations)
- Market correction signs (layoffs, funding pullback, failed products)
- Hype vs reality gaps
- Sustainable growth indicators"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )

        response = message.content[0].text
        start = response.find('{')
        end = response.rfind('}') + 1

        if start >= 0 and end > start:
            return json.loads(response[start:end])
    except Exception as e:
        print(f"AI analysis error: {e}")

    return None


def process_unanalyzed():
    """Process articles that haven't been analyzed yet."""
    articles = get_unprocessed_articles(limit=5)
    processed = 0

    for article in articles:
        result = analyze_article(article)
        if result:
            bubble = result.get('bubble_indicators', [])
            if isinstance(bubble, list):
                bubble = json.dumps(bubble)
            update_article(article['id'], {
                'summary': result.get('summary'),
                'category': result.get('category'),
                'sentiment': result.get('sentiment'),
                'sentiment_score': result.get('sentiment_score'),
                'bubble_indicators': bubble
            })
            processed += 1

    return processed


# ============ Routes ============

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/articles')
def api_articles():
    sentiment = request.args.get('sentiment')
    category = request.args.get('category')
    limit = request.args.get('limit', 50, type=int)
    articles = get_articles(limit=limit, sentiment=sentiment, category=category)
    return jsonify(articles)


@app.route('/api/article/<int:article_id>')
def api_article(article_id):
    article = get_article(article_id)
    if article:
        update_article(article_id, {'is_read': 1})
        return jsonify(article)
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())


@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    new_count = refresh_feeds()
    return jsonify({'new_articles': new_count})


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    if not API_KEY:
        return jsonify({'error': 'API key not configured', 'processed': 0})
    processed = process_unanalyzed()
    return jsonify({'processed': processed})


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    global API_KEY
    if request.method == 'POST':
        data = request.get_json()
        if 'api_key' in data:
            API_KEY = data['api_key']
        return jsonify({'status': 'saved'})
    return jsonify({'has_api_key': bool(API_KEY)})


# ============ Main ============

if __name__ == '__main__':
    init_db()
    print("Starting AI News Aggregator...")
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    print(f"Open http://localhost:{port} in your browser")
    app.run(debug=debug, host='0.0.0.0', port=port)
else:
    # For gunicorn
    init_db()
