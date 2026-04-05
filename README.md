# The Bazaar Gate

🎮 专为绕过 Tempo Launcher 官方启动器的文件完整性校验而打造的补丁工具。

[English](README_en.md)

## 这个工具是做什么的？

Tempo Launcher 会在游戏启动前验证游戏文件的完整性。当游戏安装了模组时，文件校验会失败，导致无法使用模组启动游戏。

**这个工具的作用**：在启动游戏前自动备份模组文件、删除模组文件让校验通过、捕获游戏启动参数后恢复模组文件，让你无需每次手动备份/恢复模组。

## 功能特点

- **自动模组管理**：自动备份、删除、恢复模组文件
- **参数捕获**：从 Tempo Launcher 捕获游戏启动参数
- **多语言支持**：内置中文(zh)和英文(en)，易于扩展新语言
- **现代化界面**：简洁的扁平设计

## 下载

从 [Releases](https://github.com/YOUR_USERNAME/TheBazaarGate/releases) 页面下载最新版本。

## 使用方法

1. 解压 `TheBazaarGate.zip`
2. 运行 `TheBazaarGate.exe`
3. 设置游戏目录和启动器目录
4. 点击"启动游戏"，工具会自动完成所有操作

## 添加新语言

应用程序支持在 `language.csv` 中添加无限数量的语言列。

### 第一步：编辑 language.csv

用任何文本编辑器打开 `language.csv`，添加一个新的列，列名为语言代码。

**示例 - 添加日语 (ja)：**

```csv
key,zh,en,ja
app_title,The Bazaar Gate,The Bazaar Gate,ザ・バザール・ゲート
...
```

### 第二步：翻译所有键值

复制现有语言列并翻译所有值。应用程序将自动检测新语言列并添加到下拉菜单。

### 翻译指南

- 保持表情符号指示器（📁, 🚀, 🎮 等）的一致性
- 保持占位符位置（`{}`）用于格式字符串
- 确保换行符被保留（如需换行请用引号包裹）

## 工作原理

```
┌─────────────────────────────────────────────────────────────┐
│  1. 备份模组文件                                             │
│     - 检测游戏目录中的模组文件                                │
│     - 备份到 mod_backup/ 文件夹                              │
│     - 删除游戏目录中的模组文件                                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  2. 启动 Tempo Launcher 并捕获参数                           │
│     - 启动 Tempo Launcher                                   │
│     - 等待用户点击 PLAY                                      │
│     - 捕获游戏启动参数                                       │
│     - 关闭游戏进程                                           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  3. 恢复模组文件                                             │
│     - 将备份的模组文件恢复到游戏目录                          │
│     - 清理备份文件夹                                         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  4. 启动游戏                                                 │
│     - 使用捕获的参数启动游戏                                  │
│     - 退出启动器                                             │
└─────────────────────────────────────────────────────────────┘
```

## 配置

设置存储在可执行文件同一目录下的 `settings.txt` 中：

```json
{
  "game_path": "C:\\path\\to\\game",
  "launcher_path": "C:\\path\\to\\launcher",
  "language": "zh",
  "mod_items": ["BepInEx", "BazaarPlusPlus", "doorstop_config.ini", "winhttp.dll"]
}
```

### 模组文件配置

`mod_items` 列表定义了启动前要备份的文件/文件夹：
- 每行一个文件或文件夹名称
- 不存在的文件会自动跳过
- 同时支持文件（`.dll`）和文件夹

## 开发

### 环境要求

- Python 3.9+
- Windows 系统（使用 win32gui, psutil）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 从源码运行

```bash
python dist/launcher_tool.py
```

### 构建可执行文件

```bash
pyinstaller --clean TheBazaarGate.spec
```

输出：`dist/TheBazaarGate.exe`

## 项目结构

```
TheBazaarGate/
├── dist/
│   ├── launcher_tool.py      # 主应用程序
│   ├── language.csv           # 翻译文件
│   └── TheBazaarGate.exe    # 构建的可执行文件
├── .github/
│   ├── workflows/
│   │   └── ci.yml            # CI/CD 流水线
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md     # Bug 报告模板
│       └── feature_request.md # 功能请求模板
├── SPEC.md                   # 项目规格说明
├── README.md                  # 本文件（中文）
├── README_en.md              # 英文版本
└── CONTRIBUTING.md          # 贡献指南
```

## 贡献

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解更多详情。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。