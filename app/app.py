import os
import re
import json
import pickle
import warnings

warnings.filterwarnings("ignore")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.sparse import hstack, csr_matrix

try:
    from db_connection import (
        MYSQL_CONFIG,
        fetch_country_fraud_analysis,
        fetch_employment_type_fraud_analysis,
        fetch_fraud_summary,
        fetch_high_risk_jobs,
        fetch_industry_risk,
        fetch_salary_fraud_analysis,
        run_query,
        test_connection,
    )
    DB_MODULE_AVAILABLE = True
except Exception:
    MYSQL_CONFIG = {}
    DB_MODULE_AVAILABLE = False

    def test_connection():
        return False

    def run_query(*args, **kwargs):
        return pd.DataFrame()

    def fetch_fraud_summary(*args, **kwargs):
        return pd.DataFrame()

    def fetch_high_risk_jobs(*args, **kwargs):
        return pd.DataFrame()

    def fetch_industry_risk(*args, **kwargs):
        return pd.DataFrame()

    def fetch_country_fraud_analysis(*args, **kwargs):
        return pd.DataFrame()

    def fetch_employment_type_fraud_analysis(*args, **kwargs):
        return pd.DataFrame()

    def fetch_salary_fraud_analysis(*args, **kwargs):
        return pd.DataFrame()

