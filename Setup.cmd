@echo off
rem One-time setup for Pass. Asks for admin (for the firewall rule), then:
rem   1. allows Pass.exe through Windows Firewall on Private networks only
rem   2. adds "Pass to phone" to right-click > Send to (via Add to Send to.cmd)
rem Safe to run again: it replaces its own rule and shortcut.
cd /d "%~dp0"

net session >nul 2>&1
if errorlevel 1 (
    echo Asking for admin rights for the firewall rule...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "EXE=%~dp0Pass.exe"
if not exist "%EXE%" (
    echo Pass.exe is missing. Run build.cmd first.
    pause
    exit /b 1
)

echo.
echo [1/2] Firewall: allow Pass on Private networks only
netsh advfirewall firewall delete rule name="Send to Phone" >nul 2>&1
netsh advfirewall firewall delete rule name="Pass" >nul 2>&1
netsh advfirewall firewall add rule name="Pass" dir=in action=allow program="%EXE%" enable=yes profile=private protocol=TCP
if errorlevel 1 (echo    Could not add the rule.) else (echo    Done.)

echo.
echo [2/2] Right-click Send to menu
call "%~dp0Add to Send to.cmd" < nul

echo.
echo All set. Open Pass.exe to start.
pause
