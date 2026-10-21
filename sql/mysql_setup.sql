-- =============================================================================
-- FAKE JOB DETECTION PROJECT
-- File 0: MySQL initial setup — creates the database only.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS fake_job_detection
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE fake_job_detection;

SELECT
    SCHEMA_NAME AS database_name,
    DEFAULT_CHARACTER_SET_NAME AS charset,
    DEFAULT_COLLATION_NAME AS collation
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = 'fake_job_detection';
