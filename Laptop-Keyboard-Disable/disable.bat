chcp 65001

@cd/d"%~dp0"&(cacls "%SystemDrive%\System Volume Information" >nul 2>nul)||(start "" mshta vbscript:CreateObject^("Shell.Application"^).ShellExecute^("%~nx0"," %*","","runas",1^)^(window.close^)&exit /b)
sc config i8042prt start= disabled

@echo off
set /p choice="您想现在重启计算机吗？(Y/N): "
if /i "%choice%"=="y" (shutdown /r /t 1)
if /i "%choice%"=="n" (exit)