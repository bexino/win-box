@echo off
setlocal enabledelayedexpansion
title Chrome个人资料迁移工具

rem ==========================================
rem Step 1：权限校验
rem ==========================================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 权限不足！
    echo 脚本需要“管理员权限”来执行软链接创建和文件剪切操作。
    echo 请右键点击该脚本文件，选择“以管理员身份运行”。
    pause
    exit /b
)

rem ==========================================
rem Step 2：主菜单交互
rem ==========================================
:MAIN_MENU
cls
echo =======================================================
echo               Chrome 个人资料目录迁移工具
echo =======================================================
echo   1. 开始迁移Chrome个人资料 (C盘 -^> 其他盘)
echo   2. 恢复迁移 (还原至原始路径)
echo   3. 打开GitHub
echo   4. 退出脚本
echo =======================================================
set /p choice="请输入选项序号并回车 (1-4): "

if "%choice%"=="1" goto MIGRATE
if "%choice%"=="2" goto RESTORE
if "%choice%"=="3" goto GITHUB
if "%choice%"=="4" goto EXIT_SCRIPT

echo [错误] 无效的输入，请重新选择！
timeout /t 2 >nul
goto MAIN_MENU


rem ==========================================
rem Step 4：迁移逻辑 (输入1)
rem ==========================================
:MIGRATE
cls
echo =======================================================
echo                 【开始迁移Chrome个人资料】
echo =======================================================
rem 1. 自动检索路径
set "SRC_PATH=%localappdata%\Google\Chrome\User Data"

if not exist "!SRC_PATH!" (
    echo [提示] 未能自动找到默认的Chrome个人资料目录。
    echo 请打开Chrome浏览器，在地址栏输入: chrome://version/
    echo 找到“个人资料路径”，复制并粘贴到下方。
    echo -------------------------------------------------------
    set /p SRC_PATH="请输入原始User Data路径: "
    
    rem 自动去除双引号
    set SRC_PATH=!SRC_PATH:"=!
    rem 自动去除末尾可能存在的反斜杠
    if "!SRC_PATH:~-1!"=="\" set "SRC_PATH=!SRC_PATH:~0,-1!"
    rem 自动剔除末尾的 \Default
    if /i "!SRC_PATH:~-8!"=="\Default" set "SRC_PATH=!SRC_PATH:~0,-8!"

    if not exist "!SRC_PATH!" (
        echo [错误] 输入的路径不存在，请检查后重试！
        pause >nul
        goto MAIN_MENU
    )
) else (
    echo [成功] 自动检索到原路径: !SRC_PATH!
)

rem 校验是否已经是软链接
dir /al "!SRC_PATH!" >nul 2>&1
if !errorlevel! equ 0 (
    echo [错误] 检测到该路径已经是软链接，可能之前已经迁移过！
    pause >nul
    goto MAIN_MENU
)

:CHOOSE_TARGET
echo -------------------------------------------------------
echo 请选择目标路径:
echo   1. 使用默认目标路径 (D:\Program Files (x86)\Google Chrome\User Data)
echo   2. 手动输入或拖拽目标路径
echo   3. 返回主菜单
echo -------------------------------------------------------
set /p t_choice="请输入选项 (1-3): "

if "%t_choice%"=="1" (
    set "DST_PATH=D:\Program Files (x86)\Google Chrome\User Data"
    if not exist "!DST_PATH!" (
        mkdir "!DST_PATH!" 2>nul
        if !errorlevel! neq 0 (
            echo [错误] 自动创建默认目标路径失败！请尝试手动输入。
            goto MANUAL_TARGET
        )
    )
    goto DO_MIGRATE
) else if "%t_choice%"=="2" (
    goto MANUAL_TARGET
) else if "%t_choice%"=="3" (
    goto MAIN_MENU
) else (
    echo [错误] 无效选项！
    goto CHOOSE_TARGET
)

:MANUAL_TARGET
echo -------------------------------------------------------
set /p DST_PATH="请输入或拖拽目标路径 (将迁移至此目录下): "
rem 自动去除双引号和尾部斜杠
set DST_PATH=!DST_PATH:"=!
if "!DST_PATH:~-1!"=="\" set "DST_PATH=!DST_PATH:~0,-1!"

if not exist "!DST_PATH!" (
    echo [提示] 目标路径不存在，尝试自动创建...
    mkdir "!DST_PATH!" 2>nul
    if !errorlevel! neq 0 (
        echo [错误] 创建目标路径失败！请检查输入是否合法。
        pause >nul
        goto CHOOSE_TARGET
    )
)

:DO_MIGRATE
echo -------------------------------------------------------
echo 【确认信息】
echo 原始路径: !SRC_PATH!
echo 目标路径: !DST_PATH!
echo.
echo [!!! 警告 !!!] 
echo 开始迁移前，请务必彻底关闭Chrome浏览器！
echo 确保任务管理器中没有任何 chrome.exe 进程。
pause

