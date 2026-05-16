@echo off
cd /d "%~dp0"
echo SK가스 전결 도우미 시작 중...
echo.

REM ANTHROPIC_API_KEY 확인
if "%ANTHROPIC_API_KEY%"=="" (
    echo [오류] ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.
    echo.
    echo 설정 방법: 이 창에서 아래 명령어를 실행한 뒤 다시 실행하세요.
    echo   set ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
    echo.
    pause
    exit /b 1
)

echo 브라우저에서 http://localhost:8501 이 자동으로 열립니다.
echo 종료하려면 이 창에서 Ctrl+C 를 누르세요.
echo.
C:\Users\rice2\anaconda3\python.exe -m streamlit run app.py
pause
