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
        self.app.logger = logging.getLogger("TheBazaarGateTest")
        self.app.log_t = lambda *args, **kwargs: None
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
