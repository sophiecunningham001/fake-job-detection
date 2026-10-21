"""
MySQL helper utilities for the Fake Job Detection project.

Architecture:
    Notebook → Clean CSV → MySQL → SQL Queries / Views → Streamlit App
"""

from __future__ import annotations

import os
import warnings
from typing import Any
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv

load_dotenv(override=False)
warnings.filterwarnings("ignore")

try:
    import mysql.connector
    MYSQL_CONNECTOR_AVAILABLE = True
except Exception:
    mysql = None
    MYSQL_CONNECTOR_AVAILABLE = False

try:
    from sqlalchemy import create_engine, text
    SQLALCHEMY_AVAILABLE = True
except Exception:
    create_engine = None
    text = None
    SQLALCHEMY_AVAILABLE = False

DEFAULT_MYSQL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "fake_job_detection",
    "port": 3306,
}


def get_mysql_config() -> dict[str, Any]:
    password = os.getenv("MYSQL_PASSWORD", "").strip()
    if not password:
        raise ValueError(
            "MYSQL_PASSWORD is not set.\n"
            "  → Add it to your .env file:  MYSQL_PASSWORD=your_password\n"
            "  → Or export in shell:        export MYSQL_PASSWORD=your_password"
        )
    return {
        "host": os.getenv("MYSQL_HOST", DEFAULT_MYSQL_CONFIG["host"]),
        "user": os.getenv("MYSQL_USER", DEFAULT_MYSQL_CONFIG["user"]),
        "password": password,
        "database": os.getenv("MYSQL_DATABASE", DEFAULT_MYSQL_CONFIG["database"]),
        "port": int(os.getenv("MYSQL_PORT", DEFAULT_MYSQL_CONFIG["port"])),
    }


try:
    MYSQL_CONFIG = get_mysql_config()
except ValueError as _cfg_err:
    print(f"[db_connection] ⚠ {_cfg_err}")
    print("[db_connection] MySQL disabled — running in CSV-only mode.")
    print("[db_connection] Fix: rename _env → .env and add MYSQL_PASSWORD")
    MYSQL_CONFIG = dict(DEFAULT_MYSQL_CONFIG)


def mysql_driver_ready() -> bool:
    return MYSQL_CONNECTOR_AVAILABLE and SQLALCHEMY_AVAILABLE


def ensure_database_exists() -> None:
    if not MYSQL_CONNECTOR_AVAILABLE:
        raise RuntimeError("mysql-connector-python is not installed.")
    cfg = get_mysql_config()
    conn = mysql.connector.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        port=cfg["port"],
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cur.close()
    finally:
        conn.close()


def get_engine():
    if not mysql_driver_ready():
        raise RuntimeError(
            "MySQL drivers missing. Run:\n"
            "  pip install mysql-connector-python sqlalchemy"
        )
    try:
        ensure_database_exists()
    except Exception as exc:
        print(f"[get_engine] ⚠ ensure_database_exists() failed: {exc}")

    cfg = get_mysql_config()
    encoded_pw = quote_plus(cfg["password"])
    url = (
        f"mysql+mysqlconnector://{cfg['user']}:{encoded_pw}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}?charset=utf8mb4"
    )
    return create_engine(url, pool_pre_ping=True)


