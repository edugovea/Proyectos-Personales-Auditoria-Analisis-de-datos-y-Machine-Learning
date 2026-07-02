@echo off
chcp 65001 >nul
cd /d "C:\GitHub\Proyectos-Personales-Auditoria-Analisis-de-datos-y-Machine-Learning\05-monitor-normativo-bocba"
py -X utf8 monitor_bocba_v2.py >> "reportes_bocba\log_automatizacion.txt" 2>&1
