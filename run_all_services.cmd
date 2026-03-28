@echo off
cd /d "%~dp0"

set "PY_CMD="
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PY_CMD=%LocalAppData%\Programs\Python\Python313\python.exe"
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PY_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PY_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
if not defined PY_CMD (
  where py >nul 2>nul && set "PY_CMD=py -3"
)
if not defined PY_CMD (
  where python >nul 2>nul && set "PY_CMD=python"
)
if not defined PY_CMD (
  echo [ERROR] Python not found.
  echo Install Python 3.10+ from https://www.python.org/downloads/windows/
  echo IMPORTANT: enable "Add python.exe to PATH" during install.
  pause
  exit /b 1
)

%PY_CMD% -c "import uvicorn" >nul 2>nul
if errorlevel 1 (
  echo Installing dependencies from requirements.txt...
  set "PIP_TRUSTED=--trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.tuna.tsinghua.edu.cn --trusted-host mirrors.aliyun.com"
  set "PIP_COMMON=--retries 3 --timeout 60"

  echo Trying index: https://pypi.tuna.tsinghua.edu.cn/simple
  %PY_CMD% -m pip install %PIP_COMMON% %PIP_TRUSTED% --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
  if not errorlevel 1 goto :deps_ok

  echo Trying index: https://mirrors.aliyun.com/pypi/simple/
  %PY_CMD% -m pip install %PIP_COMMON% %PIP_TRUSTED% --index-url https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
  if not errorlevel 1 goto :deps_ok

  echo Trying index: https://pypi.org/simple
  %PY_CMD% -m pip install %PIP_COMMON% %PIP_TRUSTED% --index-url https://pypi.org/simple -r requirements.txt
  if not errorlevel 1 goto :deps_ok

  echo [ERROR] Failed to install dependencies from all indexes.
  echo [HINT] Try another internet connection or VPN, then run again.
  pause
  exit /b 1
)

:deps_ok

echo Starting parser service on 127.0.0.1:8810...
start "PI Parser Service" cmd /k "%PY_CMD% -m uvicorn parser_service.main:app --host 127.0.0.1 --port 8810"

echo Starting main API on 0.0.0.0:8765...
start "PI Main API" cmd /k "%PY_CMD% -m uvicorn server.main:app --host 0.0.0.0 --port 8765"

echo Done. Check:
echo   http://127.0.0.1:8810/health
echo   http://127.0.0.1:8765/pars/api/public/status
