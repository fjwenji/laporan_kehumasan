@echo off
cd /d "C:\Users\syamh\magang\Project Kemenkeu\mayz_djpb_PRODUCTION_READY_v2"

if not exist logs mkdir logs

echo [%date% %time%] Starting Mayz Worker Loop >> logs\worker_startup.log

python worker\main.py >> logs\worker_loop.log 2>&1