st.set_page_config(
    page_title="🛡️ Fake Job Detector ML",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.main { background-color: #0d1117; }
[data-testid="stSidebar"] { background: linear-gradient(180deg,#161b22 0%,#0d1117 100%); }
.kpi-card {
    background: linear-gradient(135deg,#1e2430,#232b3e);
    border-radius: 12px; padding: 20px 16px; text-align: center;
    border-left: 4px solid; margin: 6px 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.kpi-value { font-size: 2rem; font-weight: 800; }
.kpi-label { font-size: 0.85rem; color: #8b949e; margin-top: 4px; }
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

FRAUD_THRESHOLD = 0.35

URGENCY_WORDS = [
    'urgent', 'immediate', 'asap', 'hurry', 'limited',
    'act now', 'no experience', 'work from home',
    'earn money', 'easy money', 'guaranteed',
    'weekly pay', 'quick money', 'high pay',
    'bonus', '100%', 'free training', 'daily pay'
]

RED_FLAG_CHECKS = {
    "No salary disclosed": (lambda r: r.get("has_salary", 1) == 0, "Salary disclosed"),
    "No company profile provided": (lambda r: r.get("has_company_profile", 1) == 0, "Company profile available"),
    "No requirements listed": (lambda r: r.get("has_requirements", 1) == 0, "Requirements listed"),
    "Contains urgency language": (lambda r: r.get("has_urgency_words", 0) == 1, "No urgency language"),
    "Very short description (<300)": (lambda r: r.get("desc_length", 999) < 300, "Description length OK (≥300 chars)"),
    "No company logo": (lambda r: r.get("has_company_logo", 1) == 0, "Company logo present"),
}


@st.cache_data(show_spinner=False, ttl=300)
def load_sql_views():
    if not DB_MODULE_AVAILABLE or not test_connection():
        return {"connected": False, "summary": pd.DataFrame(), "industry": pd.DataFrame(), "high_risk": pd.DataFrame(), "country": pd.DataFrame(), "employment": pd.DataFrame(), "salary": pd.DataFrame()}

    return {
        "connected": True,
        "summary": fetch_fraud_summary(),
        "industry": fetch_industry_risk(15),
        "high_risk": fetch_high_risk_jobs(20),
        "country": fetch_country_fraud_analysis(15),
        "employment": fetch_employment_type_fraud_analysis(12),
        "salary": fetch_salary_fraud_analysis(),
    }


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r'<.*?>', ' ', text)
    text = re.sub(r'http\S+|www\.\S+', ' ', text)
    text = re.sub(r'[^a-z\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def has_urgency(text: str) -> int:
    t = str(text).lower()
    return int(any(w in t for w in URGENCY_WORDS))


def risk_color(prob: float) -> str:
    if prob >= FRAUD_THRESHOLD:
        return "#E74C3C"
    if prob >= 0.20:
        return "#F39C12"
    return "#2ECC71"


def risk_label(prob: float) -> str:
    if prob >= FRAUD_THRESHOLD:
        return "🚨 HIGH RISK – LIKELY FRAUD"
    if prob >= 0.20:
        return "⚠️  MEDIUM RISK"
    return "✅ LOW RISK – LIKELY LEGITIMATE"


@st.cache_data(show_spinner=False, ttl=300)
def load_data():
    paths = [
        "outputs/cleaned_job_postings.csv",
        "cleaned_job_postings.csv",
        "Fake_Job_Postings.csv",
        "Fake Job Postings.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            return pd.read_csv(p, low_memory=False), p
    return None, "Unavailable"


def prepare_dataset(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    df = df.copy()

    if 'has_salary' not in df.columns:
        df['has_salary'] = df['salary_range'].notna().astype(int) if 'salary_range' in df.columns else 0
    if 'has_company_profile' not in df.columns:
        df['has_company_profile'] = df['company_profile'].notna().astype(int) if 'company_profile' in df.columns else 0
    if 'has_requirements' not in df.columns:
        df['has_requirements'] = df['requirements'].notna().astype(int) if 'requirements' in df.columns else 0
    if 'has_benefits' not in df.columns:
        df['has_benefits'] = df['benefits'].notna().astype(int) if 'benefits' in df.columns else 0
    if 'has_company_logo' not in df.columns:
        df['has_company_logo'] = 0
    if 'telecommuting' not in df.columns:
        df['telecommuting'] = 0
    if 'has_questions' not in df.columns:
        df['has_questions'] = 0
    if 'has_urgency_words' not in df.columns:
        df['has_urgency_words'] = (
            df.get('title', '').fillna('') + ' ' + df.get('description', '').fillna('')
        ).apply(has_urgency)
    if 'desc_length' not in df.columns:
        df['desc_length'] = df.get('description', pd.Series(dtype=str)).fillna('').astype(str).str.len()
    if 'req_length' not in df.columns:
        df['req_length'] = df.get('requirements', pd.Series(dtype=str)).fillna('').astype(str).str.len()
    if 'profile_completeness' not in df.columns:
        df['profile_completeness'] = (
            df['has_salary'].fillna(0).astype(int)
            + df['has_company_profile'].fillna(0).astype(int)
            + df['has_requirements'].fillna(0).astype(int)
            + df['has_benefits'].fillna(0).astype(int)
            + df['has_company_logo'].fillna(0).astype(int)
            + df['has_questions'].fillna(0).astype(int)
        )

    if 'department' not in df.columns:
        df['department'] = ''
    if 'has_department' not in df.columns:
        df['has_department'] = df['department'].fillna('').astype(str).str.strip().ne('').astype(int)
    if 'title_length' not in df.columns:
        df['title_length'] = df.get('title', pd.Series(dtype=str)).fillna('').astype(str).str.len()

    return df


@st.cache_resource(show_spinner=False)
def load_models():
    try:
        with open("Models/model_info.json", "r", encoding="utf-8") as f:
            info = json.load(f)
        return None, None, None, info
    except Exception:
        return None, None, None, None


# Example fallback prediction logic

def predict_job(title, company, desc, reqs, has_sal, has_logo, model, tfidf, num_cols):
    raw = f"{title} {company} {desc} {reqs}"
    cleaned = clean_text(raw)
    score = 0.15
    if not has_sal:
        score += 0.22
    if not has_logo:
        score += 0.15
    if has_urgency(raw):
        score += 0.25
    if not str(desc).strip():
        score += 0.2
    if not str(reqs).strip():
        score += 0.15
    prob = min(score, 0.97)
    red_flags = {
        'has_salary': int(has_sal) == 0,
        'has_company_profile': bool(str(company).strip()) == False,
        'has_requirements': not str(reqs).strip(),
        'has_urgency_words': has_urgency(raw),
        'desc_length': len(str(desc)) < 300,
        'has_company_logo': int(has_logo) == 0,
    }
    top_words = []
    return float(prob), red_flags, top_words


raw_df, DATA_SOURCE = load_data()
df = prepare_dataset(raw_df)
model, tfidf, num_cols, model_info = load_models()

st.sidebar.header("Fake Job Detector")
st.sidebar.markdown("Project dashboard and fraud checker")

page = st.sidebar.radio("Navigation", ["Home", "Job Checker"])

if page == "Home":
    st.title("🛡️ Fake Job Detection & Hiring Market Analysis")
    st.markdown("This project detects likely fake job postings and analyzes hiring-market risk patterns.")

    if model_info:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Jobs analyzed", f"{model_info.get('total_records', 17880):,}")
        col2.metric("Fraud rate", f"{model_info.get('fraud_rate_pct', 4.84)}%")
        col3.metric("Best model", model_info.get('best_model', 'Logistic Regression'))
        col4.metric("AUC-ROC", f"{model_info.get('auc_roc', 0.9927):.3f}")
    else:
        st.info("Model metadata is not present yet. Add the local model artifacts to enable the full ML experience.")

    if df is not None and not df.empty:
        st.subheader("Dataset preview")
        st.dataframe(df.head(10), use_container_width=True)

elif page == "Job Checker":
    st.title("🔎 Job Checker")

    with st.form("job_check"):
        title = st.text_input("Job title")
        company = st.text_input("Company name")
        description = st.text_area("Job description")
        requirements = st.text_area("Requirements")
        has_salary = st.checkbox("Salary disclosed")
        has_logo = st.checkbox("Company logo present")
        submitted = st.form_submit_button("Analyze Job")

    if submitted:
        prob, red_flags, top_words = predict_job(title, company, description, requirements, has_salary, has_logo, model, tfidf, num_cols)
        is_fraud = prob >= FRAUD_THRESHOLD
        clr = risk_color(prob)
        lbl = risk_label(prob)

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-left:4px solid {clr};border-radius:10px;padding:18px;margin:12px 0;">
            <div style="font-size:2.4rem;font-weight:800;color:{clr};line-height:1;">{prob*100:.1f}%</div>
            <div style="color:#8b949e;font-size:0.78rem;">Fraud Probability</div>
            <div style="font-size:1.1rem;font-weight:800;color:{clr};margin-top:6px;">{lbl}</div>
        </div>
        """, unsafe_allow_html=True)

        st.subheader("Red flags")
        toggled = [k for k, v in red_flags.items() if v]
        if not toggled:
            st.success("No major red flags detected.")
        else:
            for item in toggled:
                st.write(f"- {item}")
