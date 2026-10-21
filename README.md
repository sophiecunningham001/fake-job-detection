# 🛡️ Fake Job Detection & Hiring Market Analysis

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.25+-red.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange.svg)
![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.1+-yellow.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

**An End-to-End SQL Analytics + Machine Learning Pipeline that detects fraudulent job postings and analyzes the global hiring market**

</div>

---

## 🎯 Introduction

This project combines:
- text-based fraud detection for job postings
- SQL analytics for hiring-market risk
- Streamlit dashboard and job checker
- MySQL-backed KPI layer for real-time reporting

## ✨ Features
- Real-time fake job detection scoring
- Red-flag indicators table
- EDA dashboard
- Country, industry, and employment-type risk analysis
- SQL-powered KPI views
- Streamlit app deployment ready

## 🛠️ Tech Stack
- Python 3.9+
- Pandas / NumPy / scikit-learn
- Streamlit
- Plotly
- MySQL / SQLAlchemy
- Imbalanced-learn (SMOTE)

## 📦 Project Structure

```text
fake-job-detection/
├── app/
│   ├── app.py
│   └── db_connection.py
├── sql/
│   ├── mysql_setup.sql
│   ├── 01_fake_job_schema.sql
│   ├── 02_fake_job_analysis.sql
│   └── 03_create_views_only.sql
├── Models/
│   └── model_info.json
├── .gitignore
├── requirements.txt
├── README.md
└── LICENSE
```

## 🚀 Getting Started

1. Create a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure MySQL credentials in a `.env` file
```bash
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=fake_job_detection
```

4. Run the app
```bash
streamlit run app/app.py
```

## 📁 SQL Setup

Run the schema scripts in order:
```bash
mysql -u root -p < sql/mysql_setup.sql
mysql -u root -p fake_job_detection < sql/01_fake_job_schema.sql
```

## ⚠️ Notes
- The project is designed to work with local MySQL and optional CSV fallback logic.
- Model artifacts like `.pkl` files should be added locally if you want to use the full trained ML pipeline.
- This repo includes model metadata and app code to support deployment.

## 📞 Project
This repository was created for the Fake Job Detection & Hiring Market Analysis project.
