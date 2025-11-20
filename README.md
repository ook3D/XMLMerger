# XML Mod Merger

A Python tool for intelligently merging XML modifications from multiple mod directories. Designed for game modding scenarios where multiple mods modify the same base XML files.

## Quick Start

Simply run the master merge script:

```bash
python merge.py
```

This will automatically merge all mods from `mod1` and `mod2` directories with the `original` directory and output the combined result to the `combined` directory.

## Project Structure

```
xml-mod-merger/
├── xml_mod_merger/          # Main package
│   ├── __init__.py
│   ├── file_manager.py      # File discovery and loading
│   ├── change_detector.py   # Change detection logic
│   ├── merge_engine.py      # Merge and conflict resolution
│   ├── output_writer.py     # XML output generation
│   ├── logger.py            # Logging functionality
│   ├── ymap_handler.py      # YMAP-specific handling
│   └── cli.py               # Command-line interface
├── original/                # Original unmodified XML files
├── mod1/                    # First mod directory
├── mod2/                    # Second mod directory
├── combined/                # Output directory (generated)
├── merge.py                 # Master merge script
└── README.md               # This file
```

## Usage

### Simple Usage (Recommended)

Run the master script to merge with default settings:

```bash
python merge.py
```

### Advanced Usage

Use the CLI directly for custom configurations:

```bash
python -m xml_mod_merger.cli --original <original_dir> --mods <mod1_dir> <mod2_dir> --output <output_dir>
```

#### Conflict Resolution Strategies

- `last_wins` (default): Last mod takes precedence in conflicts
- `first_wins`: First mod takes precedence in conflicts
- `fail_on_conflict`: Abort merge and report conflicts

Example:
```bash
python -m xml_mod_merger.cli --original original --mods mod1 mod2 --output combined --strategy first_wins
```

## Features

- **GUID-based entity matching**: Intelligently matches entities across files using unique identifiers
- **Change detection**: Identifies additions, modifications, and deletions
- **Conflict detection**: Reports when multiple mods modify the same data
- **Multiple conflict resolution strategies**: Choose how to handle conflicts
- **YMAP support**: Specialized handling for GTA V ymap files
- **Clear logging**: Detailed output of merge operations and statistics
