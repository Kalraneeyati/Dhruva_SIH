-- One engine for geofencing, advisory RAG and vessel tracks (see CLAUDE.md).
-- If any of these fails the image is wrong; /health/ready will say so.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS timescaledb;
