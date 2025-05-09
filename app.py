import streamlit as st
import pandas as pd
from datetime import datetime, date
from pymongo import MongoClient
import os, urllib.parse, requests
from dotenv import load_dotenv
import openai

# ✅ MUST be the first Streamlit command
st.set_page_config(page_title="Succession AI - Business Assistant", layout="wide")

# Load environment variables
load_dotenv()

# MongoDB connection
@st.cache_resource
def init_connection():
    try:
        raw_user = os.getenv("MONGODB_USERNAME")
        raw_pass = os.getenv("MONGODB_PASSWORD")

        if not raw_user or not raw_pass:
            st.error("❌ MongoDB username or password not found. Check your Streamlit secrets.")
            return None

        username = urllib.parse.quote_plus(raw_user)
        password = urllib.parse.quote_plus(raw_pass)
        uri = f"mongodb+srv://{username}:{password}@cluster0.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        client.admin.command("ping")
        return client
    except Exception as e:
        st.error(f"MongoDB connection failed: {e}")
        return None

client = init_connection()
collection = client["succession_ai"]["business_data"] if client else None

# OpenAI config
openai.api_key = os.getenv("OPENAI_API_KEY")

# App title
st.title("💼 Succession AI – Business Assistant")

# Form input
with st.form("seller_form"):
    col1, col2 = st.columns(2)
    with col1:
        full_name = st.text_input("Full Name of Owner")
        company_name = st.text_input("Company Name")
        reg_number = st.text_input("Company Registration Number")
        sector = st.selectbox("Sector", ["UK Leisure", "Retail", "Tech", "Manufacturing"])
    with col2:
        dob = st.date_input("Date of Birth")
        country = st.selectbox("Country", ["United Kingdom", "United States", "India"])
        forecast = st.text_area("1–3 Year Forecast Summary")
        key_products = st.text_area("Key Products (comma-separated)")

    submitted = st.form_submit_button("Submit")
    if submitted:
        form_data = {
            "full_name": full_name,
            "company_name": company_name,
            "reg_number": reg_number,
            "sector": sector,
            "dob": str(dob),
            "country": country,
            "forecast": forecast,
            "key_products": [x.strip() for x in key_products.split(",")],
            "timestamp": datetime.now()
        }
        if collection:
            collection.insert_one(form_data)
            st.success("✔️ Data submitted to MongoDB!")

# Chatbot assistant
st.sidebar.title("🤖 Ask the Business Assistant")
question = st.sidebar.text_area("Ask based on recent submissions:")

if st.sidebar.button("Ask"):
    try:
        records = list(collection.find().sort("timestamp", -1).limit(5))
        context = "\n\n".join([f"Record {i+1}: " + ", ".join(f"{k}: {v}" for k, v in r.items() if k != "_id") for i, r in enumerate(records)])
        prompt = f"Here are recent seller submissions:\n\n{context}\n\nUser question: {question}\n\nAnswer:"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content
        st.sidebar.success(answer)
    except Exception as e:
        st.sidebar.error(f"OpenAI API Error: {e}")
