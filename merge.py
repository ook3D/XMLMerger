import sys
from pathlib import Path
from xml_mod_merger.cli import main as cli_main


def run_merge():
    print("Starting XML Mod Merger...")
    print("-" * 60)
    
    sys.argv = [
        "merge.py",
        "--original", "original",
        "--mods", "mod1", "mod2",
        "--output", "combined",
        "--strategy", "last_wins"
    ]
    
    # Run the CLI
    try:
        cli_main()
        print("\n" + "=" * 60)
        print("Merge completed successfully!")
        print("Check the 'combined' directory for merged files.")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\nError during merge: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(run_merge())
