"""
The Bazaar Gate 打包脚本

使用 PyInstaller 将启动器打包为独立的可执行文件。

Author: The Bazaar Gate Team
Version: 1.3.0
"""

import PyInstaller.__main__
import os
import sys
import traceback
from typing import List


BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
DIST_DIR: str = os.path.join(BASE_DIR, "dist")
OUTPUT_NAME: str = "TheBazaarGate"
REQUIRED_FILES: List[str] = ["launcher_tool.py", "language.csv"]


def check_required_files() -> bool:
    """
    检查打包所需的必需文件是否存在。

    Returns:
        所有必需文件存在返回True，否则返回False
    """
    missing_files = []
    for f in REQUIRED_FILES:
        file_path = os.path.join(DIST_DIR, f)
        if not os.path.exists(file_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"Missing required files: {', '.join(missing_files)}")
        return False
    return True


def get_dist_file_path(filename: str) -> str:
    """
    获取 dist 目录下文件的绝对路径。

    Args:
        filename: 文件名

    Returns:
        文件绝对路径
    """
    return os.path.join(DIST_DIR, filename)


def build() -> int:
    """
    执行打包流程。

    Returns:
        成功返回0，失败返回1
    """
    if not check_required_files():
        return 1

    print("Building The Bazaar Gate...")

    launcher_script_path = get_dist_file_path("launcher_tool.py")
    language_csv_path = get_dist_file_path("language.csv")

    try:
        PyInstaller.__main__.run(
            [
                launcher_script_path,
                "--onefile",
                "--windowed",
                f"--name={OUTPUT_NAME}",
                "--icon=NONE",
                f"--add-data={language_csv_path};.",
                "--clean",
                "--noconfirm",
            ]
        )

        print("\nBuild completed!")
        print(f"Executable created at: {os.path.join('dist', f'{OUTPUT_NAME}.exe')}")
        return 0

    except SystemExit as e:
        print(f"\nPyInstaller execution failed: {e}")
        return 1
    except OSError as e:
        print(f"\nFilesystem error: {e}")
        return 1
    except RuntimeError as e:
        print(f"\nBuild failed: {e}")
        return 1
    except ImportError as e:
        print(f"\nDependency import failed: {e}")
        return 1
    except ValueError as e:
        print(f"\nInvalid build argument: {e}")
        return 1
    except TypeError as e:
        print(f"\nInvalid build argument type: {e}")
        return 1
    except AttributeError as e:
        print(f"\nBuild tool error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(build())
