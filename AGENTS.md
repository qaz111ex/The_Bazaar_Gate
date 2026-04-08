# AGENTS.md

本文件为 AI 编码代理（如 Claude Code、GitHub Copilot、Cursor 等）提供项目上下文和开发指南。

## 项目概述

**项目名称**: The Bazaar Gate  
**类型**: Windows 桌面应用程序（The Bazaar 启动辅助工具）  
**主要语言**: Python 3.9+  
**GUI 框架**: Tkinter (ttk widgets)  
**目标平台**: Windows only

### 核心功能

绕过 Tempo Launcher 的文件完整性校验，通过以下流程实现模组加载：

1. **备份模组文件** → 检测并备份游戏目录中的模组文件
2. **删除模组文件** → 删除模组文件以通过完整性校验
3. **捕获启动参数** → 启动 Tempo Launcher，捕获游戏启动参数
4. **恢复模组文件** → 将备份的模组文件恢复到游戏目录
5. **启动游戏** → 使用捕获的参数直接启动游戏

## 项目结构

```
The_Bazaar_Gate/
├── dist/
│   ├── launcher_tool.py        # 主应用程序源码（核心文件）
│   └── language.csv            # 多语言翻译文件
├── .github/
│   ├── workflows/
│   │   └── ci.yml              # CI/CD 配置
│   ├── ISSUE_TEMPLATE/         # Issue 模板
│   └── CODEOWNERS              # 代码所有者
├── build_exe.py                # PyInstaller 打包脚本
├── TheBazaarGate.spec          # PyInstaller spec 文件
├── requirements.txt            # Python 依赖
├── SPEC.md                     # 项目规格说明
├── README.md                   # 中文文档
├── README-en.md                # 英文文档
├── CONTRIBUTING.md             # 贡献指南
├── LICENSE                     # MIT 许可证
├── .gitignore                  # Git 排除配置
├── tests/
│   ├── __init__.py             # 测试包标记
│   └── test_launcher_tool.py   # 单元测试
└── AGENTS.md                   # 本文件
```

## 核心架构

### 类结构

```
AppConfig (dataclass)
├── 应用配置常量（窗口尺寸、超时时间等）

LanguageManager (singleton, thread-safe)
├── 多语言翻译管理
├── CSV 文件加载
├── 语言切换
└── 系统语言检测

BazaarGate (main class)
├── UI 构建和管理
├── 模组备份/恢复
├── 启动器参数捕获
├── 游戏启动流程
├── 设置持久化
└── Windows 依赖懒加载
```

### 关键方法

| 方法 | 功能 |
|------|------|
| `_backup_mods()` | 备份模组文件到程序目录下的 mod_backup/ |
| `_delete_mods()` | 删除游戏目录中的模组文件 |
| `_restore_mods()` | 从备份恢复模组文件 |
| `_wait_for_manual_click_and_capture()` | 捕获 Tempo Launcher 启动参数列表 |
| `_launch_game_with_params()` | 使用参数列表启动游戏 |
| `_safe_launch_exe()` | 安全启动可执行文件（含路径验证） |
| `_ensure_windows_runtime_modules()` | 按需加载 psutil / win32gui |

## 编码规范

### Python 代码风格

- **遵循 PEP 8**
- **类型注解**: 所有公共方法必须添加类型注解
- **文档字符串**: 所有类和公共方法必须有 docstring
- **异常处理**: 捕获具体异常，禁止裸露的 `except Exception:`
- **资源管理**: 使用上下文管理器 (`with` 语句)

### 命名约定

| 类型 | 风格 | 示例 |
|------|------|------|
| 类名 | PascalCase | `BazaarGate`, `LanguageManager` |
| 方法名 | snake_case | `_backup_mods()`, `load_language_file()` |
| 私有方法 | _snake_case | `_get_language_path()` |
| 常量 | UPPER_SNAKE_CASE | `LOG_TEXT_HEIGHT`, `GAME_EXE_NAME` |
| 实例变量 | snake_case | `game_path`, `launcher_path` |

### UI 文本规则

