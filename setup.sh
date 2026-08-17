#!/bin/bash
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo ""
echo "✅ Setup complete."
echo "   Run: source .venv/bin/activate"
echo "   Then: python3 anki_tool.py --help"
