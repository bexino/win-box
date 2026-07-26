```yaml
title: "禁用笔记本键盘"
scripts:
  - name: disable.bat
    desc: 禁用笔记本键盘
  - name: enable.bat
    desc: 恢复笔记本键盘
```


# Laptop-Keyboard-Disable

> [!CAUTION]
> 已知：在部分机型上会一并禁用触控板。  
> 请知悉本工具可能带来不可预测的后果！

> [!IMPORTANT]
> 每次禁用/启用笔记本键盘都必须要重启才能生效。  
> 输入 Y 立即重启生效，**输入 N 表示你将以手动方式重启。**

此方法可用于需要把外接键盘放在笔记本上面的情况。

## 适用系统

- Windows 笔电。  
测试通过：Windows 11 x64

## 下载

下载 `Source Code.zip`  
[Release](https://github.com/beixinti/Laptop-Keyboard-Disable/releases)

## 使用

1. 解压；
2. 右键以管理员身份运行 `disable.bat` 即可禁用笔记本自带键盘;
3. 右键以管理员身份运行 `enable.bat` 即可恢复键盘使用。

## 技术细节

1. `chcp 65001`：将命令行窗口的字符编码设置为UTF-8编码，确保中文文本输出正确显示。
2. `@cd /d "%~dp0"`: 将当前目录切换到批处理文件所在的目录，`%~dp0`表示批处理文件所在的驱动器和路径。
3. `&(cacls "%SystemDrive%\\System Volume Information" >nul 2>nul)`: 尝试访问系统卷信息目录来检查当前用户是否有管理员权限。输出重定向到`nul`，表示不显示任何结果或错误。
4. `||(start "" mshta vbscript:CreateObject("Shell.Application").ShellExecute("%~nx0"," %*","","runas",1)(window.close)&exit /b)`: 如果前面的`cacls`命令失败（即当前用户没有管理员权限），则执行这个命令，它会使用VBS在管理员模式下重新启动当前的批处理文件。`exit /b`表示退出批处理文件的执行，不再继续后面的命令。
5. `sc config i8042prt start= disabled`: 将i8042prt服务的启动类型设置为“禁用”(disabled)，使系统启动时不会启动这个服务。

> i8042prt服务是Windows系统中一个系统自带的驱动程序，负责PS/2样式的键盘和鼠标设备的操作。Windows 将笔记本自带键盘视为PS/2类型键盘，所以禁用i8042prt驱动程序就能起到禁用笔记本键盘的效果。

1. `@echo off`: 关闭命令回显，只显示命令的结果，而不是命令本身。
2. `set /p choice="您想现在重启计算机吗？(Y/N): "`: 显示一条引导信息，并等待用户输入。用户的输入将被存储在变量`choice`中。
3. `if /i "%choice%"=="y" (shutdown /r /t 1)`: 如果用户输入的是`y`（由于添加了`/i`参数，所有不区分大小写），则执行括号内的命令，即使用`shutdown /r /t 1`命令立即重启计算机。其中`/r`表示重启，`/t 1`表示在1秒后执行重启。
4. `if /i "%choice%"=="n" (exit)`: 如果用户输入的是`n`（不区分大小写），则执行括号内的命令，即退出批处理文件的执行。

## 参考

笔记本自带键盘一键禁用与启动_哔哩哔哩_bilibili