- **所有用户可见文本必须在 `language.csv` 中定义**
- **禁止硬编码 UI 字符串**
- 使用 `self.lang.t('key')` 或 `self.log_t('key')` 获取翻译
- 保持表情符号指示器的一致性

## 多语言系统

### 语言文件格式

```csv
key,zh,en,zh_Hant,ru,ko,ja
app_title,The Bazaar Gate,The Bazaar Gate,The Bazaar Gate,The Bazaar Gate,The Bazaar Gate,The Bazaar Gate
game_folder_label,📁 游戏目录,📁 Game Directory,📁 遊戲目錄,📁 Каталог гри,📁 게임 디렉토리,📁 ゲームディレクトリ
```

### 添加新语言

1. 在 `dist/language.csv` 添加新列
2. 翻译所有键值
3. 运行 `python build_exe.py` 重新打包

### 翻译键使用

```python
# 获取翻译
text = self.lang.t('game_folder_label')

# 带参数的翻译
text = self.lang.t_format('found_mod_files', count)

# 日志翻译
self.log_t('backup_success', filename, level="SUCCESS")
```

## 构建和打包

### 开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 运行源码
python dist/launcher_tool.py
```

### 打包可执行文件

```bash
python build_exe.py
```

输出: `dist/TheBazaarGate.exe`

### PyInstaller 配置要点

- **单文件模式**: `--onefile`
- **无控制台**: `--windowed`
- **嵌入资源**: `--add-data=language.csv;.`
- **资源路径**: 使用 `sys._MEIPASS` 获取嵌入资源

```python
def _get_language_path(self) -> str:
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        return os.path.join(base_path, 'language.csv')
    return os.path.join(os.path.dirname(__file__), 'language.csv')
```

运行时文件说明：

- `settings.txt`、`launcher.log`、`mod_backup/` 均保存在程序目录
- 单文件 exe 仍会受 PyInstaller 自解包影响，启动速度慢于文件夹分发属于正常现象

## 安全考虑

### 路径验证

所有外部程序执行前必须验证路径：

```python
def _validate_executable_path(self, exe_path: str) -> bool:
    if not exe_path:
        return False
    abs_path = os.path.abspath(exe_path)
    if not os.path.exists(abs_path):
        return False
    if not abs_path.lower().endswith('.exe'):
        return False
    return True
```

### 线程安全

- 单例模式使用双重检查锁定
- UI 更新使用 `root.after()` 调度到主线程
- 共享状态使用锁保护
- 后台线程不直接调用 `root.update()` 或 `sys.exit()`

## 常见任务

### 添加新的 UI 组件

1. 在 `_create_main_page()` 或 `_create_settings_page()` 中添加
2. 所有文本使用 `self.lang.t('key')`
3. 在 `language.csv` 添加翻译键
4. 更新 `_apply_language_to_*_page()` 方法

### 修改模组处理逻辑

1. 编辑 `_backup_mods()`, `_delete_mods()`, `_restore_mods()`
2. 确保异常处理完善
3. 添加适当的日志记录

### 添加新的配置项

1. 在 `AppConfig` dataclass 中添加常量
2. 在 `settings.txt` JSON 结构中添加字段
3. 更新 `_read_settings_data()`、`_write_settings_data()`、`_load_settings()` 和 `_save_settings()`

## 测试清单

- [ ] 语言切换正常工作
- [ ] 模组备份/恢复功能正常
- [ ] 启动器参数捕获正常
- [ ] 游戏启动正常
- [ ] 打包后的 exe 可独立运行
- [ ] 错误处理和用户提示正确
- [ ] 启动器目录中存在多个 Tempo 相关 exe 时，能优先选择主启动器
- [ ] 遇到 Windows 错误 740 时，日志提示明确

## 已知限制

- 仅支持 Windows 平台（依赖 win32gui, psutil）
- 需要 Tempo Launcher 已安装
- 游戏目录需要包含 TheBazaar.exe
- 单文件 exe 启动速度会受到 PyInstaller 自解包影响

## 相关文档

- [README.md](README.md) - 中文用户文档
- [README-en.md](README-en.md) - 英文用户文档
- [SPEC.md](SPEC.md) - 详细技术规格
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南

---

*本文件由 AI 代理维护，用于确保代码修改符合项目规范。*
