-- Langfuse gets its own database in the same engine so its schema never mixes
-- with DHRUVA's geofencing and vessel-track tables.
SELECT 'CREATE DATABASE langfuse'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'langfuse')\gexec
