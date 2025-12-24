import streamlit as st
import pandas as pd
import requests
import re
import time
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Amazon Market Analyzer", layout="wide")

if 'data' not in st.session_state:
    st.session_state['data'] = None
if 'error' not in st.session_state:
    st.session_state['error'] = None

CATEGORIES = {
    "Technology & Programming": "programming books",
    "Business & Money": "business and money books",
    "Science Fiction & Fantasy": "science fiction and fantasy books",
    "Self-Help & Psychology": "self help books",
    "Biographies": "biographies and memoirs",
    "History": "history books",
    "Children's Books": "childrens books",
    "Health & Fitness": "health and fitness books",
    "Cookbooks": "cookbooks food and wine"
}

SORT_OPTIONS = {
    "Relevance": "RELEVANCE",
    "Lowest Price": "LOWEST_PRICE",
    "Highest Price": "HIGHEST_PRICE",
    "Highest Rated": "REVIEWS",
    "Newest Arrivals": "NEWEST"
}

@st.cache_data
def fetch_data(query, sort_code):
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        return pd.DataFrame(), "Missing API key in environment variables."

    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    
    querystring = {
        "query": query, 
        "page": "1", 
        "country": "US", 
        "sort_by": sort_code, 
        "category_id": "books"
    }
    
    headers = {
        "x-rapidapi-key": api_key, 
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        products = data.get("data", {}).get("products", [])

        if not products: 
            return pd.DataFrame(), "No products found."

        clean_data = []
        for item in products:
            raw_price = item.get("product_price")
            price = 0.0
            if raw_price:
                try:
                    clean_str = str(raw_price).replace("$", "").replace(",", "").replace("from ", "").split(" - ")[0]
                    price = float(clean_str)
                except: 
                    price = 0.0

            raw_rating = item.get("product_star_rating")
            rating = float(raw_rating) if raw_rating else 0.0
            
            raw_reviews = item.get("product_num_ratings")
            reviews = int(raw_reviews) if raw_reviews else 0

            title = item.get("product_title", "Unknown")
            fmt = "Standard"
            if "Paperback" in title: 
                fmt = "Paperback"
            elif "Hardcover" in title: 
                fmt = "Hardcover"
            elif "Audiobook" in title: 
                fmt = "Audiobook"

            clean_data.append({
                "Title": title,
                "Rating": rating,
                "Reviews": reviews,
                "Price": price,
                "Format": fmt,
                "Best_Seller": "Yes" if item.get("is_best_seller") else "No",
                "Image": item.get("product_photo", ""),
                "Link": item.get("product_url", "#")
            })

        return pd.DataFrame(clean_data), None

    except Exception as e:
        return pd.DataFrame(), f"Server Error: {str(e)}"

with st.sidebar:
    st.header("Settings")
    
    if os.getenv("RAPIDAPI_KEY"):
        st.success("API Key Loaded")
    else:
        st.error("Missing .env file")
    
    st.divider()
    
    selected_category_name = st.selectbox("Category", list(CATEGORIES.keys()))
    selected_sort_name = st.selectbox("Sort By", list(SORT_OPTIONS.keys()))
    
    raw_query = CATEGORIES[selected_category_name]
    clean_query = re.sub(r'[^a-zA-Z0-9 ]', '', raw_query)
    api_sort_code = SORT_OPTIONS[selected_sort_name]
    
    st.divider()
    
    if st.button("Run Analysis", type="primary"):
        if "last_run" in st.session_state and time.time() - st.session_state["last_run"] < 2:
            st.warning("Please wait a moment before retrying.")
            st.stop()
        st.session_state["last_run"] = time.time()
        
        with st.spinner(f"Querying Amazon..."):
            df, error = fetch_data(clean_query, api_sort_code)
            st.session_state['data'] = df
            st.session_state['error'] = error

st.title("Amazon Book Analyzer")
st.markdown(f"**{selected_category_name}** | Sorted by: **{selected_sort_name}**")

if st.session_state['data'] is not None and not st.session_state['data'].empty:
    
    df = st.session_state['data']
    
    c1, c2 = st.columns(2)
    c1.metric("Books Found", len(df))
    c2.metric("Best Sellers", len(df[df['Best_Seller'] == "Yes"]))
    
    st.divider()

    st.subheader("Top 10 Results")
    top_10 = df.head(10)
    
    cols = st.columns(5)
    for index, row in top_10.iterrows():
        col = cols[index % 5]
        with col:
            img = row['Image'] if row['Image'] else "https://via.placeholder.com/150"
            st.image(img, use_container_width=True)
            
            st.markdown(f"**{(row['Title'][:40] + '...') if len(row['Title']) > 40 else row['Title']}**")
            
            color = "green" if row['Format'] == "Paperback" else "orange" if row['Format'] == "Hardcover" else "gray"
            st.markdown(f":{color}[{row['Format']}]")
            st.markdown(f"**${row['Price']:.2f}**")
            st.link_button("View on Amazon", row['Link'])
            
            if (index + 1) % 5 == 0:
                st.divider()

elif st.session_state['error']:
    st.error(st.session_state['error'])
else:
    st.info("Select options in the sidebar and click Run Analysis.")