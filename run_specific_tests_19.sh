#!/bin/bash

MODULE_PATH="/Users/shailysharma/CursorAI/odooai1/ridhira_field_security"

echo "Starting PostgreSQL container..."
docker rm -f odoo_db_19 2>/dev/null
docker run -d -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres --name odoo_db_19 postgres:15

echo "Waiting for database..."
sleep 10

echo "Running Odoo 19.0 specific tests..."
docker run --rm --link odoo_db_19:db \
    -v "$MODULE_PATH":/mnt/extra-addons/ridhira_field_security \
    odoo:19.0 \
    odoo -i ridhira_field_security --test-tags /ridhira_field_security --stop-after-init -d test_19_only -w odoo -r odoo > test_19_only.log 2>&1

echo "--- Test Output ---"
# Only show the relevant test module logs, ignore core odoo noise
grep -E "ridhira_field_security|test_.*OK|test_.*FAIL|test_.*ERROR" test_19_only.log

echo "Cleaning up..."
docker rm -f odoo_db_19
