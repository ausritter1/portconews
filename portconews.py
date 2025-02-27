import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime
import ssl
from PIL import Image
import re

# Configure SSL context to handle certificate issues
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# Set page configuration
st.set_page_config(
    page_title="RBV Portco News Feed",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="📰"
)

# Hide default sidebar
st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] {
        display: none
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Try to load and display RBV logo
try:
    logo = Image.open("logo.png")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(logo, width=150)
except FileNotFoundError:
    # If logo file not found, just continue
    pass

# App title
st.title("Red Beard Ventures Portco News Feed 📰")
st.write("Stay updated with the latest news from our portfolio companies.")

# RSS feed URL
RSS_FEED_URL = "https://zapier.com/engine/rss/21248761/feed"


# Parses an RSS feed and returns a list of articles
def parse_rss_feed(url):
    try:
        # Parse with SSL verification disabled
        feed = feedparser.parse(url)

        # Check for parse errors
        if hasattr(feed, 'bozo_exception') and feed.bozo_exception:
            st.error(f"Error parsing the RSS feed: {feed.bozo_exception}")
            return []

        articles = []
        seen_links = set()  # Track duplicate articles

        for entry in feed.entries:
            # Skip duplicates
            link = entry.get('link', '')
            if link in seen_links:
                continue
            seen_links.add(link)

            # Extract publication date
            if 'published' in entry:
                try:
                    pub_date = pd.to_datetime(entry.published)
                except:
                    pub_date = datetime.now()
            elif 'updated' in entry:
                try:
                    pub_date = pd.to_datetime(entry.updated)
                except:
                    pub_date = datetime.now()
            else:
                pub_date = datetime.now()

            # Extract description and clean it
            description = entry.get('description', '') or entry.get('summary', '')
            # Clean HTML tags from description
            description = re.sub('<[^<]+?>', '', description)
            # Remove "Title and URL:" prefixes if present
            if "Title and URL:" in description:
                description = description.replace("Title and URL:", "").strip()
                # Remove the URL part if it appears at the end
                if " - http" in description:
                    description = description.split(" - http")[0].strip()

            article = {
                "title": entry.get('title', 'No Title'),
                "link": link,
                "date": pub_date,
                "description": description,
            }

            articles.append(article)

        return articles

    except Exception as e:
        st.error(f"Error loading feed: {e}")
        return []


# Add a refresh button at the top
col1, col2, col3 = st.columns([6, 1, 1])
with col3:
    refresh = st.button("🔄 Refresh")

# Initialize session state for articles if not exists
if 'articles' not in st.session_state or refresh:
    with st.spinner("Loading news feed..."):
        st.session_state.articles = parse_rss_feed(RSS_FEED_URL)

# Main content area - display articles
if not st.session_state.articles:
    st.warning("No articles found in the feed. Please check your connection and try refreshing.")
else:
    # Sort by date (newest first)
    articles = sorted(
        st.session_state.articles,
        key=lambda x: x.get('date', datetime.now()),
        reverse=True
    )

    # Display total count
    st.subheader(f"📚 Showing {len(articles)} News Articles")

    # Display each article
    for article in articles:
        with st.container():
            cols = st.columns([3, 1])

            with cols[0]:
                st.subheader(article['title'])

                # Display date if available
                if 'date' in article:
                    st.caption(f"📅 {article['date'].strftime('%B %d, %Y')}")

                # Display description if available
                if article.get('description') and article['description'] != article['title']:
                    st.write(article['description'])

            with cols[1]:
                if article.get('link'):
                    st.link_button("Read Article", article['link'], use_container_width=True)

            st.divider()

    # Footer
    st.caption("Red Beard Ventures © 2025 | Data updates when you click Refresh.")
