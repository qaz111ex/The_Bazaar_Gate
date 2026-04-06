# The Bazaar Gate

🎮 A patch tool specifically designed to bypass Tempo Launcher's official file integrity verification.

[中文](README.md)

## What does this tool do?

Tempo Launcher verifies game file integrity before launching the game. When mods are installed, the integrity check fails, preventing the game from starting with mods.

**This tool's purpose**: Automatically backup mod files before launch, delete mods to pass the integrity check, capture game launch parameters, then restore mod files - so you don't have to manually backup/restore mods every time.

## Features

- **Automatic Mod Management**: Automatically backup, delete, and restore mod files
- **Parameter Capture**: Capture game launch parameters from Tempo Launcher
- **Multi-Language Support**: Built-in Chinese, English, Traditional Chinese, Russian, Korean, Japanese - easily extensible
- **Modern UI**: Clean, flat design
- **Single-File Distribution**: Language files are embedded in the executable, no additional configuration files needed

## Downloads

Get the latest release from the [Releases](https://github.com/qaz111ex/The_Bazaar_Gate/releases) page.

## Usage

1. Run `TheBazaarGate.exe`
2. Set your game directory and launcher directory
3. Click "Start Game" - the tool will handle everything automatically

## Adding New Languages

Language files are embedded in the executable. To add a new language, follow these steps:

### Step 1: Edit the Language File

Edit `dist/language.csv` in the source code and add a new column with your language code as the header.

**Example - Adding French (fr):**

```csv
key,zh,en,fr
app_title,The Bazaar Gate,The Bazaar Gate,La Porte du Bazar
...
```

### Step 2: Translate All Keys

Copy an existing language column and translate all values. Ensure:
- Keep emoji indicators (📁, 🚀, 🎮, etc.) for visual consistency
- Maintain placeholder positions (`{}`) for format strings
- Every row has a translation for the new language

### Step 3: Rebuild the Executable

```bash
# Install dependencies
pip install -r requirements.txt

# Build executable (language file will be embedded automatically)
python build_exe.py
```

After building, the new language will appear in the program's language dropdown.

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

Click the "Capture Files" button in the program to configure the mod files list:
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
python build_exe.py
```

Output: `dist/TheBazaarGate.exe`

## Project Structure

```
The_Bazaar_Gate/
├── dist/
│   ├── launcher_tool.py        # Main application source
│   └── language.csv            # Language file (embedded when built)
├── .github/
│   ├── workflows/
│   │   └── ci.yml              # CI/CD pipeline
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md       # Bug report template
│       └── feature_request.md  # Feature request template
├── build_exe.py                # Build script
├── requirements.txt            # Python dependencies
├── SPEC.md                     # Project specification
├── README.md                   # Chinese version
├── README-en.md                # This file (English)
└── CONTRIBUTING.md             # Contribution guidelines
```

### Release Files

Only a single executable file is needed for release:
```
TheBazaarGate.exe    # Self-contained executable with all resources
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
