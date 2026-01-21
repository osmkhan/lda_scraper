#!/bin/bash

# Launch Datasette with LDA Transparency Database

DB_FILE="lda_transparency.db"
METADATA_FILE="datasette_metadata.yaml"
SETTINGS_FILE="datasette_settings.json"

# Check if database exists
if [ ! -f "$DB_FILE" ]; then
    echo "Error: Database file $DB_FILE not found!"
    echo "Please run 'python database/schema.py' first to create the database."
    exit 1
fi

# Check if datasette is installed
if ! command -v datasette &> /dev/null; then
    echo "Error: Datasette is not installed!"
    echo "Please run: pip install -r requirements.txt"
    exit 1
fi

# Launch Datasette
echo "Starting Datasette..."
echo "Open http://localhost:8001 in your browser"
echo "Press Ctrl+C to stop"
echo ""

datasette serve "$DB_FILE" \
    --metadata "$METADATA_FILE" \
    --setting settings "$SETTINGS_FILE" \
    --port 8001 \
    --host 0.0.0.0 \
    --reload \
    --cors
