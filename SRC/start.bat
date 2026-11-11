@echo off
setlocal

set "PROJECT_ROOT=%~dp0.."
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" --version >nul 2>nul
    if errorlevel 1 goto python_missing
    echo Iniciando a aplicacao. O navegador sera aberto quando o servidor estiver pronto.
    "%PYTHON_EXE%" "%~dp0backend.py"
    goto finished
)

where py >nul 2>nul
if not errorlevel 1 (
    echo Iniciando a aplicacao. O navegador sera aberto quando o servidor estiver pronto.
    py -3 "%~dp0backend.py"
    goto finished
)

where python >nul 2>nul
if not errorlevel 1 (
    echo Iniciando a aplicacao. O navegador sera aberto quando o servidor estiver pronto.
    python "%~dp0backend.py"
    goto finished
)

echo Python nao foi encontrado. Instale o Python ou crie o ambiente .venv na raiz do projeto.
pause
exit /b 1

:python_missing
echo O Python do ambiente .venv nao pode ser iniciado.
echo Verifique a instalacao ou recrie o ambiente virtual.
pause
exit /b 1

:finished
if errorlevel 1 (
    echo O servidor nao conseguiu iniciar ou foi encerrado com erro.
    echo Confira se a porta 8000 ja esta em uso e tente novamente.
    pause
)
