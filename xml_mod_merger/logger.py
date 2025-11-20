from typing import List
from .change_detector import ChangeSet, ChangeType
from .merge_engine import Conflict, MergeStats


class MergeLogger:
    def log_discovery(self, file_count: int, mod_count: int) -> None:
        print(f"=== XML Mod Merger ===")
        print(f"Discovered {file_count} file(s) to process")
        print(f"Processing {mod_count} mod director{'y' if mod_count == 1 else 'ies'}")
        print()
    
    def log_changes(self, mod_name: str, change_set: ChangeSet) -> None:
        # Count changes by type
        additions = sum(1 for c in change_set.changes if c.change_type == ChangeType.ADD)
        modifications = sum(1 for c in change_set.changes if c.change_type == ChangeType.MODIFY)
        deletions = sum(1 for c in change_set.changes if c.change_type == ChangeType.REMOVE)
        
        print(f"Changes detected in '{mod_name}':")
        print(f"  Additions: {additions}")
        print(f"  Modifications: {modifications}")
        print(f"  Deletions: {deletions}")
        print(f"  Total: {len(change_set.changes)}")
        print()
    
    def log_conflicts(self, conflicts: List[Conflict]) -> None:
        if not conflicts:
            print("No conflicts detected.")
            print()
            return
        
        print(f"=== CONFLICTS DETECTED: {len(conflicts)} ===")
        print()
        
        for i, conflict in enumerate(conflicts, 1):
            print(f"Conflict {i}:")
            print(f"  Element: {conflict.element_path}")
            if conflict.element_id:
                print(f"  ID: {conflict.element_id}")
            print(f"  Attribute: {conflict.attribute_name}")
            print(f"  Conflicting values:")
            for mod_name, value in conflict.conflicting_values.items():
                print(f"    {mod_name}: {value}")
            print()
    
    def log_completion(self, output_path: str, stats: MergeStats) -> None:
        print("=== Merge Complete ===")
        print(f"Output written to: {output_path}")
        print()
        print("Merge Statistics:")
        print(f"  Total changes applied: {stats.total_changes}")
        print(f"  Additions: {stats.additions}")
        print(f"  Modifications: {stats.modifications}")
        print(f"  Deletions: {stats.deletions}")
        print(f"  Conflicts: {stats.conflicts}")
        print()
