@echo off
chcp 65001 >nul
set DASHBOARD=%~dp0

python "%DASHBOARD%generate_html.py"
if errorlevel 1 (
    echo [錯誤] HTML 產生失敗
    pause
    exit /b 1
)
echo [OK] 已產生 HTML

cd /d "%DASHBOARD%"
git add .
git commit -m "update: %date:~0,10%"
git push -u origin main
if errorlevel 1 (
    echo [錯誤] git push 失敗
    pause
    exit /b 1
)
echo [OK] 已推送到 GitHub Pages
echo.
pause
