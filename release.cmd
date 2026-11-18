@echo off
rem Builds Pass.exe, then zips what a user needs into release\Pass-windows.zip (upload it to GitHub Releases).
cd /d "%~dp0"
call "%~dp0build.cmd" || exit /b 1
if not exist release mkdir release
powershell -NoProfile -Command "Compress-Archive -Force -DestinationPath 'release\Pass-windows.zip' -Path 'Pass.exe','Setup.cmd','Add to Send to.cmd','icon.ico','LICENSE','README.md'"
echo Done: release\Pass-windows.zip
