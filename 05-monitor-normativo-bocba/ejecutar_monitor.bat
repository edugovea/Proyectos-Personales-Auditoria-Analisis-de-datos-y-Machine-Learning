@echo off
chcp 65001 >nul
cd /d "C:\GitHub\Proyectos-Personales-Auditoria-Analisis-de-datos-y-Machine-Learning\05-monitor-normativo-bocba"
py -X utf8 monitor_bocba_v2.py 2>&1 | powershell -Command "$input | Tee-Object -FilePath 'reportes_bocba\log_ejecuciones.txt'"
pause