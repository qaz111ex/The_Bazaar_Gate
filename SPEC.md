# The Bazaar Gate - Project Specification

## Overview

**Project Name**: The Bazaar Gate
**Type**: Windows Desktop Application (The Bazaar launcher helper)
**Core Functionality**: Bypasses Tempo Launcher's file integrity verification by automating mod backup/deletion/capture/restore workflow
**Target Users**: Gamers who want to use mods with games that require Tempo Launcher

## Technology Stack

- **Language**: Python 3.9+
- **GUI Framework**: Tkinter (ttk widgets)
- **Platform**: Windows only (uses win32gui, psutil)
- **Build Tool**: PyInstaller
- **Dependencies**:
  - psutil (process management)
  - pywin32 (Windows API)

## Features

### Core Features

1. **Multi-Language Support**
   - CSV-based translation system
   - Language file embedded in executable
   - Runtime language switching
   - Auto-detect system language
   - Extensible: add new languages by modifying source and rebuilding

2. **Path Management**
   - Game directory selection with validation
   - Launcher directory selection with auto-detection
   - Default path detection
   - Persistent settings storage

3. **Mod Management**
   - Configurable mod file list
   - Automatic backup before launch
   - Automatic restore after parameter capture
   - Support for files and folders

4. **Parameter Capture**
   - Launch Tempo Launcher automatically
   - Wait for user interaction (click PLAY)
   - Capture command-line parameters
   - Close game process gracefully

5. **Modern UI**
   - Flat design with card-based layout
   - Dark terminal-style log output
   - Color-coded status messages
   - Responsive layout

6. **Single-File Distribution**
   - All resources embedded in executable
   - No external configuration files needed
   - Portable - just run and go

## UI/UX Specification

### Window Configuration

- **Default Size**: 500 x 600 pixels
- **Minimum Size**: 450 x 500 pixels
- **Resizable**: Yes
- **Title**: "The Bazaar Gate" (localized)

### Color Scheme

| Element | Color |
|---------|-------|
| Background | #f0f2f5 |
| Card Background | #ffffff |
| Primary Button | #0078d4 |
| Primary Button Hover | #106ebe |
| Text Primary | #1a1a1a |
| Text Secondary | #333333 |
| Text Hint | #888888 |
| Success | #00ff00 |
| Error | #ff0000 |
| Warning | #ffa500 |
| Log Background | #1e1e1e |
| Log Text | #cccccc |

### Typography

- **Title**: Microsoft YaHei UI, 16px, Bold
- **Header**: Microsoft YaHei UI, 11px, Bold
- **Label**: Microsoft YaHei UI, 10px
- **Log**: Consolas, 9px

### Layout Structure

```
┌────────────────────────────────────┐
│  [Title: 🎮 The Bazaar Gate]       │
├────────────────────────────────────┤
│  [🌐 Language ▼] [⚙️ Settings]     │  <- Language Card
├────────────────────────────────────┤
│  📁 Game Directory                 │
│  [________________] [Browse]      │  <- Settings Card
│                                    │
│  🚀 Launcher Directory             │
│  [________________] [Browse]      │
├────────────────────────────────────┤
│  [    🎯 启动游戏    ]             │  <- Button Card
├────────────────────────────────────┤
│  [Status: ✅ Ready]                │  <- Status Label
├────────────────────────────────────┤
│  📋 Operation Log                  │
│  ┌──────────────────────────────┐  │
│  │ [Dark terminal log output]   │  │  <- Log Card
│  │                              │  │
│  └──────────────────────────────┘  │
└────────────────────────────────────┘
```

### Settings Page Layout

```
┌────────────────────────────────────┐
│  [← Back] [📦 Mod Files Config]    │
├────────────────────────────────────┤
│  📝 Mod Files List (click to edit) │
│  📖 Enter one file/folder per...  │
│  ┌──────────────────────────────┐  │
│  │ [Text editor with mod list]  │  │
│  │                              │  │
│  └──────────────────────────────┘  │
│  [     💾 Save Settings     ]      │
└────────────────────────────────────┘
```

