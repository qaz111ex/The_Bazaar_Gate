# Contributing to The Bazaar Gate

Thank you for your interest in contributing!

## Development Workflow

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/qaz111ex/The_Bazaar_Gate.git
cd The_Bazaar_Gate
```

### 2. Create a Feature Branch

We use a feature branch workflow. **Never commit directly to main.**

```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 3. Make Your Changes

- Write clean, readable code following PEP 8
- Add/update translations in `dist/language.csv` if needed
- Test your changes thoroughly
- Keep commits small and focused

### 4. Commit Your Changes

We use Conventional Commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

**Examples:**
```bash
git commit -m "feat(ui): add language switcher component"
git commit -m "fix(core): handle missing game directory gracefully"
git commit -m "docs(readme): update installation instructions"
```

### 5. Push and Create Pull Request

```bash
git push origin feat/your-feature-name
```

Then create a Pull Request on GitHub.

## Pull Request Guidelines

### PR Title

Use descriptive titles with conventional commit format:
- `feat: add dark mode support`
- `fix: prevent crash on missing settings file`
- `docs: update language contribution guide`

### PR Description

Include the following sections:

```markdown
## Summary
Brief description of changes.

## Changes
- Change 1
- Change 2

## Testing
How was this tested?

## Screenshots (if applicable)
```

### Review Criteria

- [ ] Code follows project style
- [ ] Translations added/updated if needed
- [ ] No hardcoded strings (use language.csv)
- [ ] Error handling is appropriate
- [ ] Tests pass (if applicable)

## Code Review Process

1. All PRs require at least one review
2. Address reviewer feedback
3. Ensure all checks pass
4. Squashed merge to main

## Labels

We use these labels:

| Label | Description |
|-------|-------------|
| `bug` | Bug reports |
| `enhancement` | New features |
| `documentation` | Docs improvements |
| `good first issue` | Beginner-friendly |
| `help wanted` | Seeking contributors |
| `priority: high` | High priority |
| `status: in progress` | Being worked on |

## Issues

### Bug Reports

Open issues with:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment info (OS, version)

### Feature Requests

Open issues with:
- Problem you're solving
- Proposed solution
- Alternatives considered

## Development Setup

### Prerequisites

- Python 3.9+
- Windows OS
- Git

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

**Note**: The language file (`dist/language.csv`) is embedded in the executable during build. Users only need the single `.exe` file.

## Style Guide

### Python Code

- Follow PEP 8
- Use type hints where helpful
- Prefer explicit over implicit
- Use context managers for resources
- Catch specific exceptions

### UI Text

- All user-facing text must be in `dist/language.csv`
- Use translation keys, never hardcode strings
- Include emoji indicators for visual consistency
- Maintain placeholder positions (`{}`) for format strings

### Git Commits

- Use conventional commit format
- Keep messages concise (under 72 chars)
- Reference issues where applicable (#123)

## Adding New Languages

1. Edit `dist/language.csv` in the source code
2. Add a new column with the language code (e.g., `fr` for French)
3. Translate all values in the new column
4. Test by running from source: `python dist/launcher_tool.py`
5. Rebuild the executable: `python build_exe.py`
6. The new language will appear in the program's dropdown

### Translation Guidelines

- Keep emoji indicators (📁, 🚀, 🎮, etc.) for visual consistency
- Maintain placeholder positions (`{}`) for format strings
- Ensure every row has a translation for the new language
- Test the translation in the application before submitting

## Questions?

Feel free to open an issue for questions!