echo.
echo 正在安全转移文件至目标路径，此过程可能需要几分钟，请耐心等待...
rem 使用 robocopy 剪切文件
robocopy "!SRC_PATH!" "!DST_PATH!" /E /MOVE /COPYALL /R:3 /W:1 /MT:16 >nul

rem 确认原目录已空并删除空壳，防止软链接创建失败
if exist "!SRC_PATH!" (
    rmdir /s /q "!SRC_PATH!" >nul 2>&1
    if exist "!SRC_PATH!" (
        echo [错误] 原始目录仍有文件无法移除！(通常因为Chrome未彻底关闭)
        echo 迁移被迫中止，但部分文件可能已移动至目标路径，请手动排查或重启电脑后重试。
        pause >nul
        goto MAIN_MENU
    )
)

echo 正在创建目录软链接 (mklink /j)...
mklink /j "!SRC_PATH!" "!DST_PATH!" >nul
if !errorlevel! neq 0 (
    echo [错误] 软链接创建失败！
    pause >nul
    goto MAIN_MENU
)

rem 生成配置文件至目标目录
echo !SRC_PATH!> "!DST_PATH!\chrome个人资料迁移.ini"

echo -------------------------------------------------------
echo [成功] Chrome 个人资料已成功迁移！
echo 软链接状态: !SRC_PATH! =^> !DST_PATH!
echo 配置文件已生成: !DST_PATH!\chrome个人资料迁移.ini
pause
goto MAIN_MENU


rem ==========================================
rem Step 3：恢复迁移逻辑 (输入2)
rem ==========================================
:RESTORE
cls
echo =======================================================
echo                 【恢复Chrome个人资料】
echo =======================================================
set "INI_FILE="
set "DEFAULT_SRC=%localappdata%\Google\Chrome\User Data"

rem 解析原始目录软链接的指向，全自动定位目标目录中的ini文件
dir /al "!DEFAULT_SRC!\.." >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=2 delims=[]" %%a in ('dir /al "!DEFAULT_SRC!\.." ^| findstr /i "User Data" ^| findstr /v "findstr"') do (
        set "TARGET_DIR=%%a"
        if exist "!TARGET_DIR!\chrome个人资料迁移.ini" (
            set "INI_FILE=!TARGET_DIR!\chrome个人资料迁移.ini"
        )
    )
)

rem 尝试保底路径
if not defined INI_FILE (
    if exist "D:\Program Files (x86)\Google Chrome\User Data\chrome个人资料迁移.ini" (
        set "INI_FILE=D:\Program Files (x86)\Google Chrome\User Data\chrome个人资料迁移.ini"
    )
)

rem 核心判断：未找到文件则报错并返回
if not exist "!INI_FILE!" (
    echo [错误] 未能找到 chrome个人资料迁移.ini 配置文件！
    echo 可能原因：软链接已被破坏，或配置文件被删除。
    pause >nul
    goto MAIN_MENU
)

rem 读取配置文件获取原始路径
set /p RESTORE_SRC=<"!INI_FILE!"

rem 提取配置文件所在目录作为目标路径
for %%I in ("!INI_FILE!") do set "RESTORE_DST=%%~dpI"
if "!RESTORE_DST:~-1!"=="\" set "RESTORE_DST=!RESTORE_DST:~0,-1!"

echo 找到配置文件！
echo 读取到原始路径: !RESTORE_SRC!
echo 解析出数据路径: !RESTORE_DST!
echo -------------------------------------------------------
echo [!!! 警告 !!!] 
echo 恢复前，请务必彻底关闭Chrome浏览器！
pause

rem 二次校验原始路径是否为软链接
dir /al "!RESTORE_SRC!" >nul 2>&1
if !errorlevel! neq 0 (
    echo [错误] 原始路径 !RESTORE_SRC! 并非软链接，无法安全恢复！
    pause >nul
    goto MAIN_MENU
)

echo.
echo 正在删除软链接...
rmdir "!RESTORE_SRC!" >nul 2>&1

echo 正在还原文件至原始路径，请耐心等待...
rem 提前删除配置文件，防止将其转移回C盘
del /f /q "!INI_FILE!" >nul 2>&1

rem 使用 robocopy 将文件剪切回去
robocopy "!RESTORE_DST!" "!RESTORE_SRC!" /E /MOVE /COPYALL /R:3 /W:1 /MT:16 >nul

rem 移除空壳目录
if exist "!RESTORE_DST!" (
    rmdir /s /q "!RESTORE_DST!" >nul 2>&1
)

echo -------------------------------------------------------
echo [成功] Chrome个人资料已彻底恢复至原始路径！
pause
goto MAIN_MENU


rem ==========================================
rem Step 5：辅助功能
rem ==========================================
:GITHUB
start https://github.com/beixinti/userdata-changer/
goto MAIN_MENU

:EXIT_SCRIPT
exit /b
