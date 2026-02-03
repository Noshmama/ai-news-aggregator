# AI News Aggregator

A web app that aggregates AI-focused news with emphasis on investment sentiment and bubble indicators.

## Features

- **RSS Feed Aggregation** - Pulls from TechCrunch, MIT Tech Review, The Verge, Ars Technica, VentureBeat, and Hacker News
- **AI-Powered Analysis** - Uses Claude API to generate summaries, categorize articles, and assess investment sentiment
- **Sentiment Tracking** - Classifies articles as Bullish, Neutral, or Bearish for AI investment
- **Bubble Indicators** - Identifies warning signs like overvaluation, layoffs, funding pullback
- **Dashboard** - Visual breakdown of market sentiment and category distribution

## Screenshot

The app provides a clean interface with:
- Market sentiment bar showing Bullish/Neutral/Bearish distribution
- Filterable article list by sentiment and category
- Detailed view with AI summary and bubble indicators

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Add your Anthropic API key (optional, for AI analysis):
   - Edit `config.py` and set `ANTHROPIC_API_KEY`
   - Or use the Settings button in the app

3. Run the app:
```bash
python app.py
```

4. Open http://localhost:5000 in your browser

## Usage

1. Click **Refresh Feeds** to fetch latest AI news
2. Click **Analyze with AI** to process articles (requires API key)
3. Use filters to view by sentiment or category
4. Click any article to see full details and AI analysis

## Tech Stack

- **Backend**: Python, Flask
- **Database**: SQLite
- **AI**: Anthropic Claude API
- **Frontend**: Vanilla HTML/CSS/JS

## Configuration

Edit `config.py` to:
- Add/remove RSS feeds
- Change refresh interval
- Set your API key

## License

MIT
