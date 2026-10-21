-- =============================================================================
-- VIEWS ONLY — Run this when job_postings table already has data
-- =============================================================================

USE fake_job_detection;

ALTER TABLE job_postings
    MODIFY COLUMN title                VARCHAR(500)    NOT NULL,
    MODIFY COLUMN location             VARCHAR(500),
    MODIFY COLUMN country              VARCHAR(200),
    MODIFY COLUMN department           VARCHAR(500),
    MODIFY COLUMN salary_range         VARCHAR(300),
    MODIFY COLUMN employment_type      VARCHAR(150),
    MODIFY COLUMN required_experience  VARCHAR(200),
    MODIFY COLUMN required_education   VARCHAR(200),
    MODIFY COLUMN industry             VARCHAR(500),
    MODIFY COLUMN `function`           VARCHAR(500);

DROP VIEW IF EXISTS vw_salary_fraud_analysis;
DROP VIEW IF EXISTS vw_employment_type_fraud_analysis;
DROP VIEW IF EXISTS vw_country_fraud_analysis;
DROP VIEW IF EXISTS vw_fraud_summary;
DROP VIEW IF EXISTS vw_high_risk_jobs;
DROP VIEW IF EXISTS vw_industry_risk;

CREATE VIEW vw_fraud_summary AS
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
FROM job_postings;

CREATE VIEW vw_high_risk_jobs AS
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
FROM job_postings;

CREATE VIEW vw_industry_risk AS
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
HAVING COUNT(*) >= 30;

CREATE VIEW vw_country_fraud_analysis AS
SELECT
    COALESCE(NULLIF(TRIM(country), ''), 'Unknown') AS country,
    COUNT(*) AS total_jobs,
    SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
    ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
FROM job_postings
GROUP BY COALESCE(NULLIF(TRIM(country), ''), 'Unknown')
HAVING COUNT(*) >= 20;

CREATE VIEW vw_employment_type_fraud_analysis AS
SELECT
    COALESCE(NULLIF(TRIM(employment_type), ''), 'Not Specified') AS employment_type,
    COUNT(*) AS total_jobs,
    SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
    ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
FROM job_postings
GROUP BY COALESCE(NULLIF(TRIM(employment_type), ''), 'Not Specified')
HAVING COUNT(*) >= 20;

CREATE VIEW vw_salary_fraud_analysis AS
SELECT
    CASE WHEN has_salary = 1 THEN 'Salary Disclosed' ELSE 'Salary Not Disclosed' END AS salary_status,
    COUNT(*) AS total_jobs,
    SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
    ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
FROM job_postings
GROUP BY has_salary;
