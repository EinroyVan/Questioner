@echo off
cd /d "%~dp0"
python -m pip install -e . -q
python -m streamlit run app.py
pause
