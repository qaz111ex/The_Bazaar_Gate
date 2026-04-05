import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import subprocess
import time
import json
import psutil
import ctypes
import win32gui
import threading
import sys
import csv
import locale
import logging

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass


class LanguageManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.current_lang = 'zh'
        self.translations = {}
        self.language_file = self._get_language_path()
        self.available_languages = []
        self.load_language_file()

    def _get_language_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.join(os.path.dirname(sys.executable), 'language.csv')
        return 'language.csv'

    def load_language_file(self):
        if not os.path.exists(self.language_file):
            return False
        try:
            self.translations = {}
            self.available_languages = []
            with open(self.language_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames
                if headers and len(headers) > 1:
                    self.available_languages = [lang.strip() for lang in headers[1:] if lang.strip()]
                for row in reader:
                    key = row.get('key', '').strip()
                    if key:
                        self.translations[key] = {lang: row.get(lang, '').strip() for lang in self.available_languages}
            return True
        except Exception as e:
            return False

    def detect_system_language(self):
        for env_var in ('LANG', 'LC_ALL'):
            lang = os.environ.get(env_var, '')
            if lang:
                lang_code = lang.split('.')[0].split('_')[0].lower()
                if lang_code in self.available_languages:
                    return lang_code

        try:
            loc = locale.setlocale(locale.LC_ALL, '')
            if loc:
                lang_code = loc.split('.')[0].split('_')[0].lower()
                if lang_code in self.available_languages:
                    return lang_code
        except Exception:
            pass

        return 'zh'

    def t(self, key, default=None):
        if key in self.translations:
            if self.current_lang in self.translations[key]:
                return self.translations[key][self.current_lang]
            if default is not None:
                return default
            for lang in self.available_languages:
                if self.translations[key].get(lang):
                    return self.translations[key][lang]
        return default if default is not None else key

    def t_format(self, key, *args, default=None):
        template = self.t(key, default)
        try:
            return template.format(*args)
        except (IndexError, KeyError):
            return template

    def set_language(self, lang):
        if lang in self.available_languages:
            self.current_lang = lang
            return True
        return False

    def get_available_languages(self):
        return self.available_languages


class BazaarGate:
    LAUNCHER_WINDOW_TIMEOUT = 30
    GAME_START_TIMEOUT = 120
    PROCESS_CLOSE_TIMEOUT = 5

    DEFAULT_MOD_ITEMS = ['BepInEx', 'BazaarPlusPlus', 'doorstop_config.ini', 'winhttp.dll']

    def __init__(self, root):
        self.root = root
        self.root.geometry("500x600")
        self.root.minsize(400, 500)
        self.root.resizable(True, True)

        self.default_game_path = r"C:\Users\Administrator\AppData\Roaming\Tempo Launcher - Beta\game\buildx64"
        self.settings_file = "settings.txt"
        self.backup_folder = "mod_backup"
        self.log_file = "launcher.log"

        self.lang = LanguageManager()

        saved_lang = self._load_language_setting()
        if saved_lang and saved_lang in self.lang.get_available_languages():
            self.lang.set_language(saved_lang)
        else:
            detected = self.lang.detect_system_language()
            self.lang.set_language(detected)

        self.game_path = tk.StringVar()
        self.launcher_path = tk.StringVar()
        self.mod_items = self.DEFAULT_MOD_ITEMS.copy()
        self.current_page = 'main'

        self.main_frame = None
        self.settings_frame = None

        self._setup_logger()
        self._setup_ui()
        self._load_settings()
        self._apply_language()

    def _setup_logger(self):
        self.logger = logging.getLogger('BazaarGate')
        self.logger.setLevel(logging.INFO)
        self.logger.handlers = []
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            handler = logging.FileHandler(self.log_file, encoding='utf-8', mode='w')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        except Exception:
            pass

    def _load_language_setting(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get('language', None)
        except Exception:
            pass
        return None

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Main.TFrame', background='#f0f2f5')
        style.configure('Card.TFrame', background='#ffffff')

        style.configure('Title.TLabel', font=('Microsoft YaHei UI', 16, 'bold'), background='#f0f2f5', foreground='#1a1a1a')
        style.configure('Header.TLabel', font=('Microsoft YaHei UI', 11, 'bold'), background='#ffffff', foreground='#333333')
        style.configure('Label.TLabel', font=('Microsoft YaHei UI', 10), background='#ffffff', foreground='#555555')
        style.configure('Status.TLabel', font=('Microsoft YaHei UI', 10), background='#f0f2f5', foreground='#666666')
        style.configure('Hint.TLabel', font=('Microsoft YaHei UI', 9), background='#ffffff', foreground='#888888', wraplength=400)

        style.configure('Primary.TButton', font=('Microsoft YaHei UI', 11, 'bold'), foreground='#ffffff', background='#0078d4')
        style.map('Primary.TButton',
                  background=[('active', '#106ebe'), ('pressed', '#005a9e'), ('disabled', '#cccccc')],
                  foreground=[('disabled', '#999999')])

        style.configure('Secondary.TButton', font=('Microsoft YaHei UI', 10), foreground='#0078d4', background='#e8f4fd')
        style.map('Secondary.TButton',
                  background=[('active', '#d0e8f9'), ('pressed', '#b8dcf0')])

        style.configure('Modern.TEntry', font=('Microsoft YaHei UI', 10), fieldbackground='#ffffff', insertcolor='#0078d4')

    def _show_page(self, page_name):
        if self.current_page == page_name:
            return
        self.current_page = page_name
        if page_name == 'main':
            if self.settings_frame:
                self.settings_frame.grid_forget()
            if self.main_frame:
                self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        elif page_name == 'settings':
            if self.main_frame:
                self.main_frame.grid_forget()
            if self.settings_frame is None:
                self._create_settings_page()
            self.settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self._on_show_settings_page()
        self.root.update()

    def _create_main_page(self):
        self.main_frame = ttk.Frame(self.root, style='Main.TFrame', padding=20)
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(self.main_frame, text=self.lang.t('title_with_emoji'), style='Title.TLabel')
        self.title_label.grid(row=0, column=0, pady=(0, 15), sticky=tk.W)

        lang_frame = ttk.Frame(self.main_frame, style='Card.TFrame', padding=12)
        lang_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        lang_frame.configure(relief=tk.FLAT)

        self.language_label = ttk.Label(lang_frame, text="🌐 语言", style='Header.TLabel')
        self.language_label.pack(side=tk.LEFT, padx=(0, 8))
        self.language_combo = ttk.Combobox(lang_frame, values=self.lang.get_available_languages(), width=6, state='readonly')
        self.language_combo.pack(side=tk.LEFT, padx=(0, 12))
        self.language_combo.set(self.lang.current_lang)
        self.language_combo.bind('<<ComboboxSelected>>', self._on_language_changed)

        self.settings_btn = ttk.Button(lang_frame, text=self.lang.t('open_settings', '⚙️ 捕获文件'), command=lambda: self._show_page('settings'), style='Secondary.TButton')
        self.settings_btn.pack(side=tk.LEFT)

        settings_card = ttk.Frame(self.main_frame, style='Card.TFrame', padding=15)
        settings_card.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        settings_card.configure(relief=tk.FLAT)

        self.game_folder_label = ttk.Label(settings_card, text=self.lang.t('game_folder_label'), style='Header.TLabel')
        self.game_folder_label.pack(anchor=tk.W, pady=(0, 6))

        game_path_frame = ttk.Frame(settings_card)
        game_path_frame.pack(fill=tk.X, pady=(0, 10))
        game_entry = ttk.Entry(game_path_frame, textvariable=self.game_path, style='Modern.TEntry')
        game_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.browse_game_btn = ttk.Button(game_path_frame, text=self.lang.t('browse_button'), command=self._browse_game_path, style='Secondary.TButton', width=6)
        self.browse_game_btn.pack(side=tk.LEFT, padx=(8, 0), ipady=3)

        self.launcher_folder_label = ttk.Label(settings_card, text=self.lang.t('launcher_folder_label'), style='Header.TLabel')
        self.launcher_folder_label.pack(anchor=tk.W, pady=(0, 6))

        launcher_path_frame = ttk.Frame(settings_card)
        launcher_path_frame.pack(fill=tk.X)
        launcher_entry = ttk.Entry(launcher_path_frame, textvariable=self.launcher_path, style='Modern.TEntry')
        launcher_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.browse_launcher_btn = ttk.Button(launcher_path_frame, text=self.lang.t('browse_button'), command=self._browse_launcher_path, style='Secondary.TButton', width=6)
        self.browse_launcher_btn.pack(side=tk.LEFT, padx=(8, 0), ipady=3)

        button_card = ttk.Frame(self.main_frame, style='Card.TFrame', padding=15)
        button_card.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        button_card.configure(relief=tk.FLAT)

        self.launch_button = ttk.Button(button_card, text=self.lang.t('start_game_button'), command=self._start_launch_process, style='Primary.TButton')
        self.launch_button.pack(fill=tk.X, ipady=8)

        self.status_label = ttk.Label(self.main_frame, text=self.lang.t('status_ready'), style='Status.TLabel', font=('Microsoft YaHei UI', 10))
        self.status_label.grid(row=4, column=0, pady=(0, 10), sticky=tk.W)

        log_card = ttk.Frame(self.main_frame, style='Card.TFrame', padding=12)
        log_card.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        log_card.configure(relief=tk.FLAT)
        self.main_frame.rowconfigure(5, weight=1)

        self.log_card_title = ttk.Label(log_card, text=self.lang.t('log_frame_title'), style='Header.TLabel')
        self.log_card_title.pack(anchor=tk.W, pady=(0, 8))

        log_scrollbar = ttk.Scrollbar(log_card)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 5))

        self.log_text = tk.Text(log_card, height=10, wrap=tk.WORD, font=('Consolas', 9),
                               bg='#1e1e1e', fg='#cccccc', insertbackground='#ffffff',
                               yscrollcommand=log_scrollbar.set, relief=tk.FLAT, bd=0,
                               highlightthickness=0, padx=8, pady=8, spacing1=2, spacing2=2)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(0, 5))
        log_scrollbar.config(command=self.log_text.yview)

        self.log_text.tag_config('big_reminder', font=('Microsoft YaHei UI', 12, 'bold'), foreground='#00ff00', justify='center')

        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

    def _create_settings_page(self):
        self.settings_frame = ttk.Frame(self.root, style='Main.TFrame', padding=20)
        self.settings_frame.columnconfigure(0, weight=1)

        title_frame = ttk.Frame(self.settings_frame, style='Main.TFrame')
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        self.back_btn = ttk.Button(title_frame, text=self.lang.t('back_btn', '⬅️ 返回'), command=lambda: self._show_page('main'), style='Secondary.TButton')
        self.back_btn.pack(side=tk.LEFT, padx=(0, 15))

        self.settings_title_label = ttk.Label(title_frame, text=self.lang.t('settings_title', '📦 模组文件配置'), style='Title.TLabel')
        self.settings_title_label.pack(side=tk.LEFT)

        config_card = ttk.Frame(self.settings_frame, style='Card.TFrame', padding=15)
        config_card.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        config_card.configure(relief=tk.FLAT)
        self.settings_frame.rowconfigure(1, weight=1)

        self.mod_files_hint = ttk.Label(config_card, text=self.lang.t('mod_files_hint'), style='Header.TLabel')
        self.mod_files_hint.pack(anchor=tk.W, pady=(0, 8))

        self.mod_files_help = ttk.Label(config_card, text=self.lang.t('mod_files_help'), style='Hint.TLabel')
        self.mod_files_help.pack(anchor=tk.W, pady=(0, 10))

        text_frame = tk.Frame(config_card, bg='#ffffff', relief=tk.SOLID, bd=1)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        self.mod_files_text = tk.Text(text_frame, height=10, wrap=tk.WORD, font=('Microsoft YaHei UI', 10),
                                      bg='#ffffff', fg='#333333', insertbackground='#0078d4',
                                      relief=tk.FLAT, bd=0, highlightthickness=0, padx=10, pady=10)
        self.mod_files_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        text_scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.mod_files_text.yview)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.mod_files_text.config(yscrollcommand=text_scrollbar.set)

        self.save_settings_btn = ttk.Button(config_card, text=self.lang.t('save_settings_btn', '💾 保存配置'), command=self._save_mod_settings, style='Primary.TButton')
        self.save_settings_btn.pack(fill=tk.X, ipady=6)

    def _on_show_settings_page(self):
        self._load_mod_items_to_text()

    def _load_mod_items_to_text(self):
        self.mod_files_text.delete('1.0', tk.END)
        self.mod_files_text.insert('1.0', '\n'.join(self.mod_items))

    def _save_mod_settings(self):
        content = self.mod_files_text.get('1.0', tk.END).strip()
        lines = [line.strip() for line in content.split('\n') if line.strip()]

        invalid_chars = '<>:"/\\|?*'
        valid_items = []
        for item in lines:
            if any(c in item for c in invalid_chars):
                self.log_t('invalid_filename', item, level="WARNING")
                continue
            valid_items.append(item)

        if valid_items:
            self.mod_items = valid_items
        else:
            self.mod_items = self.DEFAULT_MOD_ITEMS.copy()

        try:
            settings = {}
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            settings['mod_items'] = self.mod_items
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            self.log_t('settings_saved', level="SUCCESS")
        except Exception as e:
            self.log_t('save_settings_failed', str(e), level="ERROR")

    def _setup_ui(self):
        self._setup_styles()
        self.root.configure(bg='#f0f2f5')
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self._create_main_page()
        self._create_settings_page()
        self._show_page('main')

    def _apply_language_to_main_page(self):
        self.title_label.config(text=self.lang.t('title_with_emoji'))
        self.game_folder_label.config(text=self.lang.t('game_folder_label'))
        self.browse_game_btn.config(text=self.lang.t('browse_button'))
        self.launcher_folder_label.config(text=self.lang.t('launcher_folder_label'))
        self.browse_launcher_btn.config(text=self.lang.t('browse_button'))
        self.launch_button.config(text=self.lang.t('start_game_button'))
        self.status_label.config(text=self.lang.t('status_ready'))
        self.log_card_title.config(text=self.lang.t('log_frame_title'))
        self.language_label.config(text=self.lang.t('language_setting_label', '🌐 语言'))
        self.settings_btn.config(text=self.lang.t('open_settings', '⚙️ 捕获文件'))

    def _apply_language_to_settings_page(self):
        if self.settings_frame is None:
            return
        self.settings_title_label.config(text=self.lang.t('settings_title', '📦 模组文件配置'))
        self.back_btn.config(text=self.lang.t('back_btn', '⬅️ 返回'))
        self.mod_files_hint.config(text=self.lang.t('mod_files_hint', '📝 模组文件列表:'))
        self.mod_files_help.config(text=self.lang.t('mod_files_help'))
        self.save_settings_btn.config(text=self.lang.t('save_settings_btn', '💾 保存配置'))

    def _on_language_changed(self, event=None):
        selected = self.language_combo.get()
        if self.lang.set_language(selected):
            self._save_settings()
            self._apply_language()

    def log_t(self, key, *args, level="INFO", default=None):
        message = self.lang.t_format(key, *args, default=default)
        self._log_message(message, level)

    def _log_message(self, message, level="INFO"):
        timestamp = time.strftime("%H:%M:%S")
        log_level_map = {
            "INFO": logging.INFO,
            "SUCCESS": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "SYSTEM": logging.INFO,
            "BIGREMINDER": logging.INFO
        }

        if hasattr(self, 'log_text'):
            if level == "BIGREMINDER":
                self.log_text.insert(tk.END, f"{message}\n", 'big_reminder')
            else:
                self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)

        if hasattr(self, 'status_label'):
            if level == "ERROR":
                self.status_label.config(text=f"❌ {message}", foreground='red')
            elif level == "SUCCESS":
                self.status_label.config(text=f"✅ {message}", foreground='green')
            elif level == "WARNING":
                self.status_label.config(text=f"⚠️ {message}", foreground='orange')
            else:
                self.status_label.config(text=f"🔄 {message}", foreground='blue')

        self.logger.log(log_level_map.get(level, logging.INFO), message)
        self.root.update()

    def log(self, message, level="INFO"):
        self._log_message(message, level)

    def _apply_language(self):
        self.root.title(self.lang.t('app_title'))
        self._apply_language_to_main_page()
        self._apply_language_to_settings_page()
        self.log_t('program_started', level="INFO")
        self._check_default_paths()

    def _check_default_paths(self):
        if os.path.exists(os.path.join(self.default_game_path, "TheBazaar.exe")):
            if not self.game_path.get():
                self.game_path.set(self.default_game_path)
                self.log_t('detected_default_game_path', self.default_game_path, level="SUCCESS")

    def _browse_game_path(self):
        path = filedialog.askdirectory(title=self.lang.t('select_game_dir'))
        if path:
            if os.path.exists(os.path.join(path, "TheBazaar.exe")):
                self.game_path.set(path)
                self._save_settings()
                self.log_t('game_path_set', path, level="SUCCESS")
            else:
                messagebox.showerror(self.lang.t('error_title'), self.lang.t('no_game_exe_error'))
                self.log_t('game_exe_not_found_error', level="ERROR")

    def _browse_launcher_path(self):
        path = filedialog.askdirectory(title=self.lang.t('select_launcher_dir'))
        if path:
            launcher_exe = self._find_launcher_exe(path)
            if launcher_exe:
                self.launcher_path.set(path)
                self._save_settings()
                self.log_t('launcher_path_set', path, level="SUCCESS")
                self.log_t('auto_detected', os.path.basename(launcher_exe), level="INFO")
            else:
                messagebox.showerror(self.lang.t('error_title'), f"{self.lang.t('no_launcher_error')}\n{path}")
                self.log_t('launcher_exe_not_found_error', level="ERROR")

    def _find_launcher_exe(self, launcher_dir):
        if not launcher_dir or not os.path.exists(launcher_dir):
            return None
        for item in os.listdir(launcher_dir):
            if "Tempo Launcher" in item and item.endswith('.exe'):
                return os.path.join(launcher_dir, item)
        return None

    def _load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.game_path.set(settings.get('game_path', ''))
                    self.launcher_path.set(settings.get('launcher_path', ''))
                    mod_items = settings.get('mod_items')
                    if mod_items and isinstance(mod_items, list):
                        self.mod_items = mod_items
                    self.log_t('settings_loaded', level="SYSTEM")
        except Exception as e:
            self.log_t('load_settings_failed', str(e), level="WARNING")

    def _save_settings(self):
        try:
            settings = {
                'game_path': self.game_path.get(),
                'launcher_path': self.launcher_path.get(),
                'language': self.lang.current_lang,
                'mod_items': self.mod_items
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_t('save_settings_failed', str(e), level="ERROR")

    def _get_mod_files(self, game_dir):
        mod_files = []
        for item in self.mod_items:
            item_path = os.path.join(game_dir, item)
            if os.path.exists(item_path):
                mod_files.append(item)
                self.log_t('detected_mod', item, level="INFO")
        return mod_files

    def _backup_mods(self, game_dir):
        if not os.path.exists(self.backup_folder):
            os.makedirs(self.backup_folder)
        mod_files = self._get_mod_files(game_dir)
        if not mod_files:
            return False
        self.log_t('found_mod_files', len(mod_files), level="INFO")
        for item in mod_files:
            src = os.path.join(game_dir, item)
            dst = os.path.join(self.backup_folder, item)
            try:
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                self.log_t('backup_success', item, level="SUCCESS")
            except Exception as e:
                self.log_t('delete_failed', item, str(e), level="ERROR")
                return False
        return True

    def _delete_mods(self, game_dir):
        mod_files = self._get_mod_files(game_dir)
        for item in mod_files:
            item_path = os.path.join(game_dir, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
                self.log_t('detected_mod', item, level="INFO")
            except Exception as e:
                self.log_t('backup_failed', item, str(e), level="ERROR")
                return False
        return True

    def _restore_mods(self, game_dir):
        if not os.path.exists(self.backup_folder):
            self.log_t('no_backup_folder', level="WARNING")
            return False
        self.log_t('restoring_mods', level="INFO")
        for item in os.listdir(self.backup_folder):
            src = os.path.join(self.backup_folder, item)
            dst = os.path.join(game_dir, item)
            try:
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                self.log_t('restored_success', item, level="SUCCESS")
            except Exception as e:
                self.log_t('restore_failed', item, str(e), level="ERROR")
                return False
        try:
            shutil.rmtree(self.backup_folder)
            self.log_t('backup_folder_cleaned', level="SUCCESS")
        except Exception as e:
            self.logger.warning(f"Failed to clean backup folder: {e}")
        return True

    def _find_process_by_name(self, process_name):
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if process_name.lower() in proc.info['name'].lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _close_process_gracefully(self, proc):
        try:
            proc.terminate()
            try:
                proc.wait(timeout=self.PROCESS_CLOSE_TIMEOUT)
                return True
            except psutil.TimeoutExpired:
                proc.kill()
                return True
        except Exception as e:
            self.log_t('close_process_failed', str(e), level="ERROR")
            return False

    def _show_big_reminder(self, message):
        self._log_message("", "INFO")
        self._log_message(message, "BIGREMINDER")
        self._log_message("", "INFO")

    def _wait_for_manual_click_and_capture(self):
        def find_launcher_window():
            result = []
            def enum_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "Tempo Launcher" in title:
                        result.append(hwnd)
                return True
            win32gui.EnumWindows(enum_callback, None)
            return result[0] if result else None

        self.log_t('waiting_launcher_window', level="INFO")
        hwnd = None
        for _ in range(self.LAUNCHER_WINDOW_TIMEOUT):
            hwnd = find_launcher_window()
            if hwnd:
                break
            time.sleep(1)

        if not hwnd:
            self.log_t('no_launcher_window_detected', level="WARNING")

        start_time = time.time()
        game_proc = None
        while time.time() - start_time < self.GAME_START_TIMEOUT:
            game_proc = self._find_process_by_name("TheBazaar.exe")
            if game_proc:
                break
            self.root.update()
            time.sleep(0.3)

        if not game_proc:
            raise Exception(self.lang.t_format('timeout_no_game', self.GAME_START_TIMEOUT))

        self.log_t('game_detected', game_proc.pid, level="SUCCESS")
        params = None
        try:
            cmd_line = game_proc.cmdline()
            if len(cmd_line) > 1:
                params = ' '.join(cmd_line[1:])
                self.log_t('capture_params_success', level="SUCCESS")
            else:
                raise Exception(self.lang.t('cannot_get_cmdline'))
        except Exception as e:
            raise Exception(self.lang.t_format('capture_params_failed', str(e)))
        return params

    def _launch_game_with_params(self, params):
        game_exe = os.path.join(self.game_path.get(), "TheBazaar.exe")
        if not os.path.exists(game_exe):
            raise Exception(self.lang.t_format('game_exe_not_exists', game_exe))
        self.log_t('launching_game_with_params', level="INFO")
        try:
            subprocess.Popen(
                f'"{game_exe}" {params}',
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=self.game_path.get()
            )
            self.log_t('game_started_success', level="SUCCESS")
            return True
        except Exception as e:
            raise Exception(self.lang.t_format('launch_game_failed', str(e)))

    def _start_launch_process(self):
        if not self.game_path.get():
            messagebox.showerror(self.lang.t('error_title'), self.lang.t('please_set_game_path'))
            return
        if not self.launcher_path.get():
            messagebox.showerror(self.lang.t('error_title'), self.lang.t('please_set_launcher_path'))
            return
        game_exe = os.path.join(self.game_path.get(), "TheBazaar.exe")
        if not os.path.exists(game_exe):
            messagebox.showerror(self.lang.t('error_title'), self.lang.t_format('game_exe_missing', self.game_path.get()))
            return
        launcher_dir = self.launcher_path.get()
        if not launcher_dir or not os.path.exists(launcher_dir):
            messagebox.showerror(self.lang.t('error_title'), self.lang.t('please_set_launcher_dir'))
            return
        if not self._find_launcher_exe(launcher_dir):
            messagebox.showerror(self.lang.t('error_title'), self.lang.t_format('launcher_not_found_in_dir', launcher_dir))
            return

        self.launch_button.config(state='disabled')
        threading.Thread(target=self._run_launch_process, daemon=True).start()

    def _run_launch_process(self):
        try:
            self.log_t('separator_line', level="SYSTEM")
            self.log_t('start_auto_process', level="SYSTEM")
            self.log_t('separator_line', level="SYSTEM")

            step1_success = False
            try:
                self.log_t('step1_check_mods', level="INFO")
                mod_files = self._get_mod_files(self.game_path.get())
                if mod_files:
                    self.log_t('detected_mod_count', len(mod_files), level="INFO")
                    if self._backup_mods(self.game_path.get()):
                        if self._delete_mods(self.game_path.get()):
                            self.log_t('mods_backup_deleted', level="SUCCESS")
                            step1_success = True
                        else:
                            raise Exception(self.lang.t('delete_mods_failed'))
                    else:
                        raise Exception(self.lang.t('backup_mods_failed'))
                else:
                    self.log_t('no_mods_detected_skip', level="INFO")
                    step1_success = True
            except Exception as e:
                self.log_t('step1_failed', str(e), level="ERROR")
                raise

            try:
                self.log_t('step2_launch_launcher', level="INFO")
                launcher_dir = self.launcher_path.get()
                launcher_exe = self._find_launcher_exe(launcher_dir)
                if not launcher_exe:
                    raise Exception(self.lang.t_format('launcher_not_found_in_dir', launcher_dir))
                self.log_t('launcher_dir', launcher_dir, level="INFO")
                self.log_t('launcher_exe', os.path.basename(launcher_exe), level="INFO")
                self.log_t('starting_launcher', level="INFO")
                launcher_pid = subprocess.Popen(launcher_exe, cwd=launcher_dir).pid
                self.log_t('launcher_started', launcher_pid, level="SUCCESS")
                self._show_big_reminder(self.lang.t('reminder_click_play'))
                params = self._wait_for_manual_click_and_capture()
                if not params:
                    raise Exception(self.lang.t('cannot_get_cmdline'))
                self.log_t('got_params_success', level="SUCCESS")
                self.log_t('closing_game_process', level="INFO")
                game_proc = self._find_process_by_name("TheBazaar.exe")
                if game_proc:
                    self._close_process_gracefully(game_proc)
                    self.log_t('game_process_closed', level="SUCCESS")
                else:
                    self.log_t('no_running_game_process', level="WARNING")
                time.sleep(2)
                self.log_t('step2_complete', level="SUCCESS")
            except Exception as e:
                self.log_t('step2_failed', str(e), level="ERROR")
                raise

            try:
                self.log_t('step3_restore_mods', level="INFO")
                if step1_success and os.path.exists(self.backup_folder):
                    if self._restore_mods(self.game_path.get()):
                        self.log_t('mods_restored_success', level="SUCCESS")
                    else:
                        raise Exception(self.lang.t('restore_mods_failed'))
                else:
                    self.log_t('no_need_restore_mods', level="INFO")
            except Exception as e:
                self.log_t('step3_failed', str(e), level="ERROR")
                raise

            try:
                self.log_t('step4_launch_game', level="INFO")
                if self._launch_game_with_params(params):
                    self.log_t('step_separator', level="SUCCESS")
                    self.log_t('all_steps_complete', level="SUCCESS")
                    self.log_t('step_separator', level="SUCCESS")
            except Exception as e:
                self.log_t('step4_launch_game', str(e), level="ERROR")
                raise

            time.sleep(3)
            self.log_t('program_will_exit', level="SYSTEM")
            time.sleep(2)
            self.root.quit()
            sys.exit(0)

        except Exception as e:
            self.log_t('process_execute_failed', str(e), level="ERROR")
            self.log_t('trying_cleanup', level="WARNING")
            try:
                if os.path.exists(self.backup_folder):
                    self._restore_mods(self.game_path.get())
            except Exception as e:
                self.logger.warning(f"Failed to restore mods during cleanup: {e}")
            self.launch_button.config(state='normal')
            messagebox.showerror(self.lang.t('error_title'), self.lang.t_format('process_error', str(e)))


def main():
    root = tk.Tk()
    app = BazaarGate(root)
    root.mainloop()


if __name__ == "__main__":
    main()
