# 96 days project

Simple GUI application to track daily notes from **1 September** to **1 December 2025** with a modern, Apple-inspired interface.

## Requirements
- Python 3
- [`ttkbootstrap`](https://github.com/israel-dryer/ttkbootstrap)

Install the dependency:

```bash
pip install ttkbootstrap
```

## Usage
Run the application:

```bash
python memento_mori.py
```

Select a day in the grid, edit the note in the side editor, then press **Save Note**. Days with notes show a 📝 icon. Notes are stored in `notes.json` and automatically loaded at startup. Use the toolbar's **Export JSON** button to write them to disk.