## Data Flow

### Settings Storage

**File**: `settings.txt` (JSON format, created in the program directory at runtime)

```json
{
  "game_path": "C:\\path\\to\\game",
  "launcher_path": "C:\\path\\to\\launcher",
  "language": "zh",
  "mod_items": ["BepInEx", "BazaarPlusPlus", "doorstop_config.ini", "winhttp.dll"]
}
```

### Language File Format

**File**: `dist/language.csv` (embedded in executable at build time)

```csv
key,zh,en
app_title,The Bazaar Gate,The Bazaar Gate
title_with_emoji,🎮 The Bazaar Gate,🎮 The Bazaar Gate
...
```

**Rules**:
- Column 1: Translation key (unique identifier)
- Columns 2+: Language codes (zh, en, ja, etc.)
- Format strings use `{}` placeholders
- Multiline values should be quoted

## Launch Workflow

### Step 1: Backup Mods
```
1.1. Get list of mod files from mod_items
1.2. For each existing file/folder:
     - Copy to mod_backup/ directory
     - Delete from game directory
1.3. Log operation results
```

### Step 2: Capture Parameters
```
2.1. Launch Tempo Launcher
2.2. Wait for launcher window (30s timeout)
2.3. Wait for game process (120s timeout)
2.4. Capture command-line parameters
2.5. Terminate game process gracefully
```

### Step 3: Restore Mods
```
3.1. Copy files from mod_backup/ back to game directory
3.2. Delete mod_backup/ folder
3.3. Log operation results
```

### Step 4: Launch Game
```
4.1. Launch game with captured parameters
4.2. Exit application
```

## Error Handling

| Error | Handling |
|-------|----------|
| Game path not set | Show error dialog, abort |
| Game exe not found | Show error dialog, abort |
| Launcher exe not found | Show error dialog, abort |
| Backup failed | Show error, try cleanup, abort |
| Delete mods failed | Restore backups, show error, abort |
| Parameter capture timeout | Show error, try cleanup, abort |
| Restore failed | Log error, continue |
| Settings save failed | Log error, continue |

## Security Considerations

- No network communication required
- Local file operations only
- No sensitive data stored
- Executable runs with user privileges

## Build Configuration

### PyInstaller Settings

- **Output Name**: TheBazaarGate.exe
- **Mode**: Onefile, windowed (no console)
- **Data Files**: language.csv (embedded)
- **Hidden Imports**: psutil, win32gui, win32con, pywintypes, shlex

### File Structure

```
Source:
The_Bazaar_Gate/
├── dist/
│   ├── launcher_tool.py        # Main application source
│   └── language.csv            # Language file (embedded when built)
├── build_exe.py                # Build script
└── requirements.txt            # Python dependencies

Build Output:
dist/TheBazaarGate.exe          # Self-contained executable
```

## Internationalization

### Supported Languages

| Code | Language | Status |
|------|----------|--------|
| zh | Chinese (Simplified) | Default |
| en | English | Full |
| zh_Hant | Chinese (Traditional) | Full |
| ru | Russian | Full |
| ko | Korean | Full |
| ja | Japanese | Full |

### Adding New Languages

1. Edit `dist/language.csv` in source code
2. Add new column with language code
3. Translate all values
4. Rebuild executable with `python build_exe.py`
5. New language will appear in dropdown automatically

### Translation Keys

All UI text must use translation keys. No hardcoded strings allowed.

## Future Enhancements

- [ ] Custom mod file patterns (regex support)
- [ ] Multiple mod profiles
- [ ] Backup versioning
- [ ] Cross-platform support (Linux/macOS)
- [ ] Configurable timeouts
- [ ] Dark/Light theme toggle
- [ ] Log export functionality
