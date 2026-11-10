@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m streamlit run app.py --server.address localhost --browser.gatherUsageStats false
pause
