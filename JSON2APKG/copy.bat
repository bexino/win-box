@echo off
set /p file=请拖入文件并回车: 
copy %file% "%~dp0" >nul