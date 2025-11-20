import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree

from .file_manager import FileManager
from .change_detector import ChangeDetector
from .merge_engine import MergeEngine, ConflictResolutionStrategy
from .output_writer import OutputWriter
from .logger import MergeLogger


def parse_args():
    parser = argparse.ArgumentParser(
        description="XML Mod Merger - Intelligently merge XML modifications from multiple mod directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            # Merge mods with last-wins strategy (default)
            xml-mod-merger --original ./original --mods ./mod1 ./mod2 --output ./combined

            # Use first-wins strategy for conflicts
            xml-mod-merger --original ./original --mods ./mod1 ./mod2 --output ./combined --strategy first_wins

            # Fail on any conflicts
            xml-mod-merger --original ./original --mods ./mod1 ./mod2 --output ./combined --strategy fail_on_conflict
        """
    )
    
    parser.add_argument(
        "--original",
        required=True,
        help="Path to the original files directory"
    )
    
    parser.add_argument(
        "--mods",
        nargs="+",
        required=True,
        help="Paths to mod directories"
    )
    
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output directory"
    )
    
    parser.add_argument(
        "--strategy",
        choices=["last_wins", "first_wins", "fail_on_conflict"],
        default="last_wins",
        help="Conflict resolution strategy (default: last_wins)"
    )
    
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        
        # Initialize components
        file_manager = FileManager()
        logger = MergeLogger()
        
        # Map strategy string to enum
        strategy_map = {
            "last_wins": ConflictResolutionStrategy.LAST_WINS,
            "first_wins": ConflictResolutionStrategy.FIRST_WINS,
            "fail_on_conflict": ConflictResolutionStrategy.FAIL_ON_CONFLICT
        }
        strategy = strategy_map[args.strategy]
        merge_engine = MergeEngine(strategy=strategy)
        output_writer = OutputWriter()
        
        # Discover files
        file_sets = file_manager.discover_files(args.original, args.mods)
        
        if not file_sets:
            print("No XML files found to process.")
            return 0
        
        logger.log_discovery(len(file_sets), len(args.mods))
        
        # Process each file
        for filename, file_set in file_sets.items():
            print(f"Processing: {filename}")
            print("-" * 50)
            
            # Check if we have an original file
            if file_set.original is None:
                print(f"Warning: No original file found for {filename}, skipping.")
                print()
                continue
            
            # Load original file
            try:
                original_tree = file_manager.load_xml(str(file_set.original))
            except (FileNotFoundError, ElementTree.ParseError) as e:
                print(f"Error loading original file: {e}")
                return 1
            
            # Detect changes from each mod
            change_sets = []
            for mod_name, mod_path in file_set.mods.items():
                try:
                    mod_tree = file_manager.load_xml(str(mod_path))
                    detector = ChangeDetector(mod_name=mod_name)
                    change_set = detector.detect_changes(original_tree, mod_tree)
                    change_sets.append(change_set)
                    logger.log_changes(mod_name, change_set)
                except (FileNotFoundError, ElementTree.ParseError) as e:
                    print(f"Error loading mod file {mod_name}: {e}")
                    return 1
            
            # If no mods have this file, just copy the original
            if not change_sets:
                print(f"No modifications found for {filename}, copying original.")
                output_path = Path(args.output) / filename
                output_writer.write_xml(original_tree, str(output_path))
                print()
                continue
            
            # Merge changes
            try:
                merge_result = merge_engine.merge_changes(original_tree, change_sets)
            except ValueError as e:
                # This happens when strategy is fail_on_conflict and conflicts exist
                print(f"Error: {e}")
                return 2
            
            # Log conflicts
            logger.log_conflicts(merge_result.conflicts)
            
            # Write output
            output_path = Path(args.output) / filename
            try:
                output_writer.write_xml(merge_result.merged_tree, str(output_path))
                logger.log_completion(str(output_path), merge_result.stats)
            except IOError as e:
                print(f"Error writing output file: {e}")
                return 1
        
        print("All files processed successfully.")
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
