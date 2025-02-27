import streamlit as st
import pandas as pd
import os
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="RBV Portfolio Companies News Feed",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load and display RBV logo
try:
    logo = Image.open("logo.png")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(logo, width=150)
except FileNotFoundError:
    st.warning("Logo file not found. Place 'logo.png' in the app directory.")

# App title
st.title("Red Beard Ventures Portfolio Companies News Feed 📰")
st.write("Stay updated with the latest news from our portfolio companies.")


# Function to load data from Google Sheets
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def load_news_data():
    """Load news data from Google Sheets"""
    try:
        # If using secrets in Streamlit Cloud
        if 'gcp_service_account' in st.secrets:
            credentials_info = st.secrets['gcp_service_account']
            # Create a dictionary from the secrets JSON
            credentials_dict = credentials_info
        else:
            # For local development - load from a credentials.json file
            credentials_path = "credentials.json"
            if not os.path.exists(credentials_path):
                st.error("Google Sheets API credentials not found. Please add credentials.json file.")
                return pd.DataFrame(columns=["Date", "Company", "Title", "Link", "Category"])

            with open(credentials_path, 'r') as f:
                credentials_dict = eval(f.read())

        # Set up credentials
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

        # Authorize and open the spreadsheet
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_url(
            "https://docs.google.com/spreadsheets/d/1Z8D7SLtOmZupp7aK1r6tzPcZNw4vRKjB2T02uEHoaf8/edit#gid=0")
        worksheet = spreadsheet.get_worksheet(0)  # First worksheet

        # Get all data
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Check if expected columns exist, if not create empty DataFrame with expected columns
        expected_columns = ["Date", "Company", "Title", "Link", "Category"]
        if not all(col in df.columns for col in expected_columns):
            missing_cols = [col for col in expected_columns if col not in df.columns]
            st.warning(f"Missing columns in Google Sheet: {', '.join(missing_cols)}")
            # Create DataFrame with expected columns
            for col in missing_cols:
                df[col] = ""

        # Convert date strings to datetime objects if Date column exists and has values
        if "Date" in df.columns and not df["Date"].empty:
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
            # Sort by date (newest first)
            df = df.sort_values(by="Date", ascending=False)

        return df

    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        # Return empty DataFrame with expected columns as fallback
        return pd.DataFrame(columns=["Date", "Company", "Title", "Link", "Category"])


# Load news data
with st.spinner("Loading news data..."):
    news_df = load_news_data()

# Sidebar for filtering
with st.sidebar:
    st.subheader("Filter News")

    # Filter by company if Company column exists
    if "Company" in news_df.columns and not news_df["Company"].empty:
        companies = ["All"] + sorted(news_df["Company"].unique().tolist())
        selected_company = st.selectbox("Company", companies)
    else:
        selected_company = "All"

    # Filter by category if Category column exists
    if "Category" in news_df.columns and not news_df["Category"].empty:
        categories = ["All"] + sorted(news_df["Category"].unique().tolist())
        selected_category = st.selectbox("Category", categories)
    else:
        selected_category = "All"

    # Filter by date range if Date column exists
    if "Date" in news_df.columns and not news_df["Date"].empty:
        date_range = st.date_input(
            "Date Range",
            value=(
                news_df["Date"].min().date(),
                news_df["Date"].max().date()
            ),
            max_value=datetime.now().date()
        )
    else:
        date_range = None

    st.markdown("---")
    st.caption("Red Beard Ventures © 2025")

# Apply filters
filtered_df = news_df.copy()

if selected_company != "All" and "Company" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Company"] == selected_company]

if selected_category != "All" and "Category" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]

if date_range and len(date_range) == 2 and "Date" in filtered_df.columns:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df["Date"].dt.date >= start_date) &
        (filtered_df["Date"].dt.date <= end_date)
        ]

# Display news feed
if filtered_df.empty:
    st.info("No news articles found with the current filters.")
else:
    # Display total count
    st.subheader(f"📚 Showing {len(filtered_df)} News Articles")

    # Show articles
    for i, (_, article) in enumerate(filtered_df.iterrows()):
        with st.container():
            cols = st.columns([3, 1])

            with cols[0]:
                title = article.get("Title", "No Title")
                st.subheader(title)

                # Display metadata if available
                meta_info = []
                if "Date" in article and pd.notna(article["Date"]):
                    date_str = article["Date"].strftime('%B %d, %Y') if isinstance(article["Date"],
                                                                                   pd.Timestamp) else str(
                        article["Date"])
                    meta_info.append(f"📅 {date_str}")
                if "Company" in article and pd.notna(article["Company"]):
                    meta_info.append(f"🏢 {article['Company']}")
                if "Category" in article and pd.notna(article["Category"]):
                    meta_info.append(f"🏷️ {article['Category']}")

                if meta_info:
                    st.caption(" | ".join(meta_info))

            with cols[1]:
                if "Link" in article and pd.notna(article["Link"]):
                    st.link_button("Read Article", article["Link"], use_container_width=True)

            # Optional: Display article description if available
            if "Description" in article and pd.notna(article["Description"]):
                st.write(article["Description"])

            st.markdown("---")

# Add refresh button
if st.button("Refresh Data"):
    st.cache_data.clear()
    st.experimental_rerun()
