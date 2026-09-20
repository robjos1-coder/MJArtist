@echo off
rem Preview the site on this computer: double-click, then your browser opens.
cd /d "%~dp0"
python tools\build_site.py
start "" http://localhost:8000/
python -m http.server 8000 --bind 127.0.0.1
