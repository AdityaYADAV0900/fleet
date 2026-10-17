-- ============================================================================
-- Local PostgreSQL Setup for Integrated Predictive Maintenance Platform
-- Problem Statement 26249: Air Power - Predictive Maintenance & Fleet Availability
-- ============================================================================
-- Run this script as the postgres superuser:
--   psql -U postgres -p 5432 -f database/setup_local.sql
-- (or adjust port to 5433 if your PostgreSQL 16 is configured on port 5433)

-- 1. Create Role
DO
$$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'fleetmaint') THEN
      CREATE ROLE fleetmaint WITH LOGIN PASSWORD 'fleetmaint' CREATEDB;
   ELSE
      ALTER ROLE fleetmaint WITH PASSWORD 'fleetmaint';
   END IF;
END
$$;

-- 2. Create Application Database
SELECT 'CREATE DATABASE fleetmaint OWNER fleetmaint'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'fleetmaint')\gexec

-- 3. Create Test Database
SELECT 'CREATE DATABASE fleetmaint_test OWNER fleetmaint'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'fleetmaint_test')\gexec

-- 4. Grant Permissions
GRANT ALL PRIVILEGES ON DATABASE fleetmaint TO fleetmaint;
GRANT ALL PRIVILEGES ON DATABASE fleetmaint_test TO fleetmaint;
