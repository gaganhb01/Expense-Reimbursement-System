@echo off
REM EMERGENCY HOT-FIX - Copy files directly into running container

echo ========================================
echo EMERGENCY HOT-FIX
echo Copying files directly into container
echo ========================================
echo.

echo Step 1: Checking if files exist locally...
if not exist "src\routes\expense.py" (
    echo ERROR: src\routes\expense.py not found!
    pause
    exit /b 1
)
if not exist "src\services\ai_service.py" (
    echo ERROR: src\services\ai_service.py not found!
    pause
    exit /b 1
)
echo ✓ Files found

echo.
echo Step 2: Copying expense.py into running container...
docker cp src\routes\expense.py expense-reimbursement-system-app-1:/app/src/routes/expense.py
if errorlevel 1 (
    echo ERROR: Failed to copy expense.py
    echo Trying alternate container name...
    docker cp src\routes\expense.py expense_app:/app/src/routes/expense.py
    if errorlevel 1 (
        echo ERROR: Failed with both container names
        echo.
        echo Please check container name with: docker ps
        pause
        exit /b 1
    )
)
echo ✓ expense.py copied

echo.
echo Step 3: Copying ai_service.py into running container...
docker cp src\services\ai_service.py expense-reimbursement-system-app-1:/app/src/services/ai_service.py
if errorlevel 1 (
    echo Trying alternate container name...
    docker cp src\services\ai_service.py expense_app:/app/src/services/ai_service.py
    if errorlevel 1 (
        echo ERROR: Failed with both container names
        pause
        exit /b 1
    )
)
echo ✓ ai_service.py copied

echo.
echo Step 4: Restarting app container...
docker-compose restart app
echo ✓ Container restarted

echo.
echo Step 5: Waiting for restart...
timeout /t 5 /nobreak

echo.
echo Step 6: Checking logs...
docker-compose logs --tail=30 app

echo.
echo ========================================
echo HOT-FIX COMPLETE!
echo ========================================
echo.
echo The files have been copied directly into the running container.
echo.
echo Now try creating an expense again at:
echo http://localhost:8000/api/docs
echo.
echo Watch logs with:
echo docker-compose logs -f app
echo.
pause