#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python_path="$project_dir/.venv/bin/python"

if [ ! -x "$python_path" ]; then
    echo "RestEdge's Python environment is not available."
    echo "Create it with: python3 -m venv .venv"
    echo "Then install packages with: .venv/bin/python -m pip install -r requirements.txt"
    exit 1
fi

exec "$python_path" -m streamlit run "$project_dir/app.py"
