import json
import logging
import os
import tempfile
import unittest
from unittest import mock

from dist.launcher_tool import BazaarGate, LanguageManager


class FakeStringVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class FakeProcess:
    def __init__(self, name: str) -> None:
        self.info = {"name": name}


class BazaarGateLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = BazaarGate.__new__(BazaarGate)
        self.app.root = mock.Mock()
        self.app.logger = logging.getLogger("TheBazaarGateTest")
        self.app.log_t = mock.Mock()
        self.app.lang = mock.Mock()
        self.app.lang.t.return_value = "error"
        self.app.lang.t_format.side_effect = lambda key, *args, **kwargs: (
            f"{key}:{args}"
        )

    def test_get_runtime_base_dir_uses_executable_when_frozen(self) -> None:
        with mock.patch(
            "dist.launcher_tool.sys",
            frozen=True,
            executable=r"C:\app\TheBazaarGate.exe",
        ):
            self.assertEqual(self.app._get_runtime_base_dir(), r"C:\app")

    def test_validate_executable_path_requires_existing_exe_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            exe_path = os.path.join(temp_dir, "Tempo Launcher.exe")
            txt_path = os.path.join(temp_dir, "Tempo Launcher.txt")
            with open(exe_path, "w", encoding="utf-8") as handle:
                handle.write("stub")
            with open(txt_path, "w", encoding="utf-8") as handle:
                handle.write("stub")

            self.assertTrue(self.app._validate_executable_path(exe_path))
            self.assertFalse(self.app._validate_executable_path(txt_path))
            self.assertFalse(self.app._validate_executable_path(temp_dir))

    def test_find_process_by_name_uses_exact_match(self) -> None:
        processes = [
            FakeProcess("Tempo Launcher Helper.exe"),
            FakeProcess("TheBazaar.exe"),
        ]
        psutil_module = mock.Mock()
        psutil_module.process_iter.return_value = processes
        psutil_module.NoSuchProcess = RuntimeError
        psutil_module.AccessDenied = PermissionError

        with mock.patch("dist.launcher_tool.psutil", psutil_module):
            self.assertIsNone(self.app._find_process_by_name("Tempo Launcher.exe"))
            self.assertIsNotNone(self.app._find_process_by_name("TheBazaar.exe"))

    def test_find_launcher_exe_prefers_main_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_names = [
                "Tempo Launcher Helper.exe",
                "Tempo Launcher Updater.exe",
                "Tempo Launcher.exe",
            ]
            for name in file_names:
                with open(
                    os.path.join(temp_dir, name), "w", encoding="utf-8"
                ) as handle:
                    handle.write("stub")

            launcher_exe = self.app._find_launcher_exe(temp_dir)

            self.assertIsNotNone(launcher_exe)
            self.assertEqual(os.path.basename(launcher_exe), "Tempo Launcher.exe")

    def test_find_launcher_exe_returns_none_on_permission_error(self) -> None:
        with (
            mock.patch("dist.launcher_tool.os.path.exists", return_value=True),
            mock.patch(
                "dist.launcher_tool.os.listdir", side_effect=PermissionError("denied")
            ),
        ):
            self.assertIsNone(self.app._find_launcher_exe(r"C:\Tempo"))

    def test_find_launcher_exe_returns_none_on_os_error(self) -> None:
        with (
            mock.patch("dist.launcher_tool.os.path.exists", return_value=True),
            mock.patch("dist.launcher_tool.os.listdir", side_effect=OSError("busy")),
        ):
            self.assertIsNone(self.app._find_launcher_exe(r"C:\Tempo"))

    def test_launch_game_with_params_keeps_windows_arguments_intact(self) -> None:
        self.app.game_path = FakeStringVar(r"C:\Games\The Bazaar")
        self.app.log_t = lambda *args, **kwargs: None

        captured = {}

        def fake_popen(cmd_args, creationflags=0, cwd=None):
            captured["cmd_args"] = cmd_args
            captured["creationflags"] = creationflags
            captured["cwd"] = cwd
            return mock.Mock()

        params = ["--token=abc def", "--path=C:\\Program Files\\Tempo"]
        game_exe = os.path.join(self.app.game_path.get(), "TheBazaar.exe")

        with (
            mock.patch("dist.launcher_tool.os.path.exists", return_value=True),
            mock.patch("dist.launcher_tool.subprocess.Popen", side_effect=fake_popen),
        ):
            self.assertTrue(self.app._launch_game_with_params(params))

        self.assertEqual(captured["cmd_args"], [game_exe, *params])
        self.assertEqual(captured["cwd"], self.app.game_path.get())

    def test_backup_and_restore_mods_use_runtime_backup_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game_dir = os.path.join(temp_dir, "game")
            backup_dir = os.path.join(temp_dir, "runtime_backup")
            os.makedirs(game_dir)
            os.makedirs(os.path.join(game_dir, "BepInEx"))
            with open(
                os.path.join(game_dir, "winhttp.dll"), "w", encoding="utf-8"
            ) as handle:
                handle.write("dll")
            with open(
                os.path.join(game_dir, "BepInEx", "config.ini"), "w", encoding="utf-8"
            ) as handle:
                handle.write("cfg")

            self.app.mod_items = ["BepInEx", "winhttp.dll"]
            self.app.backup_folder = backup_dir

            self.assertTrue(self.app._backup_mods(game_dir))
            self.assertTrue(
                os.path.exists(os.path.join(backup_dir, "BepInEx", "config.ini"))
            )
            self.assertTrue(os.path.exists(os.path.join(backup_dir, "winhttp.dll")))

            os.remove(os.path.join(game_dir, "winhttp.dll"))
            self.assertTrue(self.app._restore_mods(game_dir))
            self.assertTrue(os.path.exists(os.path.join(game_dir, "winhttp.dll")))
            self.assertFalse(os.path.exists(backup_dir))

    def test_delete_mods_removes_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game_dir = os.path.join(temp_dir, "game")
            os.makedirs(os.path.join(game_dir, "BepInEx"))
            with open(
                os.path.join(game_dir, "BepInEx", "config.ini"), "w", encoding="utf-8"
            ) as handle:
                handle.write("cfg")
            with open(
                os.path.join(game_dir, "winhttp.dll"), "w", encoding="utf-8"
            ) as handle:
                handle.write("dll")

            self.app.mod_items = ["BepInEx", "winhttp.dll"]

            self.assertTrue(self.app._delete_mods(game_dir))
            self.assertFalse(os.path.exists(os.path.join(game_dir, "BepInEx")))
            self.assertFalse(os.path.exists(os.path.join(game_dir, "winhttp.dll")))

    def test_backup_mods_logs_copy_error_detail(self) -> None:
        self.app.backup_folder = r"C:\Temp\mod_backup"
        self.app._copy_item = mock.Mock(return_value=(False, "permission denied"))

        result = self.app._backup_mods(r"C:\Games\The Bazaar", ["winhttp.dll"])

        self.assertFalse(result)
        self.app._copy_item.assert_called_once()
        self.app.log_t.assert_any_call(
            "backup_failed", "winhttp.dll", "permission denied", level="ERROR"
        )

    def test_restore_mods_logs_copy_error_detail(self) -> None:
        self.app.backup_folder = r"C:\Temp\mod_backup"
        self.app._copy_item = mock.Mock(return_value=(False, "file is locked"))

        with (
            mock.patch("dist.launcher_tool.os.path.exists", return_value=True),
            mock.patch("dist.launcher_tool.os.listdir", return_value=["winhttp.dll"]),
        ):
            result = self.app._restore_mods(r"C:\Games\The Bazaar")

        self.assertFalse(result)
        self.app._copy_item.assert_called_once()
        self.app.log_t.assert_any_call(
            "restore_failed", "winhttp.dll", "file is locked", level="ERROR"
        )

    def test_load_settings_ignores_invalid_mod_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.app.settings_file = os.path.join(temp_dir, "settings.txt")
            self.app.game_path = FakeStringVar()
            self.app.launcher_path = FakeStringVar()
            self.app.mod_items = ["default"]

            with open(self.app.settings_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "game_path": "game",
                        "launcher_path": "launcher",
                        "mod_items": ["BepInEx", "", 123, "winhttp.dll"],
                    },
                    handle,
                    ensure_ascii=False,
                )

            self.app._load_settings()

            self.assertEqual(self.app.game_path.get(), "game")
            self.assertEqual(self.app.launcher_path.get(), "launcher")
            self.assertEqual(self.app.mod_items, ["BepInEx", "winhttp.dll"])

    def test_read_settings_data_returns_empty_dict_for_non_mapping_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.app.settings_file = os.path.join(temp_dir, "settings.txt")
            with open(self.app.settings_file, "w", encoding="utf-8") as handle:
                json.dump(["not", "a", "mapping"], handle, ensure_ascii=False)

            self.assertEqual(self.app._read_settings_data(), {})

    def test_write_settings_data_persists_json_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.app.settings_file = os.path.join(temp_dir, "settings.txt")
            settings = {"language": "en", "mod_items": ["BepInEx"]}

            self.app._write_settings_data(settings)

            with open(self.app.settings_file, "r", encoding="utf-8") as handle:
                saved = json.load(handle)
            self.assertEqual(saved, settings)

    def test_write_settings_data_replaces_invalid_existing_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            self.app.settings_file = os.path.join(temp_dir, "settings.txt")
            with open(self.app.settings_file, "w", encoding="utf-8") as handle:
                handle.write("{invalid json")

            settings = {"language": "zh", "mod_items": ["winhttp.dll"]}

            self.app._write_settings_data(settings)

            with open(self.app.settings_file, "r", encoding="utf-8") as handle:
                saved = json.load(handle)
            self.assertEqual(saved, settings)

    def test_run_launch_process_reuses_detected_mod_files(self) -> None:
        self.app.game_path = FakeStringVar(r"C:\Games\The Bazaar")
        self.app.launcher_path = FakeStringVar(r"C:\Tempo")
        self.app.backup_folder = r"C:\Temp\mod_backup"
        self.app._request_exit = mock.Mock()
        self.app._set_button_state = mock.Mock()
        self.app._show_error_dialog = mock.Mock()
        self.app._show_big_reminder = mock.Mock()
        self.app._safe_launch_exe = mock.Mock(return_value=mock.Mock(pid=123))
        self.app._wait_for_manual_click_and_capture = mock.Mock(
            return_value=["--token=abc"]
        )
        self.app._find_process_by_name = mock.Mock(
            side_effect=[mock.Mock(pid=456), None]
        )
        self.app._close_process_gracefully = mock.Mock(return_value=True)
        self.app._restore_mods = mock.Mock(return_value=True)
        self.app._launch_game_with_params = mock.Mock(return_value=True)

        mod_files = ["BepInEx", "winhttp.dll"]
        self.app._get_mod_files = mock.Mock(return_value=mod_files)
        self.app._backup_mods = mock.Mock(return_value=True)
        self.app._delete_mods = mock.Mock(return_value=True)

        with (
            mock.patch("dist.launcher_tool.time.sleep", return_value=None),
            mock.patch(
                "dist.launcher_tool.os.path.exists",
                side_effect=lambda path: path == self.app.backup_folder,
            ),
        ):
            self.app._run_launch_process(
                self.app.game_path.get(),
                self.app.launcher_path.get(),
                r"C:\Tempo\Tempo Launcher.exe",
            )

        self.app._get_mod_files.assert_called_once_with(self.app.game_path.get())
        self.app._backup_mods.assert_called_once_with(
            self.app.game_path.get(), mod_files
        )
        self.app._delete_mods.assert_called_once_with(
            self.app.game_path.get(), mod_files
        )

    def test_copy_item_returns_error_detail_on_failure(self) -> None:
        with mock.patch(
            "dist.launcher_tool.shutil.copy2", side_effect=OSError("disk full")
        ):
            copied, error_detail = self.app._copy_item("src", "dst")

        self.assertFalse(copied)
        self.assertEqual(error_detail, "disk full")

    def test_backup_mods_does_not_rescan_when_empty_mod_list_is_provided(self) -> None:
        self.app._get_mod_files = mock.Mock(
            side_effect=AssertionError("should not rescan")
        )

        self.assertFalse(self.app._backup_mods(r"C:\Games\The Bazaar", []))

    def test_delete_mods_does_not_rescan_when_empty_mod_list_is_provided(self) -> None:
        self.app._get_mod_files = mock.Mock(
            side_effect=AssertionError("should not rescan")
        )

        self.assertTrue(self.app._delete_mods(r"C:\Games\The Bazaar", []))


class BazaarGateLaunchFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = BazaarGate.__new__(BazaarGate)
        self.app.root = mock.Mock()
        self.app.logger = logging.getLogger("TheBazaarGateLaunchFlowTest")
        self.app.log_t = lambda *args, **kwargs: None
        self.app.lang = mock.Mock()
        self.app.lang.t.side_effect = lambda key, default=None: default or key
        self.app.lang.t_format.side_effect = lambda key, *args, **kwargs: (
            f"{key}:{args}"
        )
        self.app.game_path = FakeStringVar()
        self.app.launcher_path = FakeStringVar()
        self.app.launch_button = mock.Mock()
        self.app._worker_thread = None

    def test_start_launch_process_does_not_start_worker_when_validation_fails(
        self,
    ) -> None:
        self.app._validate_launch_prerequisites = mock.Mock(return_value=None)

        with mock.patch("dist.launcher_tool.threading.Thread") as thread_cls:
            self.app._start_launch_process()

        self.app._validate_launch_prerequisites.assert_called_once_with()
        thread_cls.assert_not_called()

    def test_start_launch_process_starts_worker_with_validated_values(self) -> None:
        validated = (
            r"C:\Games\The Bazaar",
            r"C:\Tempo",
            r"C:\Tempo\Tempo Launcher.exe",
        )
        fake_thread = mock.Mock()
        self.app._validate_launch_prerequisites = mock.Mock(return_value=validated)
        self.app._set_button_state = mock.Mock()

        with mock.patch(
            "dist.launcher_tool.threading.Thread", return_value=fake_thread
        ) as thread_cls:
            self.app._start_launch_process()

        self.app._set_button_state.assert_called_once_with("disabled")
        thread_cls.assert_called_once()
        self.assertEqual(
            thread_cls.call_args.kwargs["target"], self.app._run_launch_process
        )
        self.assertEqual(thread_cls.call_args.kwargs["args"], validated)
        self.assertTrue(thread_cls.call_args.kwargs["daemon"])
        fake_thread.start.assert_called_once_with()
        self.assertIs(self.app._worker_thread, fake_thread)

    def test_set_game_path_on_ui_thread_uses_root_after(self) -> None:
        callbacks = []

        def capture_after(delay, callback):
            callbacks.append((delay, callback))

        self.app.root.after.side_effect = capture_after

        self.app._set_game_path_on_ui_thread(r"C:\Games\The Bazaar")

        self.assertEqual(len(callbacks), 1)
        delay, callback = callbacks[0]
        self.assertEqual(delay, 0)
        self.assertEqual(self.app.game_path.get(), "")
        callback()
        self.assertEqual(self.app.game_path.get(), r"C:\Games\The Bazaar")

    def test_run_launch_process_schedules_game_path_update_on_ui_thread(self) -> None:
        self.app.game_path = FakeStringVar(r"C:\Original")
        self.app.launcher_path = FakeStringVar(r"C:\Tempo")
        self.app.backup_folder = r"C:\Temp\mod_backup"
        self.app._request_exit = mock.Mock()
        self.app._set_button_state = mock.Mock()
        self.app._show_error_dialog = mock.Mock()
        self.app._show_big_reminder = mock.Mock()
        self.app._safe_launch_exe = mock.Mock(return_value=mock.Mock(pid=123))
        self.app._wait_for_manual_click_and_capture = mock.Mock(
            return_value=["--token=abc"]
        )
        self.app._find_process_by_name = mock.Mock(
            side_effect=[mock.Mock(pid=456), None]
        )
        self.app._close_process_gracefully = mock.Mock(return_value=True)
        self.app._restore_mods = mock.Mock(return_value=True)
        self.app._launch_game_with_params = mock.Mock(return_value=True)
        self.app._set_game_path_on_ui_thread = mock.Mock()
        self.app._get_mod_files = mock.Mock(return_value=["winhttp.dll"])
        self.app._backup_mods = mock.Mock(return_value=True)
        self.app._delete_mods = mock.Mock(return_value=True)

        with (
            mock.patch("dist.launcher_tool.time.sleep", return_value=None),
            mock.patch(
                "dist.launcher_tool.os.path.exists",
                side_effect=lambda path: path == self.app.backup_folder,
            ),
        ):
            self.app._run_launch_process(
                r"C:\Games\The Bazaar",
                r"C:\Tempo",
                r"C:\Tempo\Tempo Launcher.exe",
            )

        self.app._set_game_path_on_ui_thread.assert_called_once_with(
            r"C:\Games\The Bazaar"
        )
        self.app._launch_game_with_params.assert_called_once_with(["--token=abc"])

    def test_wait_for_manual_click_and_capture_uses_poll_intervals(self) -> None:
        psutil_module = mock.Mock()
        psutil_module.NoSuchProcess = RuntimeError
        psutil_module.AccessDenied = PermissionError
        self.app._find_process_by_name = mock.Mock(
            side_effect=[
                None,
                mock.Mock(pid=321, cmdline=lambda: ["TheBazaar.exe", "--token=ok"]),
            ]
        )

        sleep_calls = []

        with (
            mock.patch("dist.launcher_tool.win32gui", mock.Mock()),
            mock.patch("dist.launcher_tool.IS_WINDOWS", True),
            mock.patch("dist.launcher_tool.psutil", psutil_module),
            mock.patch(
                "dist.launcher_tool.time.sleep",
                side_effect=lambda value: sleep_calls.append(value),
            ),
            mock.patch("dist.launcher_tool.AppConfig.LAUNCHER_WINDOW_TIMEOUT", 1),
            mock.patch(
                "dist.launcher_tool.AppConfig.LAUNCHER_WINDOW_POLL_INTERVAL", 1.0
            ),
            mock.patch("dist.launcher_tool.AppConfig.GAME_START_TIMEOUT", 5),
            mock.patch("dist.launcher_tool.AppConfig.GAME_PROCESS_POLL_INTERVAL", 0.5),
        ):
            win32gui = __import__("dist.launcher_tool", fromlist=["win32gui"]).win32gui
            win32gui.IsWindowVisible.return_value = False
            win32gui.GetWindowText.return_value = ""
            win32gui.EnumWindows.side_effect = lambda callback, _: None

            params = self.app._wait_for_manual_click_and_capture()

        self.assertEqual(params, ["--token=ok"])
        self.assertIn(1.0, sleep_calls)
        self.assertIn(0.5, sleep_calls)

    def test_run_launch_process_logs_launch_failure_with_error_key(self) -> None:
        self.app.game_path = FakeStringVar(r"C:\Games\The Bazaar")
        self.app.launcher_path = FakeStringVar(r"C:\Tempo")
        self.app.backup_folder = r"C:\Temp\mod_backup"
        self.app.log_t = mock.Mock()
        self.app._request_exit = mock.Mock()
        self.app._set_button_state = mock.Mock()
        self.app._show_error_dialog = mock.Mock()
        self.app._show_big_reminder = mock.Mock()
        self.app._safe_launch_exe = mock.Mock(return_value=mock.Mock(pid=123))
        self.app._wait_for_manual_click_and_capture = mock.Mock(return_value=["--token=abc"])
        self.app._find_process_by_name = mock.Mock(side_effect=[mock.Mock(pid=456), None])
        self.app._close_process_gracefully = mock.Mock(return_value=True)
        self.app._restore_mods = mock.Mock(return_value=True)
        self.app._set_game_path_on_ui_thread = mock.Mock()
        self.app._launch_game_with_params = mock.Mock(side_effect=OSError("boom"))
        self.app._get_mod_files = mock.Mock(return_value=[])

        with (
            mock.patch("dist.launcher_tool.time.sleep", return_value=None),
            mock.patch("dist.launcher_tool.os.path.exists", return_value=False),
        ):
            self.app._run_launch_process(
                r"C:\Games\The Bazaar",
                r"C:\Tempo",
                r"C:\Tempo\Tempo Launcher.exe",
            )

        self.app.log_t.assert_any_call("launch_game_failed", "boom", level="ERROR")


class BazaarGateLanguageFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = BazaarGate.__new__(BazaarGate)
        self.app.root = mock.Mock()
        self.app.lang = mock.Mock()
        self.app.language_combo = mock.Mock()
        self.app._save_settings = mock.Mock()
        self.app._refresh_language_ui = mock.Mock()
        self.app._apply_language_to_main_page = mock.Mock()
        self.app._apply_language_to_settings_page = mock.Mock()
        self.app.log_t = mock.Mock()
        self.app._check_default_paths = mock.Mock()

    def test_on_language_changed_refreshes_ui_without_startup_side_effects(self) -> None:
        self.app.language_combo.get.return_value = "en"
        self.app.lang.set_language.return_value = True

        self.app._on_language_changed()

        self.app._save_settings.assert_called_once_with()
        self.app._refresh_language_ui.assert_called_once_with()
        self.app.log_t.assert_not_called()
        self.app._check_default_paths.assert_not_called()

    def test_apply_language_runs_startup_side_effects_once(self) -> None:
        self.app._apply_language()

        self.app._refresh_language_ui.assert_called_once_with()
        self.app.log_t.assert_called_once_with("program_started", level="INFO")
        self.app._check_default_paths.assert_called_once_with()


class LanguageManagerTests(unittest.TestCase):
    def test_translation_falls_back_to_available_language(self) -> None:
        manager = LanguageManager.__new__(LanguageManager)
        manager.current_lang = "fr"
        manager.available_languages = ["zh", "en"]
        manager.translations = {"hello": {"zh": "", "en": "Hello"}}

        self.assertEqual(manager.t("hello"), "Hello")


class BazaarGateUiSetupTests(unittest.TestCase):
    def test_setup_ui_only_builds_main_page_initially(self) -> None:
        app = BazaarGate.__new__(BazaarGate)
        app.root = mock.Mock()
        app._setup_styles = mock.Mock()
        app._create_main_page = mock.Mock()
        app._create_settings_page = mock.Mock()

        app._setup_ui()

        app._create_main_page.assert_called_once()
        app._create_settings_page.assert_not_called()


if __name__ == "__main__":
    unittest.main()
