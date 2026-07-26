import sys
import os
import re
import subprocess
import shutil
import winreg
import markdown
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextBrowser, QFrame, QMessageBox, QSplitter,
    QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

def get_base_dir():
    """获取程序运行时的根目录，支持 PyInstaller 打包后的环境"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    else:
        return os.path.dirname(os.path.abspath(__file__))

def get_refreshed_env():
    """从注册表和常规目录中实时刷新 PATH 环境变量"""
    env = os.environ.copy()
    paths = []
    
    # 1. 从 HKLM 注册表提取系统 PATH
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            sys_path, _ = winreg.QueryValueEx(key, "Path")
            paths.append(sys_path)
    except Exception:
        pass

    # 2. 从 HKCU 注册表提取用户 PATH
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            user_path, _ = winreg.QueryValueEx(key, "Path")
            paths.append(user_path)
    except Exception:
        pass

    # 3. 补充常见的 node/python 安装目录备用
    paths.extend([
        r"C:\Program Files\nodejs",
        r"C:\Program Files (x86)\nodejs",
        r"D:\Program Files\nodejs",
        r"D:\Program Files (x86)\nodejs",
        os.path.expanduser(r"~\AppData\Roaming\npm"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python311\Scripts"),
    ])
    paths.append(env.get("PATH", ""))

    # 去重并展开环境变量
    full_path_list = []
    for p in ";".join(paths).split(";"):
        p_clean = os.path.expandvars(p.strip())
        if p_clean and p_clean not in full_path_list:
            full_path_list.append(p_clean)

    env["PATH"] = ";".join(full_path_list)
    return env

def clean_yaml_val(val):
    """去除 YAML 字符串两侧的空格和双引号/单引号"""
    if not val:
        return ""
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1].strip()
    return val

def parse_yaml_header(md_text):
    """提取并解析 Markdown 头部的 YAML 元数据 (title 和 scripts 列表)"""
    data = {"title": None, "scripts": []}
    if not md_text:
        return data

    yaml_str = None
    m_code = re.search(r'```yaml\s*\n(.*?)\n```', md_text, re.DOTALL | re.IGNORECASE)
    if m_code:
        yaml_str = m_code.group(1)
    else:
        m_dash = re.search(r'^---\s*\n(.*?)\n---', md_text, re.DOTALL)
        if m_dash:
            yaml_str = m_dash.group(1)

    if not yaml_str:
        h1_m = re.search(r'^\s*#\s+(.+)$', md_text, re.MULTILINE)
        if h1_m:
            data["title"] = h1_m.group(1).strip()
        return data

    t_m = re.search(r'^\s*title:\s*(.+)$', yaml_str, re.MULTILINE | re.IGNORECASE)
    if t_m:
        data["title"] = clean_yaml_val(t_m.group(1))
    else:
        h1_m = re.search(r'^\s*#\s+(.+)$', md_text, re.MULTILINE)
        if h1_m:
            data["title"] = h1_m.group(1).strip()

    curr_script = None
    for line in yaml_str.splitlines():
        line_s = line.strip()
        if not line_s or line_s.startswith("#"):
            continue

        if line_s.startswith("-"):
            if curr_script and curr_script.get("name"):
                data["scripts"].append(curr_script)
            curr_script = {}
            line_s = line_s[1:].strip()

        if ":" in line_s:
            key, val = line_s.split(":", 1)
            key = key.strip().lower()
            val = clean_yaml_val(val)
            if key in ["name", "desc"] and curr_script is not None:
                curr_script[key] = val

    if curr_script and curr_script.get("name"):
        data["scripts"].append(curr_script)

    return data

def preprocess_github_alerts(text):
    """处理 GitHub 风格的 Alert 块引用 (如 > [!CAUTION])"""
    lines = text.splitlines()
    new_lines = []
    i = 0
    alert_map = {
        'CAUTION': ('🚨 警告', 'caution'),
        'IMPORTANT': ('❗ 重要', 'important'),
        'WARNING': ('⚠️ 注意', 'warning'),
        'NOTE': ('ℹ️ 提示', 'note'),
        'TIP': ('💡 技巧', 'tip')
    }
    
    while i < len(lines):
        line = lines[i]
        alert_match = re.match(r'^>\s*\[\!(NOTE|IMPORTANT|WARNING|CAUTION|TIP)\]', line, re.IGNORECASE)
        if alert_match:
            alert_type = alert_match.group(1).upper()
            title_text, css_class = alert_map.get(alert_type, (alert_type, alert_type.lower()))
            i += 1
            body_lines = []
            while i < len(lines) and lines[i].startswith('>'):
                cleaned_line = re.sub(r'^>\s?', '', lines[i])
                body_lines.append(cleaned_line)
                i += 1
            body_text = "<br>".join(body_lines)
            new_lines.append(f'<blockquote class="callout callout-{css_class}"><strong>{title_text}</strong><br>{body_text}</blockquote>')
        else:
            new_lines.append(line)
            i += 1
    return "\n".join(new_lines)

def render_md_to_html(md_text):
    """将 Markdown 转换为带亮色 Theme 现代 CSS 样式的富文本 HTML"""
    if not md_text:
        return '<div class="empty-notice">未找到说明文档</div>'

    cleaned_md = re.sub(r'```yaml\s*\n.*?\n```\s*\n?', '', md_text, flags=re.DOTALL | re.IGNORECASE)
    cleaned_md = re.sub(r'^---\s*\n.*?\n---\s*\n?', '', cleaned_md, flags=re.DOTALL)
    
    processed_md = preprocess_github_alerts(cleaned_md)
    
    html_body = markdown.markdown(
        processed_md,
        extensions=['fenced_code', 'tables', 'nl2br', 'sane_lists']
    )

    css_style = """
    <style>
        body {
            font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
            color: #1e293b;
            background-color: #ffffff;
            line-height: 1.6;
            margin: 10px 15px;
        }
        h1 {
            color: #0f172a;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 8px;
            font-size: 22px;
            margin-top: 10px;
        }
        h2 {
            color: #1e40af;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 5px;
            font-size: 18px;
            margin-top: 20px;
        }
        h3 {
            color: #1d4ed8;
            font-size: 15px;
            margin-top: 15px;
        }
        p {
            margin-bottom: 10px;
        }
        a {
            color: #2563eb;
            text-decoration: none;
        }
        code {
            background-color: #f1f5f9;
            color: #e11d48;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Consolas', 'Cascadia Code', monospace;
            font-size: 13px;
        }
        pre {
            background-color: #f8fafc;
            color: #0f172a;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
            font-family: 'Consolas', 'Cascadia Code', monospace;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        pre code {
            background-color: transparent;
            color: inherit;
            padding: 0;
        }
        ul, ol {
            padding-left: 24px;
            margin-bottom: 12px;
        }
        li {
            margin-bottom: 4px;
        }
        blockquote {
            border-left: 4px solid #3b82f6;
            background-color: #eff6ff;
            margin: 12px 0;
            padding: 10px 14px;
            border-radius: 0 6px 6px 0;
            color: #1e3a8a;
        }
        blockquote.callout-caution {
            border-left-color: #ef4444;
            background-color: #fef2f2;
            color: #991b1b;
        }
        blockquote.callout-important {
            border-left-color: #f59e0b;
            background-color: #fffbeb;
            color: #92400e;
        }
        blockquote.callout-warning {
            border-left-color: #eab308;
            background-color: #fefce8;
            color: #854d0e;
        }
        blockquote.callout-note {
            border-left-color: #3b82f6;
            background-color: #eff6ff;
            color: #1e40af;
        }
        blockquote.callout-tip {
            border-left-color: #10b981;
            background-color: #ecfdf5;
            color: #065f46;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }
        th, td {
            border: 1px solid #e2e8f0;
            padding: 8px 12px;
            text-align: left;
        }
        th {
            background-color: #f1f5f9;
            color: #0f172a;
        }
        tr:nth-child(even) {
            background-color: #f8fafc;
        }
        img {
            max-width: 100%;
            height: auto;
            border-radius: 6px;
        }
        .empty-notice {
            text-align: center;
            color: #64748b;
            font-size: 18px;
            margin-top: 100px;
        }
    </style>
    """
    return f"<!DOCTYPE html><html><head>{css_style}</head><body>{html_body}</body></html>"

class ScriptToolboxApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base_dir = get_base_dir()
        self.tools = []
        
        self.init_ui()
        self.scan_tools()
        self.load_tool_list()

    def init_ui(self):
        self.setWindowTitle("脚本工具箱")
        self.resize(920, 620)
        self.setMinimumSize(800, 500)

        # 中央 Splitter 分割布局
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        # ================= 左侧：项目列表面板 =================
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        lbl_left_header = QLabel("📦 项目列表")
        lbl_left_header.setStyleSheet("font-size: 15px; font-weight: bold; color: #0f172a; padding-bottom: 4px;")

        self.list_projects = QListWidget()
        self.list_projects.setObjectName("projectList")
        self.list_projects.currentRowChanged.connect(self.on_project_selected)

        left_layout.addWidget(lbl_left_header)
        left_layout.addWidget(self.list_projects)

        # ================= 右侧：脚本运行 + 说明文档面板 =================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(12)

        # 右侧顶部：项目标题 & 脚本运行按钮区
        self.top_frame = QFrame()
        self.top_frame.setObjectName("topBar")
        top_layout = QVBoxLayout(self.top_frame)
        top_layout.setContentsMargins(14, 12, 14, 12)
        top_layout.setSpacing(10)

        # 标题栏行 (包含项目名称与打开目录按钮)
        header_row = QHBoxLayout()
        self.lbl_title = QLabel("请选择项目")
        self.lbl_title.setObjectName("titleLabel")
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0f172a;")

        self.btn_open_dir = QPushButton("📁 打开目录")
        self.btn_open_dir.setObjectName("openBtn")
        self.btn_open_dir.setCursor(Qt.PointingHandCursor)
        self.btn_open_dir.clicked.connect(self.open_current_directory)

        header_row.addWidget(self.lbl_title, 1)
        header_row.addWidget(self.btn_open_dir)

        # 脚本执行按钮容器行 (动态填充)
        self.scripts_container = QWidget()
        self.scripts_layout = QHBoxLayout(self.scripts_container)
        self.scripts_layout.setContentsMargins(0, 4, 0, 0)
        self.scripts_layout.setSpacing(10)
        self.scripts_layout.setAlignment(Qt.AlignLeft)

        top_layout.addLayout(header_row)
        top_layout.addWidget(self.scripts_container)

        # 右侧下方：Markdown 说明文档渲染区
        self.md_viewer = QTextBrowser()
        self.md_viewer.setOpenExternalLinks(True)

        right_layout.addWidget(self.top_frame)
        right_layout.addWidget(self.md_viewer, 1)

        # 添加左右分割部件
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)

        # 初始分割比例: 28% 左侧, 72% 右侧
        splitter.setSizes([260, 660])

        self.apply_stylesheet()

    def apply_stylesheet(self):
        qss = """
        QMainWindow, QWidget {
            background-color: #f8fafc;
            color: #1e293b;
        }
        QSplitter::handle {
            background-color: #cbd5e1;
            width: 2px;
        }
        QFrame#topBar {
            background-color: #ffffff;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        QListWidget#projectList {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 6px;
            outline: 0px;
        }
        QListWidget#projectList::item {
            color: #334155;
            padding: 10px 14px;
            border-radius: 6px;
            margin-bottom: 4px;
            font-size: 13px;
            font-weight: 500;
        }
        QListWidget#projectList::item:hover {
            background-color: #f1f5f9;
            color: #0f172a;
        }
        QListWidget#projectList::item:selected {
            background-color: #2563eb;
            color: #ffffff;
            font-weight: bold;
        }
        QPushButton#runScriptBtn {
            background-color: #2563eb;
            color: #ffffff;
            font-weight: bold;
            font-size: 13px;
            border: none;
            border-radius: 6px;
            padding: 8px 18px;
        }
        QPushButton#runScriptBtn:hover {
            background-color: #3b82f6;
        }
        QPushButton#runScriptBtn:pressed {
            background-color: #1d4ed8;
        }
        QPushButton#openBtn {
            background-color: #f1f5f9;
            color: #475569;
            font-size: 13px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 6px 12px;
        }
        QPushButton#openBtn:hover {
            background-color: #e2e8f0;
            color: #0f172a;
        }
        QTextBrowser {
            background-color: #ffffff;
            color: #1e293b;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px;
        }
        """
        self.setStyleSheet(qss)

    def scan_tools(self):
        """扫描子目录下的批处理、PowerShell、Python 及 Node.js 脚本工具项目"""
        self.tools = []

        try:
            entries = sorted(os.listdir(self.base_dir))
        except Exception:
            entries = []

        for entry in entries:
            folder_path = os.path.join(self.base_dir, entry)
            if not os.path.isdir(folder_path) or entry.startswith('.') or entry.startswith('__') or entry.lower() in ['build', 'dist']:
                continue

            scripts_in_dir = self.get_scripts_in_dir(folder_path)
            readme_path = os.path.join(folder_path, "README.md")
            has_readme = os.path.isfile(readme_path)

            if scripts_in_dir or has_readme:
                readme_text = ""
                if has_readme:
                    try:
                        with open(readme_path, "r", encoding="utf-8") as f:
                            readme_text = f.read()
                    except Exception:
                        pass
                
                meta = parse_yaml_header(readme_text)
                title = meta["title"] if meta["title"] else entry
                scripts_list = self.combine_script_info(scripts_in_dir, meta["scripts"])

                self.tools.append({
                    "display_name": title,
                    "dir_path": folder_path,
                    "title": title,
                    "scripts": scripts_list,
                    "readme_path": readme_path if has_readme else None
                })

    def combine_script_info(self, found_files, yaml_scripts):
        """匹配并组合 YAML 中定义的脚本描述与实际存在的脚本文件"""
        result = []
        
        if yaml_scripts:
            # 当 YAML 中显式定义了 scripts 列表时，严格仅呈现 YAML 中声明的脚本
            added_files = set()
            for item in yaml_scripts:
                name = item.get("name", "")
                desc = item.get("desc", "")
                if not name:
                    continue
                matched_file = next((f for f in found_files if f.lower() == name.lower()), None)
                if matched_file and matched_file not in added_files:
                    result.append({
                        "file_name": matched_file,
                        "display_name": desc if desc else matched_file
                    })
                    added_files.add(matched_file)
        else:
            # 当 YAML 未声明 scripts 时，退回为显示目录下发现的所有可用脚本
            for file in found_files:
                result.append({
                    "file_name": file,
                    "display_name": os.path.splitext(file)[0]
                })

        return result

    def get_scripts_in_dir(self, dir_path):
        """获取指定目录下的 .bat, .ps1, .cmd, .py, .pyw, .js 脚本文件，自动排除程序自身 (main.py 等)"""
        scripts = []
        ignored_files = {'main.py', 'main.pyw', 'app.py', 'setup.py'}
        try:
            for item in sorted(os.listdir(dir_path)):
                if item.lower() in ignored_files:
                    continue
                if os.path.isfile(os.path.join(dir_path, item)):
                    ext = os.path.splitext(item)[1].lower()
                    if ext in ['.bat', '.ps1', '.cmd', '.py', '.pyw', '.js']:
                        scripts.append(item)
        except Exception:
            pass
        return scripts

    def load_tool_list(self):
        """向左侧列表填充项目"""
        self.list_projects.blockSignals(True)
        self.list_projects.clear()

        if not self.tools:
            item = QListWidgetItem("未找到任何工具或脚本")
            self.list_projects.addItem(item)
            self.lbl_title.setText("未在同目录下找到可用的脚本工具")
            self.md_viewer.setHtml(render_md_to_html(""))
            self.list_projects.blockSignals(False)
            return

        for tool in self.tools:
            item = QListWidgetItem(tool["display_name"])
            self.list_projects.addItem(item)

        self.list_projects.blockSignals(False)
        self.list_projects.setCurrentRow(0)

    def on_project_selected(self, index):
        """当用户在左侧选择项目时触发"""
        if index < 0 or index >= len(self.tools):
            return

        tool = self.tools[index]

        # 1. 更新顶部标题
        self.lbl_title.setText(f"📌 {tool['title']}")

        # 2. 清空并重新生成右侧顶部的脚本运行按钮 (仅显示 YAML 中定义的 desc 描述名称)
        while self.scripts_layout.count():
            child = self.scripts_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if tool["scripts"]:
            for script_info in tool["scripts"]:
                btn_text = f"▶ {script_info['display_name']}"
                btn = QPushButton(btn_text)
                btn.setObjectName("runScriptBtn")
                btn.setCursor(Qt.PointingHandCursor)
                
                file_name = script_info['file_name']
                dir_path = tool['dir_path']
                btn.clicked.connect(lambda checked=False, f=file_name, d=dir_path: self.run_script(d, f))
                
                self.scripts_layout.addWidget(btn)
        else:
            lbl_none = QLabel("当前项目无可用脚本文件")
            lbl_none.setStyleSheet("color: #64748b; font-size: 13px;")
            self.scripts_layout.addWidget(lbl_none)

        self.scripts_layout.addStretch(1)

        # 3. 加载并渲染 Markdown 文件
        readme_path = tool["readme_path"]
        if readme_path and os.path.isfile(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    md_text = f.read()
                html_content = render_md_to_html(md_text)
            except Exception as e:
                html_content = f'<div class="empty-notice">读取文档出错: {e}</div>'
        else:
            html_content = render_md_to_html("")

        self.md_viewer.setHtml(html_content)

    def run_script(self, dir_path, script_name):
        """直接运行指定的批处理、PowerShell、Python 或 Node.js 文件"""
        script_path = os.path.join(dir_path, script_name)
        if not os.path.exists(script_path):
            QMessageBox.critical(self, "错误", f"脚本文件不存在: {script_path}")
            return

        ext = os.path.splitext(script_name)[1].lower()
        env = get_refreshed_env()

        try:
            if ext == ".ps1":
                cmd = ["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", f".\\{script_name}"]
                subprocess.Popen(cmd, cwd=dir_path, env=env, creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif ext in [".bat", ".cmd"]:
                cmd = f'start "" cmd /k "{script_name}"'
                subprocess.Popen(cmd, cwd=dir_path, env=env, shell=True)
            elif ext in [".py", ".pyw"]:
                cmd = f'start "" cmd /k python "{script_name}"'
                subprocess.Popen(cmd, cwd=dir_path, env=env, shell=True)
            elif ext in [".js"]:
                cmd = f'start "" cmd /k node "{script_name}"'
                subprocess.Popen(cmd, cwd=dir_path, env=env, shell=True)
            else:
                QMessageBox.warning(self, "不支持的格式", f"无法直接运行 {ext} 扩展名的脚本文件。")
                return

        except Exception as e:
            QMessageBox.critical(self, "执行异常", f"启动脚本失败:\n{str(e)}")

    def open_current_directory(self):
        """在 Windows 资源管理器中打开当前脚本所在文件夹"""
        curr_index = self.list_projects.currentRow()
        if curr_index >= 0 and curr_index < len(self.tools):
            dir_path = self.tools[curr_index]["dir_path"]
            try:
                os.startfile(dir_path)
            except Exception as e:
                QMessageBox.warning(self, "提示", f"无法打开文件夹: {e}")

def main():
    # 针对 Windows 高 DPI 屏幕优化
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    window = ScriptToolboxApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
