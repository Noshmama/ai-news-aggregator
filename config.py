"""Configuration for AI News Web App."""

# RSS Feeds focused on AI investment and bubble indicators
FEEDS = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "AI Industry"
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "category": "AI Research"
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "category": "AI Industry"
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "category": "AI Industry"
    },
    {
        "name": "VentureBeat AI",
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "AI Business"
    },
    {
        "name": "Hacker News AI",
        "url": "https://hnrss.org/newest?q=AI+OR+artificial+intelligence+OR+LLM+OR+OpenAI",
        "category": "AI Community"
    }
]

# App settings
REFRESH_INTERVAL_MINUTES = 15
MAX_ARTICLES_PER_FEED = 15
ANTHROPIC_API_KEY = ""  # Set your API key here or use the Settings button in the app
