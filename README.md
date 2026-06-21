# Muse

一个基于 Python（tkinter + pygame）的本地 MP3 播放器，支持歌词同步显示、封面展示、曲库管理、元数据编辑、音视频格式转换，并可注册为系统默认 MP3 播放程序。

> 本项目前身为 [sstnplayer](https://github.com/zjksstn/sstnplayer)，经过大幅重写后更名为 Muse。

## 功能特性

- **本地播放**：基于 `pygame.mixer` 播放 MP3，支持播放/暂停/停止/上一曲/下一曲/进度拖动/静音
- **歌词同步**：解析 `.lrc` 歌词文件，随播放进度逐行高亮显示
- **歌词下载**：集成 [LDDC](https://github.com/chenmozhijin/LDDC)（外部独立工具）一键搜索并下载精准歌词
- **封面显示**：自动提取/展示 MP3 内嵌封面
- **曲库管理**：播放列表的增删、排序（按字母/按时间）、另存为列表、断点续播（记忆上次播放位置）
- **元数据编辑**：修改单曲或整库的标题、专辑、演唱者，支持批量序列化标题、文件名格式化
- **格式转换**：单文件转换为 MP3、批量转换为 MP3、从视频中提取 MP3 音轨（依赖 FFmpeg）
- **系统集成**：可将 Muse 注册为 `.mp3` 文件的默认打开方式

## 项目结构

```
Muse/
├── muse.py              # 主程序入口
├── muse.spec            # PyInstaller 打包配置
├── v2.ico                # 程序图标
├── images/               # 界面所需图标/动画资源
├── config/                # 配置文件、控件布局、播放记录等
├── bin/                   # （需自行准备）FFmpeg 可执行文件存放目录
└── LDDC/                  # （需自行准备）LDDC 歌词工具存放目录
```

## 环境依赖

### 运行环境

- Python 3.10+（开发环境为 3.10，打包产物基于该版本）
- Windows（当前主要适配平台，部分功能如 `--register` 文件关联为 Windows 专用）

### Python 依赖

```bash
pip install pygame pillow pyperclip selenium beautifulsoup4 requests eyed3 mutagen
```

> `selenium` 需要配套的浏览器驱动（如 ChromeDriver），请确保已正确安装并配置在系统 PATH 中。

### 外部工具依赖（不随仓库提供，需自行下载）

这两个依赖体积较大且为独立的第三方工具，**不纳入本仓库版本控制**，请按需自行下载放置：

#### 1. FFmpeg（音视频转换功能需要）

任选其一：

- **方式 A（推荐）**：[下载 FFmpeg](https://ffmpeg.org/download.html) 并将其添加到系统环境变量 PATH，程序会自动检测调用
- **方式 B**：下载 `ffmpeg.exe`、`ffplay.exe`、`ffprobe.exe`，放入项目根目录下的 `bin/` 文件夹

若未配置，点击转换相关按钮时会提示「未找到 FFmpeg」，不影响播放器其他功能的使用。

#### 2. LDDC（歌词下载功能需要）

1. 前往 [LDDC Releases](https://github.com/chenmozhijin/LDDC/releases) 下载最新 Windows 绿色版（`LDDC-x.x.x-windows-amd64.zip`）
2. 解压后将整个文件夹重命名为 `LDDC`，放置在项目根目录下（与 `muse.py` 同级），确保 `LDDC/LDDC.exe` 路径存在

若未配置，歌词下载功能将无法启动，不影响播放器其他功能的使用。

## 运行方式

### 直接运行源码

```bash
python muse.py
```

### 打包为可执行程序

项目使用 PyInstaller 打包为 `--onedir` 模式（不可拆分为单文件，原因见下文）。

在项目根目录 `F:\Muse` 下打开 PowerShell：

```powershell
# 1. 确认 PyInstaller 已安装
.\.venv\Scripts\pip.exe show pyinstaller
# 未安装则执行：.\.venv\Scripts\pip.exe install pyinstaller

# 2. 一键打包（打包 + 复制资源目录，缺一不可）
.\.venv\Scripts\pyinstaller.exe --onedir --noconsole --icon=v2.ico --noconfirm muse.py; foreach ($d in 'images','config','bin','LDDC') { Copy-Item $d "dist\muse\$d" -Recurse -Force }
```

打包完成后，完整可运行的程序在 `F:\Muse\dist\muse\` 目录下。**分发或运行时，`muse.exe` 必须和 `_internal`、`images`、`config`、`bin`、`LDDC` 这些文件夹放在一起**，不可只复制 exe 单独使用。

#### 参数说明

| 参数 | 说明 |
|---|---|
| `--onedir` | 生成程序目录（exe + `_internal` 文件夹），不可拆分 |
| `--onefile` | 单文件 exe，启动慢且每次解压到临时目录，配置无法持久保存，**不推荐本项目使用** |
| `--noconsole` | 隐藏控制台窗口 |
| `--noconfirm` | 覆盖旧 `dist` 目录时不询问 |

#### 为什么要单独复制资源目录

程序通过相对路径读取 `images/`、`config/`、`bin/`、`LDDC/`，而 `muse.spec` 中 `datas=[]` 默认不打包这些资源，且每次打包 PyInstaller 的 `COLLECT` 阶段都会删除重建 `dist\muse\`，所以必须在打包后手动复制，上面的一键命令已包含这一步。

### 注册为 MP3 默认打开程序

打包并复制资源后，在 `dist\muse\` 目录下执行：

```bash
.\muse.exe --register
```

之后右键任意 `.mp3` 文件 → 打开方式 → 选择其他应用 → 选择 Muse → 勾选"始终使用此应用打开 .mp3 文件"。

取消注册：

```bash
.\muse.exe --unregister
```

## 常见问题

**1. 提示 "Failed to load Python DLL ... python3XX.dll，找不到指定的模块"**

原因：单独拿走了 `muse.exe`，丢失了同级的 `_internal` 文件夹。
解决：始终保留整个 `dist\muse\` 文件夹，不要只复制 exe。

**2. 启动闪退，或提示找不到 `widgets.json` / `v2.ico`**

原因：资源目录没有复制到 exe 旁。
解决：重新执行打包命令中的 `Copy-Item` 部分，确认 `images`、`config`、`bin`、`LDDC` 都已在 `dist\muse\` 下。

**3. 点击转换/提取 MP3 时提示找不到 FFmpeg**

参见上文「外部工具依赖」中 FFmpeg 的配置方式。

**4. 歌词下载功能无反应**

确认项目根目录下存在 `LDDC/LDDC.exe`，参见上文「外部工具依赖」中 LDDC 的配置方式。

## License

待补充
