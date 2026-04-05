import PyInstaller.__main__
import os
import sys

PyInstaller.__main__.run([
    'launcher_tool.py',
    '--onefile',
    '--windowed',
    '--name=BazaarModLauncher',
    '--icon=NONE',
    '--add-data=language.csv;language.csv',
    '--clean',
    '--noconfirm'
])

print("\n✅ 打包完成！")
print("可执行文件位于: dist/BazaarModLauncher.exe")
