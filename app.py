import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, date
import urllib.parse
import os
import re
import openai
from dotenv import load_dotenv

# Set page config first
st.set_page_config(page_title="Succession AI - Business Assistant", layout="wide")

# Load environment
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# MongoDB connection
@st.cache_resource
def init_connection():
    try:
        raw_user = os.getenv("MONGODB_USERNAME")
        raw_pass = os.getenv("MONGODB_PASSWORD")
        if not raw_user or not raw_pass:
            st.error("❌ MongoDB credentials not found. Set secrets.")
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

# Form sections
st.sidebar.title("Navigation")
section = st.sidebar.selectbox("Go to section:", [
    "Personal Details", "Company Details", "Financial Info", "Sector Info",
    "Management & Shareholders", "Employee Info", "Submit All Business Info", "Ask AI"
])

st.title("Succession AI - Business Assistant")

if 'form_data' not in st.session_state:
    st.session_state.form_data = {}

def update_form(key, value):
    st.session_state.form_data[key] = value

def calculate_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

if section == "Personal Details":
    prefix = st.selectbox("Prefix", ["Mr", "Mrs", "Ms", "Dr"])
    full_name = st.text_input("Full Name of the Owner")
    dob = st.date_input("Date of Birth", date(1990, 1, 1))
    suffix = st.text_input("Suffix (Jr, Sr, II, etc.)")
    update_form("prefix", prefix)
    update_form("full_name", full_name)
    update_form("dob", str(dob))
    update_form("age", calculate_age(dob))
    update_form("suffix", suffix)

elif section == "Company Details":
    company_name = st.text_input("Company Name")
    jurisdiction = st.text_input("Jurisdiction")
    registration_number = st.text_input("Company Registration Number")
    country = st.selectbox("Country", ["United Kingdom", "United States", "India"])
    address = st.text_input("Address")
    update_form("company_name", company_name)
    update_form("jurisdiction", jurisdiction)
    update_form("registration_number", registration_number)
    update_form("country", country)
    update_form("address", address)

elif section == "Financial Info":
    p1 = st.file_uploader("Upload P&L - Year 1")
    p2 = st.file_uploader("Upload P&L - Year 2")
    p3 = st.file_uploader("Upload P&L - Year 3")
    forecast = st.text_area("Forecast for next 1–3 years")
    update_form("pnl_yr1", p1.name if p1 else None)
    update_form("pnl_yr2", p2.name if p2 else None)
    update_form("pnl_yr3", p3.name if p3 else None)
    update_form("forecast", forecast)

elif section == "Sector Info":
    sector = st.selectbox("Sector", ["UK Leisure", "Retail", "Tech", "Manufacturing"])
    products = st.text_area("Key Products (comma-separated)")
    customers = st.text_area("Key Customers")
    suppliers = st.text_area("Key Suppliers")
    competitors = st.text_area("Key Competitors")
    update_form("sector", sector)
    update_form("products", products.split(","))
    update_form("customers", customers)
    update_form("suppliers", suppliers)
    update_form("competitors", competitors)

elif section == "Management & Shareholders":
    senior_mgmt = st.text_area("Senior Management Info (education/work history)")
    shareholders = st.text_area("Shareholders and percentages")
    update_form("senior_management", senior_mgmt)
    update_form("shareholders", shareholders)

elif section == "Employee Info":
    emp_count = st.number_input("Employee Count", min_value=0)
    payroll = st.text_input("Total Payroll Cost")
    mgmt_pay = st.text_input("Senior Management Compensation")
    update_form("employee_count", emp_count)
    update_form("payroll", payroll)
    update_form("management_pay", mgmt_pay)

elif section == "Submit All Business Info":
    if st.button("Submit to MongoDB"):
        if collection:
            st.session_state.form_data["timestamp"] = datetime.now()
            collection.insert_one(st.session_state.form_data)
            st.success("✔️ Submitted successfully!")
            st.dataframe(pd.DataFrame([st.session_state.form_data]))
        else:
            st.error("❌ No MongoDB connection. Check credentials.")

elif section == "Ask AI":
    question = st.text_input("Your Question:")
    if st.button("Ask"):
        if not openai.api_key:
            st.error("❌ Missing OpenAI API Key.")
        elif not collection:
            st.error("❌ MongoDB not connected.")
        else:
            records = list(collection.find().sort("timestamp", -1).limit(3))
            context = "\n".join([str(r) for r in records])
            prompt = f"Based on the records below, answer this question: {question}\n\n{context}"
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                answer = response.choices[0].message.content
                st.write("**AI Answer:**")
                st.success(answer)
            except Exception as e:
                st.error(f"OpenAI Error: {e}")
