@echo off
title Zenith Chrome Launcher
echo ===================================================
echo   Zenith AI - Google Chrome Launcher
echo   Default User Profile
echo ===================================================
echo.

set "CHROME_BIN="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME_BIN=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME_BIN (
    if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME_BIN=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
)
if not defined CHROME_BIN (
    if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME_BIN=%LocalAppData%\Google\Chrome\Application\chrome.exe"
)

if defined CHROME_BIN (
    echo Starting Google Chrome (Default Profile)...
    start "" "%CHROME_BIN%" --no-first-run --no-default-browser-check
) else (
    start chrome --no-first-run --no-default-browser-check
)

echo Google Chrome launched with your default profile.
ping 127.0.0.1 -n 2 >nul
exit
