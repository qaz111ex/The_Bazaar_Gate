# The Bazaar Gate

🎮 A patch tool specifically designed to bypass Tempo Launcher's official file integrity verification.

[中文](README_cn.md)

## What does this tool do?

Tempo Launcher verifies game file integrity before launching the game. When mods are installed, the integrity check fails, preventing the game from starting with mods.

**This tool's purpose**: Automatically backup mod files before launch, delete mods to pass the integrity check, capture game launch parameters, then restore mod files - so you don't have to manually backup/restore mods every time.

## Features

- **Automatic Mod Management**: Automatically backup, delete, and restore mod files
- **Parameter Capture**: Capture game launch parameters from Tempo Launcher
- **Multi-Language Support**: Built-in Chinese (zh) and English (en), easily extensible
- **Modern UI**: Clean, flat design

## Downloads

Get the latest release from the [Releases](https://github.com/YOUR_USERNAME/TheBazaarGate/releases) page.

## Usage

1. Extract `TheBazaarGate.zip`
2. Run `TheBazaarGate.exe`
3. Set your game directory and launcher directory
4. Click "Start Game" - the tool will handle everything automatically

## Adding New Languages

The application supports unlimited language columns in `language.csv`.

### Step 1: Edit language.csv

Open `language.csv` in any text editor and add a new column with your language code as the header.

**Example - Adding Japanese (ja):**

```csv
key,zh,en,ja
app_title,The Bazaar Gate,The Bazaar Gate,ザ・バザール・ゲート
...
```

### Step 2: Translate all keys

Copy an existing language column and translate all values. The application will automatically detect the new language column and add it to the dropdown.

### Translation Guidelines

- Keep emoji indicators (📁, 🚀, 🎮, etc.) for visual consistency
- Maintain placeholder positions (`{}`) for format strings
- Ensure line breaks are preserved (wrap in quotes if needed)

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  1. Backup Mod Files                                        │
│     - Detect mod files in game directory                    │
│     - Backup to mod_backup/ folder                          │
│     - Delete mod files from game directory                  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Launch Tempo Launcher & Capture                         │
│     - Start Tempo Launcher                                  │
│     - Wait for user to click PLAY                           │
│     - Capture game launch parameters                        │
│     - Close game process                                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Restore Mod Files                                       │
│     - Restore backed-up mod files to game directory         │
│     - Clean up backup folder                                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  4. Launch Game                                             │
│     - Start game with captured parameters                   │
│     - Exit launcher                                         │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

Settings are stored in `settings.txt` in the same directory as the executable:

```json
{
  "game_path": "C:\\path\\to\\game",
  "launcher_path": "C:\\path\\to\\launcher",
  "language": "zh",
  "mod_items": ["BepInEx", "BazaarPlusPlus", "doorstop_config.ini", "winhttp.dll"]
}
```

### Mod Files Configuration

The `mod_items` list defines which files/folders to backup before launching:
- Each line = one file or folder name
- Non-existent files are automatically skipped
- Supports both files (`.dll`) and folders

## Development

### Requirements

- Python 3.9+
- Windows OS (uses win32gui, psutil)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run from Source

```bash
python dist/launcher_tool.py
```

### Build Executable

```bash
pyinstaller --clean TheBazaarGate.spec
```

Output: `dist/TheBazaarGate.exe`

## Project Structure

```
TheBazaarGate/
├── dist/
│   ├── launcher_tool.py      # Main application
│   ├── language.csv          # Translation file
│   └── TheBazaarGate.exe    # Built executable
├── .github/
│   ├── workflows/
│   │   └── ci.yml            # CI/CD pipeline
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md     # Bug report template
│       └── feature_request.md # Feature request template
├── SPEC.md                   # Project specification
├── README_cn.md              # Chinese version
├── README_en.md              # This file (English)
└── CONTRIBUTING.md          # Contribution guidelines
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.