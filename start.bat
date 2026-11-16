@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 uv。请先安装：powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  pause
  exit /b 1
)

if not exist "frontend\dist\index.html" (
  where npm >nul 2>nul
  if errorlevel 1 (
    echo [错误] 前端尚未构建，且未找到 Node.js。请安装 Node.js 20+ 后重试。
    pause
    exit /b 1
  )
  echo 首次运行：正在构建前端，大约需要 1 分钟……
  pushd frontend
  call npm install || (popd & pause & exit /b 1)
  call npm run build || (popd & pause & exit /b 1)
  popd
)

if "%STUPY_PORT%"=="" set STUPY_PORT=8765
echo.
echo 学习系统启动中：http://127.0.0.1:%STUPY_PORT%
echo 学习记录保存在 data\study.db；关闭本窗口即停止服务。
echo.
start "" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:%STUPY_PORT%"

cd backend
uv run python -m app.main
pause
