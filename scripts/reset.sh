#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
echo "AnimaLearn — Reset"
cd "$DIR"
python -c "from src.ingest_qdrant import delete_collection; delete_collection()" 2>/dev/null || echo "Qdrant skip"
rm -rf "$DIR/outputs/videos/"* "$DIR/outputs/trace_logs.jsonl"
mkdir -p "$DIR/outputs/videos"
python -c "from src.ingest_qdrant import ingest_corpus; ingest_corpus()" 2>/dev/null || echo "Ingest skip"
echo "✅ Reset complete! Run: streamlit run app.py"
