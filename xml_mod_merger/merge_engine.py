from xml.etree import ElementTree
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import copy

from .change_detector import Change, ChangeSet, ChangeType
from .ymap_handler import YmapHandler


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""
    LAST_WINS = "last_wins"
    FIRST_WINS = "first_wins"
    FAIL_ON_CONFLICT = "fail_on_conflict"


@dataclass
class Conflict:
    """Represents a conflict between multiple mods."""
    element_path: str
    element_id: Optional[str]
    attribute_name: str
    conflicting_values: Dict[str, str]  # mod_name -> value


@dataclass
class MergeStats:
    """Statistics about the merge operation."""
    total_changes: int
    additions: int
    modifications: int
    deletions: int
    conflicts: int


@dataclass
class MergeResult:
    """Result of a merge operation."""
    merged_tree: ElementTree.ElementTree
    conflicts: List[Conflict]
    applied_changes: List[Change]
    stats: MergeStats


class MergeEngine:
    def __init__(self, strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WINS):
        self.strategy = strategy
    
    def _find_element(
        self, 
        root: ElementTree.Element, 
        path: str, 
        element_id: Optional[str]
    ) -> Optional[ElementTree.Element]:
        # Parse the path to navigate the tree
        parts = [p for p in path.split('/') if p]
        
        current = root
        for part in parts[1:]:  # Skip the first part (root tag)
            # Extract tag name and any predicates
            if '[' in part:
                tag = part[:part.index('[')]
                predicate = part[part.index('['):part.index(']')+1]
                
                # Handle GUID predicate
                if '@guid=' in predicate:
                    guid = predicate.split("'")[1]
                    found = False
                    for child in current:
                        if child.tag == tag:
                            # Check for GUID as attribute
                            child_guid = child.attrib.get('guid')
                            # If not found, check for <guid> child element
                            if not child_guid:
                                guid_elem = child.find('guid')
                                if guid_elem is not None:
                                    child_guid = guid_elem.attrib.get('value')
                            if child_guid == guid:
                                current = child
                                found = True
                                break
                    if not found:
                        return None
                # Handle index predicate
                elif predicate.startswith('[') and predicate.endswith(']'):
                    try:
                        index = int(predicate[1:-1])
                        # Get all children with matching tag
                        children = [c for c in current if c.tag == tag]
                        # If there's only one child with this tag, use it regardless of index
                        if len(children) == 1:
                            current = children[0]
                        elif index < len(children):
                            current = children[index]
                        else:
                            return None
                    except (ValueError, IndexError):
                        return None
            else:
                # Simple tag name
                found = False
                for child in current:
                    if child.tag == part:
                        current = child
                        found = True
                        break
                if not found:
                    return None
        
        return current
    
    def _find_parent(
        self, 
        root: ElementTree.Element, 
        path: str, 
        element_id: Optional[str]
    ) -> Optional[ElementTree.Element]:
        # Get parent path by removing the last component
        parts = [p for p in path.split('/') if p]
        if len(parts) <= 1:
            return None
        
        parent_path = '/' + '/'.join(parts[:-1])
        return self._find_element(root, parent_path, None)
    
    def _add_element(self, root: ElementTree.Element, change: Change) -> None:
        # Find the parent element
        parent = self._find_parent(root, change.element_path, change.element_id)
        if parent is None:
            return
        
        # Extract tag name from path
        parts = [p for p in change.element_path.split('/') if p]
        last_part = parts[-1]
        
        if '[' in last_part:
            tag = last_part[:last_part.index('[')]
        else:
            tag = last_part
        
        # Create new element
        new_elem = ElementTree.Element(tag)
        
        # Set GUID if available
        if change.element_id:
            new_elem.set('guid', change.element_id)
        
        # Add to parent
        parent.append(new_elem)
    
    def _calculate_stats(
        self, 
        applied_changes: List[Change], 
        conflicts: List[Conflict]
    ) -> MergeStats:
        additions = sum(1 for c in applied_changes if c.change_type == ChangeType.ADD)
        modifications = sum(1 for c in applied_changes if c.change_type == ChangeType.MODIFY)
        deletions = sum(1 for c in applied_changes if c.change_type == ChangeType.REMOVE)
        
        return MergeStats(
            total_changes=len(applied_changes),
            additions=additions,
            modifications=modifications,
            deletions=deletions,
            conflicts=len(conflicts)
        )
    
    def _resolve_conflicts(
        self, 
        all_changes: List[Change], 
        conflicts: List[Conflict]
    ) -> List[Change]:
        if self.strategy == ConflictResolutionStrategy.FAIL_ON_CONFLICT:
            if conflicts:
                raise ValueError(f"Merge failed due to {len(conflicts)} conflict(s)")
        
        # Build a set of conflicting change identifiers
        conflicting_keys = set()
        for conflict in conflicts:
            key = (conflict.element_path, conflict.element_id, conflict.attribute_name)
            conflicting_keys.add(key)
        
        # Separate non-conflicting and conflicting changes
        non_conflicting = []
        conflicting_changes = {}
        
        for change in all_changes:
            key = (change.element_path, change.element_id, change.attribute_name)
            if key in conflicting_keys:
                if key not in conflicting_changes:
                    conflicting_changes[key] = []
                conflicting_changes[key].append(change)
            else:
                non_conflicting.append(change)
        
        # Apply resolution strategy to conflicting changes
        resolved = []
        for key, changes in conflicting_changes.items():
            if self.strategy == ConflictResolutionStrategy.FIRST_WINS:
                resolved.append(changes[0])
            elif self.strategy == ConflictResolutionStrategy.LAST_WINS:
                resolved.append(changes[-1])
        
        return non_conflicting + resolved
    
    def merge_changes(
        self, 
        original: ElementTree.ElementTree, 
        change_sets: List[ChangeSet]
    ) -> MergeResult:
        # Detect conflicts first
        conflicts = self.detect_conflicts(change_sets)
        
        # Collect all changes
        all_changes = []
        for change_set in change_sets:
            all_changes.extend(change_set.changes)
        
        # Filter out conflicting changes based on strategy
        applied_changes = self._resolve_conflicts(all_changes, conflicts)
        
        # Apply changes to a copy of the original tree
        merged_tree = self.apply_changes(original, applied_changes)
        
        # Apply ymap-specific handling if this is a ymap file
        if YmapHandler.is_ymap_file(original):
            # Preserve metadata from original
            merged_tree = YmapHandler.preserve_metadata(original, merged_tree)
            # Ensure entities container exists
            merged_tree = YmapHandler.ensure_entities_container(merged_tree)
        
        # Calculate statistics
        stats = self._calculate_stats(applied_changes, conflicts)
        
        return MergeResult(
            merged_tree=merged_tree,
            conflicts=conflicts,
            applied_changes=applied_changes,
            stats=stats
        )
    
    def detect_conflicts(self, change_sets: List[ChangeSet]) -> List[Conflict]:
        conflicts = []
        
        # Group changes by element and attribute
        # Key: (element_path, element_id, attribute_name)
        # Value: List of (mod_name, change) tuples
        change_map: Dict[tuple, List[tuple]] = {}
        
        for change_set in change_sets:
            for change in change_set.changes:
                # Only modifications can conflict
                if change.change_type == ChangeType.MODIFY:
                    key = (change.element_path, change.element_id, change.attribute_name)
                    if key not in change_map:
                        change_map[key] = []
                    change_map[key].append((change_set.mod_name, change))
        
        # Check for conflicts (multiple mods modifying the same attribute)
        for key, mod_changes in change_map.items():
            if len(mod_changes) > 1:
                # Multiple mods are modifying the same attribute
                element_path, element_id, attribute_name = key
                
                # Check if the values are actually different
                values = {}
                for mod_name, change in mod_changes:
                    values[mod_name] = change.new_value
                
                # If all values are the same, it's not a conflict
                unique_values = set(values.values())
                if len(unique_values) > 1:
                    conflicts.append(Conflict(
                        element_path=element_path,
                        element_id=element_id,
                        attribute_name=attribute_name or "text",
                        conflicting_values=values
                    ))
        
        return conflicts
    
    def apply_changes(
        self, 
        tree: ElementTree.ElementTree, 
        changes: List[Change]
    ) -> ElementTree.ElementTree:
        # Create a deep copy to avoid modifying the original
        result_tree = copy.deepcopy(tree)
        root = result_tree.getroot()
        
        # Group changes by type for efficient processing
        additions = [c for c in changes if c.change_type == ChangeType.ADD]
        modifications = [c for c in changes if c.change_type == ChangeType.MODIFY]
        deletions = [c for c in changes if c.change_type == ChangeType.REMOVE]
        
        # Apply modifications first (they work on existing elements)
        for change in modifications:
            element = self._find_element(root, change.element_path, change.element_id)
            if element is not None:
                if change.attribute_name:
                    # Modify attribute
                    if change.new_value is not None:
                        element.set(change.attribute_name, change.new_value)
                    elif change.attribute_name in element.attrib:
                        del element.attrib[change.attribute_name]
                else:
                    # Modify text content
                    element.text = change.new_value
        
        # Apply deletions (remove elements)
        for change in deletions:
            element = self._find_element(root, change.element_path, change.element_id)
            if element is not None:
                parent = self._find_parent(root, change.element_path, change.element_id)
                if parent is not None:
                    parent.remove(element)
        
        # Apply additions (add new elements)
        for change in additions:
            self._add_element(root, change)
        
        return result_tree
