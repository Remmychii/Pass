@echo off
rem Builds Pass.exe (one file, icon embedded) into this folder. Needs: pip install pyinstaller pywebview segno
cd /d "%~dp0"
python -m PyInstaller --noconfirm --distpath . --onefile --windowed --name "Pass" --icon icon.ico --add-data "icon.ico;." --add-data "ui.html;." --add-data "fonts;fonts" pass_app.py
