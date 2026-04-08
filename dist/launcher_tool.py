"""
The Bazaar Gate - The Bazaar 启动辅助工具

该模块提供了一个图形界面工具，用于管理 The Bazaar 的模组加载流程。
主要功能包括：模组备份/恢复、启动器参数捕获、游戏启动等。

Author: The Bazaar Gate Team
Version: 1.2.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import subprocess
import time
import json
import threading
import sys
import csv
import locale
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

IS_WINDOWS = sys.platform == "win32"
psutil = None
win32gui = None

if IS_WINDOWS:
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


@dataclass
class AppConfig:
    LOG_TEXT_HEIGHT: int = 10
    MOD_FILES_TEXT_HEIGHT: int = 10
    LAUNCHER_WINDOW_TIMEOUT: int = 30
    GAME_START_TIMEOUT: int = 120
    PROCESS_CLOSE_TIMEOUT: int = 5
    WINDOW_WIDTH: int = 500
    WINDOW_HEIGHT: int = 600
    WINDOW_MIN_WIDTH: int = 450
    WINDOW_MIN_HEIGHT: int = 500
    GAME_EXE_NAME: str = "TheBazaar.exe"
    LAUNCHER_PROCESS_NAME: str = "Tempo Launcher"
    DEFAULT_MOD_ITEMS: Tuple[str, ...] = (
        "BepInEx",
        "BazaarPlusPlus",
        "doorstop_config.ini",
        "winhttp.dll",
    )


class LanguageManager:
    """
    多语言管理器，负责加载和管理应用程序的多语言翻译。

    使用单例模式确保全局只有一个语言管理器实例。
    线程安全的实现。
    """

    _instance: Optional["LanguageManager"] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls) -> "LanguageManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if LanguageManager._initialized:
            return
        with LanguageManager._lock:
            if LanguageManager._initialized:
                return
            self.current_lang: str = "zh"
            self.translations: Dict[str, Dict[str, str]] = {}
            self.language_file: str = self._get_language_path()
            self.available_languages: List[str] = []
            self._logger: logging.Logger = logging.getLogger("LanguageManager")
            self.load_language_file()
            LanguageManager._initialized = True

    def _get_language_path(self) -> str:
        """
        获取语言配置文件的路径。

        Returns:
            语言配置文件的完整路径
        """
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
            return os.path.join(base_path, "language.csv")
        return os.path.join(os.path.dirname(__file__), "language.csv")

    def load_language_file(self) -> bool:
        """
        从CSV文件加载语言翻译配置。

        Returns:
            加载成功返回True，否则返回False
        """
        if not os.path.exists(self.language_file):
            return False
        try:
            self.translations = {}
            self.available_languages = []
            with open(self.language_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                if headers and len(headers) > 1:
                    self.available_languages = [
                        lang.strip() for lang in headers[1:] if lang.strip()
                    ]
                for row in reader:
                    key = row.get("key", "").strip()
                    if key:
                        self.translations[key] = {
                            lang: row.get(lang, "").strip()
                            for lang in self.available_languages
                        }
            return True
        except (FileNotFoundError, PermissionError) as e:
            self._logger.warning(f"Language file access error: {e}")
            return False
        except csv.Error as e:
            self._logger.warning(f"CSV parse error in language file: {e}")
            return False

    def detect_system_language(self) -> str:
        """
        检测系统语言并返回匹配的可用语言代码。

        Returns:
            检测到的语言代码，默认返回'zh'
        """
        for env_var in ("LANG", "LC_ALL"):
            lang = os.environ.get(env_var, "")
            if lang:
                lang_code = lang.split(".")[0].split("_")[0].lower()
                if lang_code in self.available_languages:
                    return lang_code

        try:
            loc = locale.setlocale(locale.LC_ALL, "")
            if loc:
                lang_code = loc.split(".")[0].split("_")[0].lower()
                if lang_code in self.available_languages:
                    return lang_code
        except (locale.Error, ValueError) as e:
            self._logger.debug(f"Locale detection failed: {e}")

        return "zh"

    def t(self, key: str, default: Optional[str] = None) -> str:
        """
        获取指定键的翻译文本。

        Args:
            key: 翻译键名
            default: 默认文本，当找不到翻译时返回

        Returns:
            翻译后的文本
        """
        if key in self.translations:
            if self.current_lang in self.translations[key]:
                return self.translations[key][self.current_lang]
            if default is not None:
                return default
            for lang in self.available_languages:
                if self.translations[key].get(lang):
                    return self.translations[key][lang]
        return default if default is not None else key

    def t_format(self, key: str, *args: Any, default: Optional[str] = None) -> str:
        """
        获取翻译文本并进行格式化。

        Args:
            key: 翻译键名
            *args: 格式化参数
            default: 默认文本

        Returns:
            格式化后的翻译文本
        """
        template = self.t(key, default)
        try:
            return template.format(*args)
        except (IndexError, KeyError) as e:
            self._logger.debug(f"Translation format error for key '{key}': {e}")
            return template

    def set_language(self, lang: str) -> bool:
        """
        设置当前语言。

        Args:
            lang: 语言代码

        Returns:
            设置成功返回True，语言不可用返回False
        """
        if lang in self.available_languages:
            self.current_lang = lang
            return True
        return False

    def get_available_languages(self) -> List[str]:
        """
        获取所有可用的语言列表。

        Returns:
            可用语言代码列表
        """
        return self.available_languages.copy()


class BazaarGate:
    """
    The Bazaar Gate 主类。

    负责管理GUI界面、模组备份/恢复、启动器参数捕获和游戏启动等功能。
    """

    LOG_LEVEL_MAP: Dict[str, int] = {
        "INFO": logging.INFO,
        "SUCCESS": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "SYSTEM": logging.INFO,
        "BIGREMINDER": logging.INFO,
    }

    def __init__(self, root: tk.Tk) -> None:
        """
        初始化BazaarGate实例。

        Args:
            root: Tkinter根窗口实例
        """
        self.root = root
        self.root.geometry(f"{AppConfig.WINDOW_WIDTH}x{AppConfig.WINDOW_HEIGHT}")
        self.root.minsize(AppConfig.WINDOW_MIN_WIDTH, AppConfig.WINDOW_MIN_HEIGHT)
        self.root.resizable(True, True)

        self.app_dir: str = self._get_runtime_base_dir()
        self.default_game_path: str = self._get_default_game_path()
        self.settings_file: str = self._get_runtime_path("settings.txt")
        self.backup_folder: str = self._get_runtime_path("mod_backup")
        self.log_file: str = self._get_runtime_path("launcher.log")

        self._setup_logger()

        self.lang: LanguageManager = LanguageManager()

        saved_lang = self._load_language_setting()
        if saved_lang and saved_lang in self.lang.get_available_languages():
            self.lang.set_language(saved_lang)
        else:
            detected = self.lang.detect_system_language()
            self.lang.set_language(detected)

        self.game_path: tk.StringVar = tk.StringVar()
        self.launcher_path: tk.StringVar = tk.StringVar()
        self.mod_items: List[str] = list(AppConfig.DEFAULT_MOD_ITEMS)
        self.current_page: str = "main"

        self.main_frame: Optional[ttk.Frame] = None
        self.settings_frame: Optional[ttk.Frame] = None
        self.launcher_proc: Optional[subprocess.Popen] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._ui_lock: threading.Lock = threading.Lock()

        self._setup_ui()
        self._load_settings()
        self._apply_language()

    def _get_runtime_base_dir(self) -> str:
        """
        获取运行时文件存放目录。

        Returns:
            可执行文件或源码文件所在目录
        """
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(__file__)

    def _get_runtime_path(self, name: str) -> str:
        """
        构造运行时文件的绝对路径。

        Args:
            name: 文件或目录名称

        Returns:
            运行时文件的绝对路径
        """
        return os.path.join(self.app_dir, name)

    def _get_default_game_path(self) -> str:
        """
        获取默认游戏路径，使用环境变量动态构建。

        Returns:
            默认游戏安装路径
        """
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return os.path.join(appdata, "Tempo Launcher - Beta", "game", "buildx64")
        return ""

    def _setup_logger(self) -> None:
        """
        配置日志记录器。
        """
        self.logger = logging.getLogger("BazaarGate")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            handler = logging.FileHandler(self.log_file, encoding="utf-8", mode="w")
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        except (IOError, OSError, PermissionError) as e:
            self.logger.warning(f"Failed to setup log file: {e}")

    def _load_language_setting(self) -> Optional[str]:
        """
        从设置文件加载语言设置。

        Returns:
            保存的语言代码，未找到则返回None
        """
        try:
            settings = self._read_settings_data()
            return settings.get("language")
        except (IOError, OSError, json.JSONDecodeError) as e:
            self.logger.debug(f"Failed to load language setting: {e}")
        return None

    def _read_settings_data(self) -> Dict[str, Any]:
        """
        读取设置文件内容。

        Returns:
            设置字典，文件不存在时返回空字典
        """
        if not os.path.exists(self.settings_file):
            return {}
        with open(self.settings_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}

    def _write_settings_data(self, settings: Dict[str, Any]) -> None:
        """
        写入设置文件内容。

        Args:
            settings: 要保存的设置字典
        """
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    def _setup_styles(self) -> None:
        """
        配置UI样式。
        """
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Main.TFrame", background="#f0f2f5")
        style.configure("Card.TFrame", background="#ffffff")

        style.configure(
            "Title.TLabel",
            font=("Microsoft YaHei UI", 16, "bold"),
            background="#f0f2f5",
            foreground="#1a1a1a",
        )
        style.configure(
            "Header.TLabel",
            font=("Microsoft YaHei UI", 11, "bold"),
            background="#ffffff",
            foreground="#333333",
        )
        style.configure(
            "Label.TLabel",
            font=("Microsoft YaHei UI", 10),
            background="#ffffff",
            foreground="#555555",
        )
        style.configure(
            "Status.TLabel",
            font=("Microsoft YaHei UI", 10),
            background="#f0f2f5",
            foreground="#666666",
        )
        style.configure(
            "Hint.TLabel",
            font=("Microsoft YaHei UI", 9),
            background="#ffffff",
            foreground="#888888",
            wraplength=400,
        )

        style.configure(
            "Primary.TButton",
            font=("Microsoft YaHei UI", 10, "bold"),
            foreground="#ffffff",
            background="#0078d4",
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", "#106ebe"),
                ("pressed", "#005a9e"),
                ("disabled", "#cccccc"),
            ],
            foreground=[("disabled", "#999999")],
        )

        style.configure(
            "Secondary.TButton",
            font=("Microsoft YaHei UI", 10),
            foreground="#0078d4",
            background="#e8f4fd",
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#d0e8f9"), ("pressed", "#b8dcf0")],
        )

        style.configure(
            "Modern.TEntry",
            font=("Microsoft YaHei UI", 10),
            fieldbackground="#ffffff",
            insertcolor="#0078d4",
        )

    def _show_page(self, page_name: str) -> None:
        """
        显示指定页面。

        Args:
            page_name: 页面名称 ('main' 或 'settings')
        """
        if self.current_page == page_name:
            return
        self.current_page = page_name
        if page_name == "main":
            if self.settings_frame:
                self.settings_frame.grid_forget()
            if self.main_frame:
                self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        elif page_name == "settings":
            if self.main_frame:
                self.main_frame.grid_forget()
            if self.settings_frame is None:
                self._create_settings_page()
            self.settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self._on_show_settings_page()

    def _create_main_page(self) -> None:
        """
        创建主页面UI组件。
        """
        self.main_frame = ttk.Frame(self.root, style="Main.TFrame", padding=20)
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(
            self.main_frame, text=self.lang.t("title_with_emoji"), style="Title.TLabel"
        )
        self.title_label.grid(row=0, column=0, pady=(0, 15), sticky=tk.W)

        lang_frame = ttk.Frame(self.main_frame, style="Card.TFrame", padding=12)
        lang_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        lang_frame.configure(relief=tk.FLAT)

        self.language_label = ttk.Label(
            lang_frame,
            text=self.lang.t("language_setting_label", "🌐 语言"),
            style="Header.TLabel",
        )
        self.language_label.pack(side=tk.LEFT, padx=(0, 8))
        self.language_combo = ttk.Combobox(
            lang_frame,
            values=self.lang.get_available_languages(),
            width=6,
            state="readonly",
        )
        self.language_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.language_combo.set(self.lang.current_lang)
        self.language_combo.bind("<<ComboboxSelected>>", self._on_language_changed)

        self.settings_btn = ttk.Button(
            lang_frame,
            text=self.lang.t("open_settings", "⚙️ 捕获文件"),
            command=lambda: self._show_page("settings"),
            style="Secondary.TButton",
        )
        self.settings_btn.pack(side=tk.LEFT)

        settings_card = ttk.Frame(self.main_frame, style="Card.TFrame", padding=15)
        settings_card.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        settings_card.configure(relief=tk.FLAT)

        self.game_folder_label = ttk.Label(
            settings_card, text=self.lang.t("game_folder_label"), style="Header.TLabel"
        )
        self.game_folder_label.pack(anchor=tk.W, pady=(0, 6))

        game_path_frame = ttk.Frame(settings_card)
        game_path_frame.pack(fill=tk.X, pady=(0, 10))
        game_entry = ttk.Entry(
            game_path_frame, textvariable=self.game_path, style="Modern.TEntry"
        )
        game_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.browse_game_btn = ttk.Button(
            game_path_frame,
            text=self.lang.t("browse_button"),
            command=self._browse_game_path,
            style="Secondary.TButton",
            width=6,
        )
        self.browse_game_btn.pack(side=tk.LEFT, padx=(8, 0), ipady=3)

        self.launcher_folder_label = ttk.Label(
            settings_card,
            text=self.lang.t("launcher_folder_label"),
            style="Header.TLabel",
        )
        self.launcher_folder_label.pack(anchor=tk.W, pady=(0, 6))

        launcher_path_frame = ttk.Frame(settings_card)
        launcher_path_frame.pack(fill=tk.X)
        launcher_entry = ttk.Entry(
            launcher_path_frame, textvariable=self.launcher_path, style="Modern.TEntry"
        )
        launcher_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.browse_launcher_btn = ttk.Button(
            launcher_path_frame,
            text=self.lang.t("browse_button"),
            command=self._browse_launcher_path,
            style="Secondary.TButton",
            width=6,
        )
        self.browse_launcher_btn.pack(side=tk.LEFT, padx=(8, 0), ipady=3)

        button_card = ttk.Frame(self.main_frame, style="Card.TFrame", padding=15)
        button_card.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        button_card.configure(relief=tk.FLAT)

        self.launch_button = ttk.Button(
            button_card,
            text=self.lang.t("start_game_button"),
            command=self._start_launch_process,
            style="Primary.TButton",
        )
        self.launch_button.pack(fill=tk.X, ipady=8)

        self.status_label = ttk.Label(
            self.main_frame,
            text=self.lang.t("status_ready"),
            style="Status.TLabel",
            font=("Microsoft YaHei UI", 10),
        )
        self.status_label.grid(row=4, column=0, pady=(0, 10), sticky=tk.W)

        log_card = ttk.Frame(self.main_frame, style="Card.TFrame", padding=12)
        log_card.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        log_card.configure(relief=tk.FLAT)
        self.main_frame.rowconfigure(5, weight=1)

        self.log_card_title = ttk.Label(
            log_card, text=self.lang.t("log_frame_title"), style="Header.TLabel"
        )
        self.log_card_title.pack(anchor=tk.W, pady=(0, 8))

        log_scrollbar = ttk.Scrollbar(log_card)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 5))

        self.log_text = tk.Text(
            log_card,
            height=AppConfig.LOG_TEXT_HEIGHT,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#cccccc",
            insertbackground="#ffffff",
            yscrollcommand=log_scrollbar.set,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=8,
            pady=8,
            spacing1=2,
            spacing2=2,
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0, 5))
        log_scrollbar.config(command=self.log_text.yview)

        self.log_text.tag_config(
            "big_reminder",
            font=("Microsoft YaHei UI", 12, "bold"),
            foreground="#00ff00",
            justify="center",
        )

        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

    def _create_settings_page(self) -> None:
        """
        创建设置页面UI组件。
        """
        self.settings_frame = ttk.Frame(self.root, style="Main.TFrame", padding=20)
        self.settings_frame.columnconfigure(0, weight=1)

        title_frame = ttk.Frame(self.settings_frame, style="Main.TFrame")
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        self.back_btn = ttk.Button(
            title_frame,
            text=self.lang.t("back_btn", "⬅️ 返回"),
            command=lambda: self._show_page("main"),
            style="Secondary.TButton",
        )
        self.back_btn.pack(side=tk.LEFT, padx=(0, 15))

        self.settings_title_label = ttk.Label(
            title_frame,
            text=self.lang.t("settings_title", "📦 模组文件配置"),
            style="Title.TLabel",
        )
        self.settings_title_label.pack(side=tk.LEFT)

        config_card = ttk.Frame(self.settings_frame, style="Card.TFrame", padding=15)
        config_card.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        config_card.configure(relief=tk.FLAT)
        self.settings_frame.rowconfigure(1, weight=1)

        self.mod_files_hint = ttk.Label(
            config_card, text=self.lang.t("mod_files_hint"), style="Header.TLabel"
        )
        self.mod_files_hint.pack(anchor=tk.W, pady=(0, 8))

        self.mod_files_help = ttk.Label(
            config_card, text=self.lang.t("mod_files_help"), style="Hint.TLabel"
        )
        self.mod_files_help.pack(anchor=tk.W, pady=(0, 10))

        text_frame = tk.Frame(config_card, bg="#ffffff", relief=tk.FLAT, bd=1)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.mod_files_text = tk.Text(
            text_frame,
            height=AppConfig.MOD_FILES_TEXT_HEIGHT,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
            bg="#ffffff",
            fg="#333333",
            insertbackground="#0078d4",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self.mod_files_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        text_scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical", command=self.mod_files_text.yview
        )
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.mod_files_text.config(yscrollcommand=text_scrollbar.set)

        button_frame = ttk.Frame(config_card)
        button_frame.pack(fill=tk.X)

        self.save_settings_btn = ttk.Button(
            button_frame,
            text=self.lang.t("save_settings_btn", "💾 保存配置"),
            command=self._save_mod_settings,
            style="Primary.TButton",
        )
        self.save_settings_btn.pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 4)
        )

        self.reset_default_btn = ttk.Button(
            button_frame,
            text=self.lang.t("reset_default_btn", "🔄 恢复默认"),
            command=self._reset_to_default,
            style="Secondary.TButton",
        )
        self.reset_default_btn.pack(
            side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(4, 0)
        )

    def _on_show_settings_page(self) -> None:
        """
        显示设置页面时的回调处理。
        """
        self._load_mod_items_to_text()

    def _load_mod_items_to_text(self) -> None:
        """
        将模组项目列表加载到文本框中。
        """
        if not hasattr(self, "mod_files_text"):
            return
        self.mod_files_text.delete("1.0", tk.END)
        self.mod_files_text.insert("1.0", "\n".join(self.mod_items))

    def _reset_to_default(self) -> None:
        """
        重置模组项目为默认值。
        """
        self.mod_items = list(AppConfig.DEFAULT_MOD_ITEMS)
        self._load_mod_items_to_text()
        self.log_t("reset_default_success", level="SUCCESS")

    def _save_mod_settings(self) -> None:
        """
        保存模组设置到配置文件。
        """
        content = self.mod_files_text.get("1.0", tk.END).strip()
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        invalid_chars = '<>:"/\\|?*'
        valid_items = []
        for item in lines:
            if any(c in item for c in invalid_chars):
                self.log_t("invalid_filename", item, level="WARNING")
                continue
            valid_items.append(item)

        if valid_items:
            self.mod_items = valid_items
        else:
            self.mod_items = list(AppConfig.DEFAULT_MOD_ITEMS)

        try:
            settings = self._read_settings_data()
            settings["mod_items"] = self.mod_items
            self._write_settings_data(settings)
            self.log_t("settings_saved", level="SUCCESS")
        except (IOError, OSError, json.JSONDecodeError) as e:
            self.log_t("save_settings_failed", str(e), level="ERROR")

    def _setup_ui(self) -> None:
        """
        设置整体UI布局。
        """
        self._setup_styles()
        self.root.configure(bg="#f0f2f5")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self._create_main_page()

    def _ensure_windows_runtime_modules(self) -> bool:
        """
        按需加载运行时依赖，避免启动阶段做不必要初始化。

        Returns:
            加载成功返回 True，否则返回 False
        """
        global psutil, win32gui

        if psutil is None:
            try:
                import psutil as psutil_module
            except ImportError as e:
                self.log_t("launch_failed", str(e), level="ERROR")
                return False
            psutil = psutil_module

        if IS_WINDOWS and win32gui is None:
            try:
                import win32gui as win32gui_module
            except ImportError as e:
                self.log_t("launch_failed", str(e), level="ERROR")
                return False
            win32gui = win32gui_module

        return True

    def _apply_language_to_main_page(self) -> None:
        """
        应用语言设置到主页面。
        """
        self.title_label.config(text=self.lang.t("title_with_emoji"))
        self.game_folder_label.config(text=self.lang.t("game_folder_label"))
        self.browse_game_btn.config(text=self.lang.t("browse_button"))
        self.launcher_folder_label.config(text=self.lang.t("launcher_folder_label"))
        self.browse_launcher_btn.config(text=self.lang.t("browse_button"))
        self.launch_button.config(text=self.lang.t("start_game_button"))
        self.status_label.config(text=self.lang.t("status_ready"))
        self.log_card_title.config(text=self.lang.t("log_frame_title"))
        self.language_label.config(
            text=self.lang.t("language_setting_label", "🌐 语言")
        )
        self.settings_btn.config(text=self.lang.t("open_settings", "⚙️ 捕获文件"))

    def _apply_language_to_settings_page(self) -> None:
        """
        应用语言设置到设置页面。
        """
        if self.settings_frame is None:
            return
        self.settings_title_label.config(
            text=self.lang.t("settings_title", "📦 模组文件配置")
        )
        self.back_btn.config(text=self.lang.t("back_btn", "⬅️ 返回"))
        self.mod_files_hint.config(
            text=self.lang.t("mod_files_hint", "📝 模组文件列表:")
        )
        self.mod_files_help.config(text=self.lang.t("mod_files_help"))
        self.save_settings_btn.config(
            text=self.lang.t("save_settings_btn", "💾 保存配置")
        )
        self.reset_default_btn.config(
            text=self.lang.t("reset_default_btn", "🔄 恢复默认")
        )

    def _on_language_changed(self, event: Optional[tk.Event] = None) -> None:
        """
        语言选择变更时的回调处理。

        Args:
            event: Tkinter事件对象
        """
        selected = self.language_combo.get()
        if self.lang.set_language(selected):
            self._save_settings()
            self._apply_language()

    def log_t(
        self, key: str, *args: Any, level: str = "INFO", default: Optional[str] = None
    ) -> None:
        """
        记录翻译后的日志消息。

        Args:
            key: 翻译键名
            *args: 格式化参数
            level: 日志级别
            default: 默认文本
        """
        message = self.lang.t_format(key, *args, default=default)
        self._log_message(message, level)

    def _log_message(self, message: str, level: str = "INFO") -> None:
        """
        在UI线程中记录日志消息。

        Args:
            message: 日志消息内容
            level: 日志级别
        """
        self.root.after(0, lambda: self._do_log_message(message, level))

    def _update_log_text(self, formatted: str, level: str) -> None:
        """
        更新日志文本框内容。

        Args:
            formatted: 格式化后的日志文本
            level: 日志级别
        """
        if hasattr(self, "log_text"):
            tag = "big_reminder" if level == "BIGREMINDER" else None
            self.log_text.insert(tk.END, f"{formatted}\n", tag)
            self.log_text.see(tk.END)

    def _update_status_label(self, message: str, level: str) -> None:
        """
        更新状态标签。

        Args:
            message: 状态消息
            level: 日志级别
        """
        if not hasattr(self, "status_label"):
            return
        icons = {"ERROR": "❌", "SUCCESS": "✅", "WARNING": "⚠️", "INFO": "🔄"}
        colors = {
            "ERROR": "red",
            "SUCCESS": "green",
            "WARNING": "orange",
            "INFO": "blue",
        }
        self.status_label.config(
            text=f"{icons.get(level, '🔄')} {message}",
            foreground=colors.get(level, "blue"),
        )

    def _do_log_message(self, message: str, level: str = "INFO") -> None:
        """
        执行实际的日志记录操作。

        Args:
            message: 日志消息内容
            level: 日志级别
        """
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"

        self._update_log_text(formatted, level)
        self._update_status_label(message, level)
        self.logger.log(self.LOG_LEVEL_MAP.get(level, logging.INFO), message)

    def _show_error_dialog(self, message: str) -> None:
        """
        在主线程中显示错误对话框。

        Args:
            message: 错误消息内容
        """
        error_title = self.lang.t("error_title")
        self.root.after(0, lambda: messagebox.showerror(error_title, message))

    def _request_exit(self) -> None:
        """
        请求主线程退出应用程序。
        """
        self.root.after(0, self.root.quit)

    def log(self, message: str, level: str = "INFO") -> None:
        """
        记录日志消息的公共接口。

        Args:
            message: 日志消息内容
            level: 日志级别
        """
        self._log_message(message, level)

    def _apply_language(self) -> None:
        """
        应用语言设置到所有UI组件。
        """
        self.root.title(self.lang.t("app_title"))
        self._apply_language_to_main_page()
        self._apply_language_to_settings_page()
        self.log_t("program_started", level="INFO")
        self._check_default_paths()

    def _check_default_paths(self) -> None:
        """
        检查并设置默认路径。
        """
        if self.default_game_path and os.path.exists(
            os.path.join(self.default_game_path, AppConfig.GAME_EXE_NAME)
        ):
            if not self.game_path.get():
                self.game_path.set(self.default_game_path)
                self.log_t(
                    "detected_default_game_path",
                    self.default_game_path,
                    level="SUCCESS",
                )

    def _browse_game_path(self) -> None:
        """
        浏览并选择游戏目录。
        """
        path = filedialog.askdirectory(title=self.lang.t("select_game_dir"))
        if path:
            if os.path.exists(os.path.join(path, AppConfig.GAME_EXE_NAME)):
                self.game_path.set(path)
                self._save_settings()
                self.log_t("game_path_set", path, level="SUCCESS")
            else:
                messagebox.showerror(
                    self.lang.t("error_title"), self.lang.t("no_game_exe_error")
                )
                self.log_t("game_exe_not_found_error", level="ERROR")

    def _browse_launcher_path(self) -> None:
        """
        浏览并选择启动器目录。
        """
        path = filedialog.askdirectory(title=self.lang.t("select_launcher_dir"))
        if path:
            launcher_exe = self._find_launcher_exe(path)
            if launcher_exe:
                self.launcher_path.set(path)
                self._save_settings()
                self.log_t("launcher_path_set", path, level="SUCCESS")
                self.log_t(
                    "auto_detected", os.path.basename(launcher_exe), level="INFO"
                )
            else:
                messagebox.showerror(
                    self.lang.t("error_title"),
                    f"{self.lang.t('no_launcher_error')}\n{path}",
                )
                self.log_t("launcher_exe_not_found_error", level="ERROR")

    def _find_launcher_exe(self, launcher_dir: str) -> Optional[str]:
        """
        在指定目录中查找启动器可执行文件。

        Args:
            launcher_dir: 要搜索的目录路径

        Returns:
            找到的可执行文件完整路径，未找到返回None
        """
        if not launcher_dir or not os.path.exists(launcher_dir):
            return None
        candidates: List[str] = []
        preferred_keywords = ("launcher",)
        excluded_keywords = ("updater", "install", "crash", "helper", "service")

        for item in os.listdir(launcher_dir):
            lower_item = item.lower()
            if AppConfig.LAUNCHER_PROCESS_NAME.lower() not in lower_item:
                continue
            if not lower_item.endswith(".exe"):
                continue
            if any(keyword in lower_item for keyword in excluded_keywords):
                continue
            candidates.append(item)

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                0
                if any(keyword in item.lower() for keyword in preferred_keywords)
                else 1,
                len(item),
                item.lower(),
            )
        )
        return os.path.join(launcher_dir, candidates[0])

    def _load_settings(self) -> None:
        """
        从配置文件加载设置。
        """
        try:
            settings = self._read_settings_data()
            if not settings:
                return
            self.game_path.set(settings.get("game_path", ""))
            self.launcher_path.set(settings.get("launcher_path", ""))
            mod_items = settings.get("mod_items")
            if isinstance(mod_items, list):
                cleaned_items = [
                    item for item in mod_items if isinstance(item, str) and item.strip()
                ]
                if cleaned_items:
                    self.mod_items = cleaned_items
            self.log_t("settings_loaded", level="SYSTEM")
        except (IOError, OSError, json.JSONDecodeError) as e:
            self.log_t("load_settings_failed", str(e), level="WARNING")

    def _save_settings(self) -> None:
        """
        保存当前设置到配置文件。
        """
        try:
            settings = {
                "game_path": self.game_path.get(),
                "launcher_path": self.launcher_path.get(),
                "language": self.lang.current_lang,
                "mod_items": self.mod_items,
            }
            self._write_settings_data(settings)
        except (IOError, OSError, json.JSONDecodeError) as e:
            self.log_t("save_settings_failed", str(e), level="ERROR")

    def _get_mod_files(self, game_dir: str) -> List[str]:
        """
        获取游戏目录中存在的模组文件列表。

        Args:
            game_dir: 游戏目录路径

        Returns:
            存在的模组文件名列表
        """
        mod_files = []
        for item in self.mod_items:
            item_path = os.path.join(game_dir, item)
            if os.path.exists(item_path):
                mod_files.append(item)
                self.log_t("detected_mod", item, level="INFO")
        return mod_files

    def _copy_item(self, src: str, dst: str) -> bool:
        """
        复制文件或目录。

        Args:
            src: 源路径
            dst: 目标路径

        Returns:
            复制成功返回True，失败返回False
        """
        try:
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
            return True
        except (IOError, OSError, shutil.Error) as e:
            self.logger.error(f"Failed to copy {src} to {dst}: {e}")
            return False

    def _backup_mods(self, game_dir: str) -> bool:
        """
        备份游戏目录中的模组文件。

        Args:
            game_dir: 游戏目录路径

        Returns:
            备份成功返回True，失败返回False
        """
        mod_files = self._get_mod_files(game_dir)
        if not mod_files:
            return False

        if os.path.exists(self.backup_folder):
            shutil.rmtree(self.backup_folder)
        os.makedirs(self.backup_folder, exist_ok=True)

        self.log_t("found_mod_files", len(mod_files), level="INFO")
        for item in mod_files:
            src = os.path.join(game_dir, item)
            dst = os.path.join(self.backup_folder, item)
            if self._copy_item(src, dst):
                self.log_t("backup_success", item, level="SUCCESS")
            else:
                self.log_t("backup_failed", item, "copy failed", level="ERROR")
                return False
        return True

    def _delete_mods(self, game_dir: str) -> bool:
        """
        删除游戏目录中的模组文件。

        Args:
            game_dir: 游戏目录路径

        Returns:
            删除成功返回True，失败返回False
        """
        mod_files = self._get_mod_files(game_dir)
        for item in mod_files:
            item_path = os.path.join(game_dir, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                self.log_t("delete_success", item, level="INFO")
            except (IOError, OSError, shutil.Error) as e:
                self.log_t("delete_failed", item, str(e), level="ERROR")
                return False
        return True

    def _restore_mods(self, game_dir: str) -> bool:
        """
        从备份恢复模组文件到游戏目录。

        Args:
            game_dir: 游戏目录路径

        Returns:
            恢复成功返回True，失败返回False
        """
        if not os.path.exists(self.backup_folder):
            self.log_t("no_backup_folder", level="WARNING")
            return False
        self.log_t("restoring_mods", level="INFO")
        for item in os.listdir(self.backup_folder):
            src = os.path.join(self.backup_folder, item)
            dst = os.path.join(game_dir, item)
            if self._copy_item(src, dst):
                self.log_t("restored_success", item, level="SUCCESS")
            else:
                self.log_t("restore_failed", item, level="ERROR")
                return False
        try:
            shutil.rmtree(self.backup_folder)
            self.log_t("backup_folder_cleaned", level="SUCCESS")
        except (IOError, OSError, shutil.Error) as e:
            self.logger.warning(f"Failed to clean backup folder: {e}")
        return True

    def _find_process_by_name(self, process_name: str) -> Optional["psutil.Process"]:
        """
        根据进程名查找进程。

        Args:
            process_name: 进程名称（部分匹配）

        Returns:
            找到的进程对象，未找到返回None
        """
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                proc_name = proc.info.get("name")
                if proc_name and proc_name.lower() == process_name.lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _close_process_gracefully(self, proc: "psutil.Process") -> bool:
        """
        优雅地关闭进程。

        Args:
            proc: 要关闭的进程对象

        Returns:
            关闭成功返回True，失败返回False
        """
        try:
            proc.terminate()
            try:
                proc.wait(timeout=AppConfig.PROCESS_CLOSE_TIMEOUT)
                return True
            except psutil.TimeoutExpired:
                proc.kill()
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as e:
            self.log_t("close_process_failed", str(e), level="ERROR")
            return False

    def _show_big_reminder(self, message: str) -> None:
        """
        在日志区域显示大号提醒消息。

        Args:
            message: 提醒消息内容
        """
        self._log_message("", "INFO")
        self._log_message(message, "BIGREMINDER")
        self._log_message("", "INFO")

    def _validate_executable_path(self, exe_path: str) -> bool:
        """
        验证可执行文件路径的安全性。

        Args:
            exe_path: 可执行文件路径

        Returns:
            路径安全有效返回True，否则返回False
        """
        if not exe_path:
            return False
        try:
            abs_path = os.path.abspath(exe_path)
            if not os.path.isfile(abs_path):
                return False
            if not abs_path.lower().endswith(".exe"):
                return False
            return True
        except (OSError, ValueError):
            return False

    def _safe_launch_exe(self, exe_path: str, cwd: str) -> Optional[subprocess.Popen]:
        """
        安全地启动可执行文件。

        Args:
            exe_path: 可执行文件路径
            cwd: 工作目录

        Returns:
            启动的进程对象，失败返回None
        """
        exe_path = os.path.abspath(exe_path)
        cwd = os.path.abspath(cwd)

        if not self._validate_executable_path(exe_path):
            self.log_t("invalid_executable_path", exe_path, level="ERROR")
            return None

        if not os.path.exists(cwd):
            self.log_t("invalid_working_dir", cwd, level="ERROR")
            return None

        try:
            return subprocess.Popen([exe_path], cwd=cwd)
        except (OSError, subprocess.SubprocessError) as e:
            if getattr(e, "winerror", None) == 740:
                self.log_t(
                    "launch_requires_admin", os.path.basename(exe_path), level="ERROR"
                )
            self.log_t("launch_failed", str(e), level="ERROR")
            return None

    def _wait_for_manual_click_and_capture(self) -> Optional[List[str]]:
        """
        等待用户手动点击启动器并捕获游戏启动参数。

        Returns:
            捕获到的命令行参数列表，失败返回None
        """

        def find_launcher_window() -> Optional[int]:
            if not IS_WINDOWS:
                return None
            result: List[int] = []

            def enum_callback(hwnd: int, _: Any) -> bool:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if AppConfig.LAUNCHER_PROCESS_NAME in title:
                        result.append(hwnd)
                return True

            win32gui.EnumWindows(enum_callback, None)
            return result[0] if result else None

        self.log_t("waiting_launcher_window", level="INFO")
        hwnd = None
        for _ in range(AppConfig.LAUNCHER_WINDOW_TIMEOUT):
            hwnd = find_launcher_window()
            if hwnd:
                break
            time.sleep(1)

        if not hwnd:
            self.log_t("no_launcher_window_detected", level="WARNING")

        start_time = time.time()
        game_proc = None
        while time.time() - start_time < AppConfig.GAME_START_TIMEOUT:
            game_proc = self._find_process_by_name(AppConfig.GAME_EXE_NAME)
            if game_proc:
                break
            time.sleep(0.3)

        if not game_proc:
            raise RuntimeError(
                self.lang.t_format("timeout_no_game", AppConfig.GAME_START_TIMEOUT)
            )

        self.log_t("game_detected", game_proc.pid, level="SUCCESS")
        params: Optional[List[str]] = None
        try:
            cmd_line = game_proc.cmdline()
            if len(cmd_line) > 1:
                params = cmd_line[1:]
                self.log_t("capture_params_success", level="SUCCESS")
            else:
                raise RuntimeError(self.lang.t("cannot_get_cmdline"))
        except (psutil.NoSuchProcess, psutil.AccessDenied, IndexError) as e:
            raise RuntimeError(self.lang.t_format("capture_params_failed", str(e)))
        return params

    def _launch_game_with_params(self, params: Optional[List[str]]) -> bool:
        """
        使用捕获的参数启动游戏。

        Args:
            params: 游戏启动参数

        Returns:
            启动成功返回True，失败返回False
        """
        if not self._ensure_windows_runtime_modules():
            raise RuntimeError(self.lang.t("launcher_launch_failed"))

        game_exe = os.path.join(self.game_path.get(), AppConfig.GAME_EXE_NAME)
        if not os.path.exists(game_exe):
            raise FileNotFoundError(self.lang.t_format("game_exe_not_exists", game_exe))
        self.log_t("launching_game_with_params", level="INFO")
        try:
            cmd_args = [game_exe]
            if params:
                cmd_args.extend(params)
            subprocess.Popen(
                cmd_args,
                creationflags=subprocess.CREATE_NEW_CONSOLE if IS_WINDOWS else 0,
                cwd=self.game_path.get(),
            )
            self.log_t("game_started_success", level="SUCCESS")
            return True
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            raise RuntimeError(self.lang.t_format("launch_game_failed", str(e)))

    def _set_button_state(self, state: str) -> None:
        """
        线程安全地设置按钮状态。

        Args:
            state: 按钮状态 ('normal' 或 'disabled')
        """
        with self._ui_lock:
            self.root.after(0, lambda: self.launch_button.config(state=state))

    def _start_launch_process(self) -> None:
        """
        启动游戏启动流程的入口方法。
        """
        if not self.game_path.get():
            messagebox.showerror(
                self.lang.t("error_title"), self.lang.t("please_set_game_path")
            )
            return
        if not self.launcher_path.get():
            messagebox.showerror(
                self.lang.t("error_title"), self.lang.t("please_set_launcher_path")
            )
            return
        if not self._ensure_windows_runtime_modules():
            messagebox.showerror(
                self.lang.t("error_title"), self.lang.t("launcher_launch_failed")
            )
            return
        game_exe = os.path.join(self.game_path.get(), AppConfig.GAME_EXE_NAME)
        if not os.path.exists(game_exe):
            messagebox.showerror(
                self.lang.t("error_title"),
                self.lang.t_format("game_exe_missing", self.game_path.get()),
            )
            return
        launcher_dir = self.launcher_path.get()
        if not launcher_dir or not os.path.exists(launcher_dir):
            messagebox.showerror(
                self.lang.t("error_title"), self.lang.t("please_set_launcher_dir")
            )
            return
        if not self._find_launcher_exe(launcher_dir):
            messagebox.showerror(
                self.lang.t("error_title"),
                self.lang.t_format("launcher_not_found_in_dir", launcher_dir),
            )
            return

        self._set_button_state("disabled")
        worker_thread = threading.Thread(target=self._run_launch_process, daemon=True)
        worker_thread.start()
        self._worker_thread = worker_thread

    def _run_launch_process(self) -> None:
        """
        执行完整的游戏启动流程（在工作线程中运行）。
        """
        try:
            self.log_t("separator_line", level="SYSTEM")
            self.log_t("start_auto_process", level="SYSTEM")
            self.log_t("separator_line", level="SYSTEM")
            params: Optional[List[str]] = None

            step1_success = False
            try:
                self.log_t("step1_check_mods", level="INFO")
                mod_files = self._get_mod_files(self.game_path.get())
                if mod_files:
                    self.log_t("detected_mod_count", len(mod_files), level="INFO")
                    if self._backup_mods(self.game_path.get()):
                        if self._delete_mods(self.game_path.get()):
                            self.log_t("mods_backup_deleted", level="SUCCESS")
                            step1_success = True
                        else:
                            raise RuntimeError(self.lang.t("delete_mods_failed"))
                    else:
                        raise RuntimeError(self.lang.t("backup_mods_failed"))
                else:
                    self.log_t("no_mods_detected_skip", level="INFO")
                    step1_success = True
            except RuntimeError:
                raise
            except (OSError, shutil.Error) as e:
                self.log_t("step1_failed", str(e), level="ERROR")
                raise

            try:
                self.log_t("step2_launch_launcher", level="INFO")
                launcher_dir = self.launcher_path.get()
                launcher_exe = self._find_launcher_exe(launcher_dir)
                if not launcher_exe:
                    raise RuntimeError(
                        self.lang.t_format("launcher_not_found_in_dir", launcher_dir)
                    )
                self.log_t("launcher_dir", launcher_dir, level="INFO")
                self.log_t("launcher_exe", os.path.basename(launcher_exe), level="INFO")
                self.log_t("starting_launcher", level="INFO")

                self.launcher_proc = self._safe_launch_exe(launcher_exe, launcher_dir)
                if not self.launcher_proc:
                    raise RuntimeError(self.lang.t("launcher_launch_failed"))

                self.log_t("launcher_started", self.launcher_proc.pid, level="SUCCESS")
                self._show_big_reminder(self.lang.t("reminder_click_play"))
                params = self._wait_for_manual_click_and_capture()
                if not params:
                    raise RuntimeError(self.lang.t("cannot_get_cmdline"))
                self.log_t("got_params_success", level="SUCCESS")
                self.log_t("closing_game_process", level="INFO")
                game_proc = self._find_process_by_name(AppConfig.GAME_EXE_NAME)
                if game_proc:
                    self._close_process_gracefully(game_proc)
                    self.log_t("game_process_closed", level="SUCCESS")
                else:
                    self.log_t("no_running_game_process", level="WARNING")
                time.sleep(2)
                self.log_t("step2_complete", level="SUCCESS")
            except RuntimeError:
                raise
            except (OSError, subprocess.SubprocessError) as e:
                self.log_t("step2_failed", str(e), level="ERROR")
                raise

            try:
                self.log_t("step3_restore_mods", level="INFO")
                if step1_success and os.path.exists(self.backup_folder):
                    if self._restore_mods(self.game_path.get()):
                        self.log_t("mods_restored_success", level="SUCCESS")
                    else:
                        raise RuntimeError(self.lang.t("restore_mods_failed"))
                else:
                    self.log_t("no_need_restore_mods", level="INFO")
            except RuntimeError:
                raise
            except (OSError, shutil.Error) as e:
                self.log_t("step3_failed", str(e), level="ERROR")
                raise

            try:
                self.log_t("step4_launch_game", level="INFO")
                if self._launch_game_with_params(params):
                    self.log_t("step_separator", level="SUCCESS")
                    self.log_t("all_steps_complete", level="SUCCESS")
                    self.log_t("step_separator", level="SUCCESS")
            except (OSError, subprocess.SubprocessError, ValueError) as e:
                self.log_t("step4_launch_game", str(e), level="ERROR")
                raise

            time.sleep(1)
            self.log_t("program_will_exit", level="SYSTEM")
            self._request_exit()

        except (
            OSError,
            subprocess.SubprocessError,
            ValueError,
            RuntimeError,
            FileNotFoundError,
        ) as e:
            self.log_t("process_execute_failed", str(e), level="ERROR")
            self.log_t("trying_cleanup", level="WARNING")
            try:
                if os.path.exists(self.backup_folder):
                    self._restore_mods(self.game_path.get())
            except (OSError, shutil.Error) as cleanup_error:
                self.logger.warning(
                    f"Failed to restore mods during cleanup: {cleanup_error}"
                )
            error_msg = self.lang.t_format("process_error", str(e))
            self._set_button_state("normal")
            self._show_error_dialog(error_msg)


def main() -> None:
    """
    应用程序入口点。
    """
    root = tk.Tk()
    BazaarGate(root)
    root.mainloop()


if __name__ == "__main__":
    main()
