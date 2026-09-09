#!/bin/bash
set -euo pipefail
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=ON_ERROR_STOP=1 \
  --set=app_password="$APP_DB_PASSWORD" --set=owner_password="$OWNER_DB_PASSWORD" <<'SQL'
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE ROLE racing_owner LOGIN PASSWORD :'owner_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE racing_app LOGIN PASSWORD :'app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE SCHEMA game AUTHORIZATION racing_owner;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public, game TO racing_app;
GRANT USAGE ON SCHEMA public TO racing_owner;
SQL
