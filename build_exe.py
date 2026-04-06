"""
The Bazaar Gate 打包脚本

使用 PyInstaller 将启动器打包为独立的可执行文件。

Author: The Bazaar Gate Team
Version: 1.1.0
"""

import PyInstaller.__main__
import os
import sys
from typing import List


DIST_DIR: str = 'dist'
OUTPUT_NAME: str = 'TheBazaarGate'
REQUIRED_FILES: List[str] = ['launcher_tool.py', 'language.csv']


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
        print(f"错误: 缺少必需文件: {', '.join(missing_files)}")
        return False
    return True


def build() -> int:
    """
    执行打包流程。
    
    Returns:
        成功返回0，失败返回1
    """
    if not check_required_files():
        return 1
    
    print("开始打包 The Bazaar Gate...")
    
    language_csv_path = os.path.join(DIST_DIR, 'language.csv')
    
    try:
        PyInstaller.__main__.run([
            os.path.join(DIST_DIR, 'launcher_tool.py'),
            '--onefile',
            '--windowed',
            f'--name={OUTPUT_NAME}',
            '--icon=NONE',
            f'--add-data={language_csv_path};.',
            '--clean',
            '--noconfirm'
        ])
        
        print(f"\n✅ 打包完成！")
        print(f"可执行文件位于: dist/{OUTPUT_NAME}.exe")
        return 0
        
    except PyInstaller.__main__.PyInstallerError as e:
        print(f"\n❌ PyInstaller 错误: {e}")
        return 1
    except OSError as e:
        print(f"\n❌ 文件系统错误: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 打包失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(build())
