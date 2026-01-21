#!/bin/bash
# Seed Neo4j with sample skill graph data
# Usage: ./scripts/seed.sh

cd "$(dirname "$0")/.."

echo "Seeding Neo4j with sample data..."
uv run python scripts/seed_graph.py 2>&1 | grep -v "Received notification" | grep -v "DEPRECATION" | grep -v "WARNING" | grep -v "position=" | grep -v "classification=" | grep -v "severity=" | grep -v "diagnostic_record=" | grep -v "gql_status=" | grep -v "status_description=" | grep -v "raw_classification=" | grep -v "raw_severity=" | grep -v "OPERATION=" | grep -v "OPERATION_CODE=" | grep -v "CURRENT_SCHEMA="
