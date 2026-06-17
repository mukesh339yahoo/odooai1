#!/bin/bash

MODULE_PATH="/Users/shailysharma/CursorAI/odooai1/ridhira_field_security"

# Start PostgreSQL
echo "Starting PostgreSQL container..."
docker rm -f odoo_db 2>/dev/null
docker run -d -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres --name odoo_db postgres:15

# Wait for DB to be ready
echo "Waiting for database..."
sleep 10

for VERSION in "17.0" "18.0" "19.0"; do
    echo "======================================"
    echo "Testing Odoo $VERSION"
    echo "======================================"
    
    # Try to pull the image
    if ! docker pull odoo:$VERSION > /dev/null 2>&1; then
        echo "Image odoo:$VERSION not found on Docker Hub. Skipping."
        continue
    fi
    
    echo "Running tests..."
    docker run --rm --link odoo_db:db \
        -v "$MODULE_PATH":/mnt/extra-addons/ridhira_field_security \
        odoo:$VERSION \
        odoo -i ridhira_field_security --test-enable --stop-after-init -d test_${VERSION} -w odoo -r odoo > test_${VERSION}.log 2>&1
        
    if grep -q -E "FAILED|ERROR test_${VERSION}" test_${VERSION}.log; then
        echo "Tests FAILED or ERROR encountered for Odoo $VERSION"
        grep -A 2 -B 2 -E "ERROR|FAIL|Traceback" test_${VERSION}.log | head -n 20
    else
        echo "Tests PASSED for Odoo $VERSION"
        grep -E "test_.* OK|test_.* FAIL|test_.* ERROR" test_${VERSION}.log || echo "No test output found. Check log."
    fi
done

# Cleanup
echo "Cleaning up..."
docker rm -f odoo_db
