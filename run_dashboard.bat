@echo off
title Zenith Dashboard
cd /d "%~dp0electron_dashboard"
if exist ".\node_modules\.bin\electron.cmd" (
  call ".\node_modules\.bin\electron.cmd" .
) else (
  call npm start
)
