#!/bin/bash
# run_pipeline
set -e 

echo "[1/3] Starting Static Data Import..."
python import_static_data.py

# Check if build_stops_dict.py exists before running it
if [ -f "build_stops_dict.py" ]; then
    echo "[2/3] Building Stops Dictionary..."
    python build_stops_dict.py
else
    echo "Skiping build_stops_dict.py (File not found)"
fi

echo "Setup Complete. Database is ready."

echo "[3/3] Starting Real-Time Ingestion Loop..."

exec python main.py