@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r "mujoco_arm_demo\desktop_requirements.txt"
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" "mujoco_arm_demo\desktop_shoulder_workspace.py"