def get_connection():
    if not MYSQL_CONNECTOR_AVAILABLE:
        raise RuntimeError("mysql-connector-python is not installed.")
    cfg = get_mysql_config()
    return mysql.connector.connect(
        host=cfg["host"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        port=cfg["port"],
        charset="utf8mb4",
        autocommit=True,
    )


def test_connection() -> bool:
    try:
        ensure_database_exists()
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS job_postings (
    job_id                INT             NOT NULL,
    title                 VARCHAR(500)    NOT NULL,
    location              VARCHAR(500),
    country               VARCHAR(200),
    department            VARCHAR(500),
    salary_range          VARCHAR(300),
    employment_type       VARCHAR(150),
    required_experience   VARCHAR(200),
    required_education    VARCHAR(200),
    industry              VARCHAR(500),
    `function`            VARCHAR(500),
    company_profile       LONGTEXT,
    description           LONGTEXT,
    requirements          LONGTEXT,
    benefits              TEXT,
    telecommuting         TINYINT(1)  DEFAULT 0,
    has_company_logo      TINYINT(1)  DEFAULT 0,
    has_questions         TINYINT(1)  DEFAULT 0,
    has_salary            TINYINT(1)  DEFAULT 0,
    has_company_profile   TINYINT(1)  DEFAULT 0,
    has_requirements      TINYINT(1)  DEFAULT 0,
    has_benefits          TINYINT(1)  DEFAULT 0,
    has_department        TINYINT(1)  DEFAULT 0,
    has_urgency_words     TINYINT(1)  DEFAULT 0,
    desc_length           INT         DEFAULT 0,
    req_length            INT         DEFAULT 0,
    title_length          INT         DEFAULT 0,
    profile_completeness  TINYINT     DEFAULT 0,
    fraudulent            TINYINT(1)  NOT NULL DEFAULT 0,
    inserted_at           DATETIME    DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (job_id)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
"""

_CREATE_INDEX_STATEMENTS = [
    "CREATE INDEX idx_fraudulent           ON job_postings (fraudulent)",
    "CREATE INDEX idx_country              ON job_postings (country)",
    "CREATE INDEX idx_industry             ON job_postings (industry)",
    "CREATE INDEX idx_employment_type      ON job_postings (employment_type)",
    "CREATE INDEX idx_profile_completeness ON job_postings (profile_completeness)",
    "CREATE INDEX idx_has_salary           ON job_postings (has_salary)",
    "CREATE INDEX idx_has_urgency          ON job_postings (has_urgency_words)",
    "CREATE INDEX idx_fraud_country        ON job_postings (fraudulent, country)",
    "CREATE INDEX idx_fraud_industry       ON job_postings (fraudulent, industry)",
]

_CREATE_VIEW_STATEMENTS = [
    """
    CREATE OR REPLACE VIEW vw_fraud_summary AS
    SELECT
        COUNT(*) AS total_jobs,
        SUM(fraudulent) AS total_fraud,
        SUM(CASE WHEN fraudulent = 0 THEN 1 ELSE 0 END) AS total_legit,
        ROUND(100.0 * SUM(fraudulent) / COUNT(*), 2) AS fraud_rate_pct,
        ROUND(AVG(CASE WHEN fraudulent = 1 THEN desc_length END), 0) AS avg_fake_desc_len,
        ROUND(AVG(CASE WHEN fraudulent = 0 THEN desc_length END), 0) AS avg_real_desc_len,
        SUM(CASE WHEN has_urgency_words = 1 AND fraudulent = 1 THEN 1 ELSE 0 END) AS urgency_fraud_count,
        SUM(CASE WHEN has_salary = 0 AND fraudulent = 1 THEN 1 ELSE 0 END) AS no_salary_fraud_count,
        ROUND(AVG(CASE WHEN fraudulent = 1 THEN profile_completeness END), 2) AS avg_fraud_completeness,
        ROUND(AVG(CASE WHEN fraudulent = 0 THEN profile_completeness END), 2) AS avg_legit_completeness
    FROM job_postings
    """,
    """
    CREATE OR REPLACE VIEW vw_high_risk_jobs AS
    SELECT
        job_id, title, country, industry, employment_type,
        CASE WHEN has_salary = 0 THEN 'Not Disclosed' ELSE 'Disclosed' END AS salary_status,
        has_urgency_words, has_company_logo, has_company_profile,
        profile_completeness,
        CASE
            WHEN has_salary = 0 AND has_company_logo = 0 AND has_urgency_words = 1 THEN 'VERY HIGH RISK'
            WHEN has_salary = 0 AND has_company_logo = 0 THEN 'HIGH RISK'
            WHEN has_salary = 0 OR has_urgency_words = 1 THEN 'MEDIUM RISK'
            ELSE 'LOW RISK'
        END AS risk_category,
        fraudulent
    FROM job_postings
    """,
    """
    CREATE OR REPLACE VIEW vw_industry_risk AS
    SELECT
        COALESCE(industry, 'Unknown') AS industry,
        COUNT(*) AS total_jobs,
        SUM(fraudulent) AS fraud_count,
        ROUND(100.0 * SUM(fraudulent) / COUNT(*), 2) AS fraud_rate_pct,
        ROUND(AVG(has_urgency_words) * 100, 1) AS urgency_word_pct,
        ROUND(AVG(profile_completeness), 2) AS avg_completeness
    FROM job_postings
    WHERE industry IS NOT NULL
    GROUP BY industry
    HAVING COUNT(*) >= 30
    """,
    """
    CREATE OR REPLACE VIEW vw_country_fraud_analysis AS
    SELECT
        COALESCE(NULLIF(TRIM(country), ''), 'Unknown') AS country,
        COUNT(*) AS total_jobs,
        SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
        ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
    FROM job_postings
    GROUP BY COALESCE(NULLIF(TRIM(country), ''), 'Unknown')
    HAVING COUNT(*) >= 20
    """,
    """
    CREATE OR REPLACE VIEW vw_employment_type_fraud_analysis AS
    SELECT
        COALESCE(NULLIF(TRIM(employment_type), ''), 'Not Specified') AS employment_type,
        COUNT(*) AS total_jobs,
        SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
        ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
    FROM job_postings
    GROUP BY COALESCE(NULLIF(TRIM(employment_type), ''), 'Not Specified')
    HAVING COUNT(*) >= 20
    """,
    """
    CREATE OR REPLACE VIEW vw_salary_fraud_analysis AS
    SELECT
        CASE WHEN has_salary = 1 THEN 'Salary Disclosed' ELSE 'Salary Not Disclosed' END AS salary_status,
        COUNT(*) AS total_jobs,
        SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
        ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
    FROM job_postings
    GROUP BY has_salary
    """,
]


def ensure_schema(verbose: bool = True) -> None:
    ensure_database_exists()
    engine = get_engine()

    with engine.begin() as conn:
        conn.execute(text(_CREATE_TABLE_SQL))

        for stmt in _CREATE_INDEX_STATEMENTS:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass

        for stmt in _CREATE_VIEW_STATEMENTS:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass

    if verbose:
        print("[ensure_schema] ✅ Ready.")


def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            rows = result.fetchall()
            return pd.DataFrame(rows, columns=list(result.keys()))
    except Exception as exc:
        print(f"[run_query] ERROR: {exc}")
        return pd.DataFrame()


def fetch_fraud_summary() -> pd.DataFrame:
    return run_query("SELECT * FROM vw_fraud_summary")


def fetch_high_risk_jobs(limit: int = 25) -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM vw_high_risk_jobs
        ORDER BY
            CASE risk_category
                WHEN 'VERY HIGH RISK' THEN 1
                WHEN 'HIGH RISK'      THEN 2
                WHEN 'MEDIUM RISK'    THEN 3
                ELSE 4
            END,
            fraudulent DESC,
            profile_completeness ASC,
            job_id ASC
        LIMIT :limit
        """,
        {"limit": int(limit)},
    )


def fetch_industry_risk(limit: int = 15) -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM vw_industry_risk
        ORDER BY fraud_rate_pct DESC, total_jobs DESC
        LIMIT :limit
        """,
        {"limit": int(limit)},
    )


def fetch_country_fraud_analysis(limit: int = 15) -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM vw_country_fraud_analysis
        ORDER BY fraud_rate_pct DESC, total_jobs DESC
        LIMIT :limit
        """,
        {"limit": int(limit)},
    )


