@echo off
chcp 65001 >nul
title SKYTICKETservice — acesso no telemóvel
cd /d "%~dp0"

echo.
echo  ================================================
echo   SKYTICKETservice — acesso no telemóvel
echo  ================================================
echo.

:: 1) Site local tem de estar a correr
echo  [1] A verificar se o site esta em http://127.0.0.1:5000 ...
powershell -NoProfile -Command "try { (Invoke-WebRequest http://127.0.0.1:5000/ -UseBasicParsing -TimeoutSec 3).StatusCode } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  echo.
  echo   O site NAO esta a correr.
  echo   Abra outro terminal e execute:  python app.py
  echo   Depois volte a correr este ficheiro.
  echo.
  pause
  exit /b 1
)
echo   OK — site activo.
echo.

:: 2) IP Wi-Fi local
echo  [2] Na MESMA Wi-Fi do PC, no browser do telemovel tente:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
  for /f "tokens=1" %%b in ("%%a") do (
    echo.
    echo      http://%%b:5000
  )
)
echo.
echo   Requisitos: PC e telemovel na MESMA Wi-Fi. Desligue dados moveis 4G/5G.
echo.

:: 3) Firewall (admin)
net session >nul 2>&1
if %errorlevel%==0 (
  echo  [3] A abrir porta 5000 na firewall...
  netsh advfirewall firewall delete rule name="SKYTICKETservice Flask 5000" >nul 2>&1
  netsh advfirewall firewall add rule name="SKYTICKETservice Flask 5000" dir=in action=allow protocol=TCP localport=5000 profile=any enable=yes >nul
  echo   Firewall OK.
) else (
  echo  [3] Firewall: se a Wi-Fi falhar, clique direito neste ficheiro
  echo      e "Executar como administrador".
)
echo.

:: 4) Tunel Cloudflare (funciona mesmo com dados moveis / router isolado)
if not exist "tools\cloudflared.exe" (
  echo  [4] cloudflared em falta em tools\ — use so o IP da Wi-Fi acima.
  echo.
  pause
  exit /b 0
)

echo  [4] A abrir link PUBLICO para o telemovel (Cloudflare)...
echo      Funciona com Wi-Fi ou dados moveis.
echo      Deixe esta janela ABERTA enquanto usa o telemovel.
echo.
tools\cloudflared.exe tunnel --url http://127.0.0.1:5000 --no-autoupdate
pause
