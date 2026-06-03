@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================
echo    个人消费管理系统 - 启动程序
echo ========================================
echo.

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

:: 安装依赖
echo [1/4] 检查依赖包...
python -m pip show starlette >nul 2>&1
if errorlevel 1 (
    echo [2/4] 安装依赖包...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

:: 创建必要目录
echo [3/4] 初始化数据目录...
if not exist "data" mkdir data
if not exist "exports" mkdir exports
if not exist "backups" mkdir backups

:: 启动后端 API 服务（后台）
echo [4/4] 启动后端 API 服务...
start "API服务" cmd /c "python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

:: 等待后端就绪
echo.
echo 正在等待后端服务启动...
for /L %%i in (1,1,10) do (
    curl -s http://127.0.0.1:8000/ >nul 2>&1
    if not errorlevel 1 (
        echo 后端已就绪！
        goto :backend_ready
    )
    timeout /t 1 >nul
)
echo 警告: 后端启动可能需要更长时间，请手动检查 http://127.0.0.1:8000

:backend_ready
echo.
echo ========================================
echo    所有准备工作已完成！
echo ========================================
echo.
echo  后端 API:  http://127.0.0.1:8000
echo  前端页面:  http://127.0.0.1:8000/frontend/index.html
echo.
echo  请在浏览器中打开前端页面查看效果
echo  关闭此窗口会停止后端服务
echo ========================================
echo.
start "" "http://127.0.0.1:8000/frontend/index.html"

:: 保持脚本运行，显示实时日志
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload --log-level info
