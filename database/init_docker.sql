-- Create test database if not exists
SELECT 'CREATE DATABASE fleetmaint_test OWNER fleetmaint'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'fleetmaint_test')\gexec
