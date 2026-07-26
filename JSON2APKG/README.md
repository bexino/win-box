```yaml
title: "JSON转APKG"
scripts:
  - name: py-dl.bat
    desc: "1. 下载python"
  - name: genanki.bat
    desc: "2. 装依赖库"
  - name: copy.bat
    desc: "3. 导入JSON词书"
  - name: convert.py
    desc: "4. 开始转换"
```


# JSON2APKG

## 快速入门 (针对 Windows 与 MacOS)

### 第一步：打开终端并安装依赖库

前提条件：请先下载从官网 python 本体，Windows 用户需要勾选 add to PATH。

1. 打开 `终端` 或 `Terminal` 并回车，打开终端窗口。

2. 在终端中输入以下命令并回车，安装制作 Anki 词书所需的依赖库：

   MacOS：

   ```
   pip3 install genanki
   ```

   Windows：
   
   ```
   pip install genanki
   ```

### 第二步：导入词书文本

1. 把你的 .json 格式的词书拷贝到当前目录。

2. 重命名该文件为：

   `target.json`

### 第三步：生成 Anki 词书

1. 回到刚才的终端。

2. 输入命令并回车，开始制作词书：

   MacOS：

   ```
   python3 convert.py
   ```

   Windows：

   ```
   python convert.py
   ```

3. 运行完成后，你会发现在当前文件夹下成功生成了一个名为 `output.apkg` 的文件。

### 第四步：导入 Anki

双击 `output.apkg` 即可将其全量导入到你的 Anki 客户端中！