def fetch_employment_type_fraud_analysis(limit: int = 15) -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM vw_employment_type_fraud_analysis
        ORDER BY fraud_rate_pct DESC, total_jobs DESC
        LIMIT :limit
        """,
        {"limit": int(limit)},
    )


def fetch_salary_fraud_analysis() -> pd.DataFrame:
    return run_query("SELECT * FROM vw_salary_fraud_analysis ORDER BY fraud_rate_pct DESC")


SCHEMA_COLUMNS = [
    "job_id",
    "title", "location", "country", "department",
    "salary_range", "employment_type",
    "required_experience", "required_education",
    "industry", "function",
    "company_profile", "description", "requirements", "benefits",
    "telecommuting", "has_company_logo", "has_questions",
    "has_salary", "has_company_profile", "has_requirements", "has_benefits",
    "has_department", "has_urgency_words",
    "desc_length", "req_length", "title_length",
    "profile_completeness",
    "fraudulent",
]

SCHEMA_NUMERIC_DEFAULTS = {
    "telecommuting": 0,
    "has_company_logo": 0,
    "has_questions": 0,
    "has_salary": 0,
    "has_company_profile": 0,
    "has_requirements": 0,
    "has_benefits": 0,
    "has_department": 0,
    "has_urgency_words": 0,
    "desc_length": 0,
    "req_length": 0,
    "title_length": 0,
    "profile_completeness": 0,
    "fraudulent": 0,
}

VARCHAR_LIMITS = {
    "title": 500,
    "location": 500,
    "country": 200,
    "department": 500,
    "salary_range": 300,
    "employment_type": 150,
    "required_experience": 200,
    "required_education": 200,
    "industry": 500,
    "function": 500,
}

BOOL_COLS = [
    "telecommuting", "has_company_logo", "has_questions", "fraudulent",
    "has_salary", "has_company_profile", "has_requirements",
    "has_benefits", "has_department", "has_urgency_words",
]

INT_COLS = [
    "job_id", "desc_length", "req_length", "profile_completeness", "title_length",
]


def _clean_dataframe_for_mysql(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    unknown_cols = [c for c in df.columns if c not in SCHEMA_COLUMNS]
    if unknown_cols:
        df = df.drop(columns=unknown_cols)

    for col, default in SCHEMA_NUMERIC_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default

    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    for col in INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col, max_len in VARCHAR_LIMITS.items():
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.slice(0, max_len)

    return df


def upload_csv_to_mysql(csv_path: str = "outputs/cleaned_job_postings.csv", table_name: str = "job_postings", chunksize: int = 200) -> int:
    ensure_schema(verbose=True)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found at '{csv_path}'.")

    df = pd.read_csv(csv_path, low_memory=False)
    df = _clean_dataframe_for_mysql(df)

    if "job_id" in df.columns:
        df = df.drop_duplicates(subset=["job_id"])

    safe_name = table_name.replace("`", "").strip()
    ALLOWED_TABLES = {"job_postings"}
    if safe_name not in ALLOWED_TABLES:
        raise ValueError(f"Unknown table '{safe_name}'.")
    engine = get_engine()

    with engine.begin() as conn:
        try:
            conn.execute(text(f"TRUNCATE TABLE `{safe_name}`"))
        except Exception:
            conn.execute(text(f"DELETE FROM `{safe_name}`"))

    df.to_sql(
        name=safe_name,
        con=engine,
        if_exists="append",
        index=False,
        chunksize=chunksize,
        method="multi",
    )

    with engine.connect() as conn:
        count_after = conn.execute(text(f"SELECT COUNT(*) FROM `{safe_name}`")).scalar()

    return count_after
