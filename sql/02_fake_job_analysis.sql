-- =============================================================================
-- Fake Job Detection Project
-- SQL Fraud Analysis Queries
-- =============================================================================

USE fake_job_detection;

SELECT
    COUNT(*) AS total_jobs,
    SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS total_fraud_jobs,
    SUM(CASE WHEN fraudulent = 0 THEN 1 ELSE 0 END) AS total_real_jobs,
    ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
FROM job_postings;

SELECT
    COALESCE(NULLIF(TRIM(employment_type), ''), 'Not Specified') AS employment_type,
    COUNT(*) AS total_jobs,
    SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
    ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
FROM job_postings
GROUP BY COALESCE(NULLIF(TRIM(employment_type), ''), 'Not Specified')
HAVING COUNT(*) >= 20
ORDER BY fraud_rate_pct DESC, total_jobs DESC;

SELECT
    COALESCE(NULLIF(TRIM(industry), ''), 'Unknown') AS industry,
    COUNT(*) AS total_jobs,
    SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
    ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
FROM job_postings
GROUP BY COALESCE(NULLIF(TRIM(industry), ''), 'Unknown')
HAVING COUNT(*) >= 30
ORDER BY fraud_rate_pct DESC, total_jobs DESC;

SELECT
    COALESCE(NULLIF(TRIM(country), ''), 'Unknown') AS country,
    COUNT(*) AS total_jobs,
    SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
    ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
FROM job_postings
GROUP BY COALESCE(NULLIF(TRIM(country), ''), 'Unknown')
HAVING COUNT(*) >= 20
ORDER BY fraud_rate_pct DESC, total_jobs DESC;

SELECT
    CASE WHEN has_salary = 1 THEN 'Salary Disclosed' ELSE 'Salary Not Disclosed' END AS salary_status,
    COUNT(*) AS total_jobs,
    SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) AS fraud_jobs,
    ROUND(100.0 * SUM(CASE WHEN fraudulent = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS fraud_rate_pct
FROM job_postings
GROUP BY has_salary
ORDER BY fraud_rate_pct DESC;
