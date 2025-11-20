from xml.etree import ElementTree
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class ChangeType(Enum):
    ADD = "add"
    REMOVE = "remove"
    MODIFY = "modify"


@dataclass
class Change:
    change_type: ChangeType
    element_path: str  # XPath-like path to element
    element_id: Optional[str]  # GUID or other identifier
    attribute_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    mod_source: str  # Which mod made this change


@dataclass
class ChangeSet:
    mod_name: str
    changes: List[Change]


class ChangeDetector:
    def __init__(self, mod_name: str = "unknown"):
        self.mod_name = mod_name
    
    def detect_changes(
        self, 
        original: ElementTree.ElementTree, 
        modified: ElementTree.ElementTree
    ) -> ChangeSet:
        changes = []
        
        orig_root = original.getroot()
        mod_root = modified.getroot()
        
        # Compare the root elements
        root_changes = self.compare_elements(orig_root, mod_root, f"/{orig_root.tag}")
        changes.extend(root_changes)
        
        return ChangeSet(mod_name=self.mod_name, changes=changes)
    
    def compare_elements(
        self, 
        orig_elem: ElementTree.Element, 
        mod_elem: ElementTree.Element, 
        path: str,
        parent_guid: Optional[str] = None
    ) -> List[Change]:
        changes = []
        
        # Compare attributes
        orig_attribs = orig_elem.attrib
        mod_attribs = mod_elem.attrib
        
        # Get element identifier (GUID if available, otherwise use parents GUID)
        element_id = mod_attribs.get('guid') or orig_attribs.get('guid')
        # If not found as attribute, check for <guid> child element
        if not element_id:
            guid_elem = mod_elem.find('guid') or orig_elem.find('guid')
            if guid_elem is not None:
                element_id = guid_elem.attrib.get('value')
        # Fall back to parent GUID if still not found
        if not element_id:
            element_id = parent_guid
        
        # Check for modified attributes
        all_attrib_keys = set(orig_attribs.keys()) | set(mod_attribs.keys())
        for attr_name in all_attrib_keys:
            orig_value = orig_attribs.get(attr_name)
            mod_value = mod_attribs.get(attr_name)
            
            if orig_value != mod_value:
                changes.append(Change(
                    change_type=ChangeType.MODIFY,
                    element_path=path,
                    element_id=element_id,
                    attribute_name=attr_name,
                    old_value=orig_value,
                    new_value=mod_value,
                    mod_source=self.mod_name
                ))
        
        # Compare text content
        orig_text = (orig_elem.text or "").strip()
        mod_text = (mod_elem.text or "").strip()
        
        if orig_text != mod_text:
            changes.append(Change(
                change_type=ChangeType.MODIFY,
                element_path=path,
                element_id=element_id,
                attribute_name=None,
                old_value=orig_text,
                new_value=mod_text,
                mod_source=self.mod_name
            ))
        
        # Compare child elements, passing down the GUID
        child_changes = self._compare_children(orig_elem, mod_elem, path, element_id)
        changes.extend(child_changes)
        
        return changes
    
    def _compare_children(
        self,
        orig_elem: ElementTree.Element,
        mod_elem: ElementTree.Element,
        parent_path: str,
        parent_guid: Optional[str] = None
    ) -> List[Change]:
        changes = []
        
        # Get all children
        orig_children = list(orig_elem)
        mod_children = list(mod_elem)
        
        # Build dictionaries for GUID-based matching
        orig_guid_map = {}
        mod_guid_map = {}
        
        for child in orig_children:
            # Check for GUID as attribute
            guid = child.attrib.get('guid')
            # If not found, check for <guid> child element
            if not guid:
                guid_elem = child.find('guid')
                if guid_elem is not None:
                    guid = guid_elem.attrib.get('value')
            if guid:
                orig_guid_map[guid] = child
        
        for child in mod_children:
            # Check for GUID as attribute
            guid = child.attrib.get('guid')
            # If not found, check for <guid> child element
            if not guid:
                guid_elem = child.find('guid')
                if guid_elem is not None:
                    guid = guid_elem.attrib.get('value')
            if guid:
                mod_guid_map[guid] = child
        
        # Track which children have been matched
        matched_orig_indices = set()
        matched_mod_indices = set()
        
        # First pass: Match by GUID
        for guid, mod_child in mod_guid_map.items():
            if guid in orig_guid_map:
                # Found matching element by GUID
                orig_child = orig_guid_map[guid]
                orig_idx = orig_children.index(orig_child)
                mod_idx = mod_children.index(mod_child)
                
                matched_orig_indices.add(orig_idx)
                matched_mod_indices.add(mod_idx)
                
                # Recursively compare matched elements, passing the GUID down
                child_path = f"{parent_path}/{mod_child.tag}[@guid='{guid}']"
                child_changes = self.compare_elements(orig_child, mod_child, child_path, guid)
                changes.extend(child_changes)
        
        # Second pass: Match remaining elements by position and tag
        orig_unmatched = [(i, child) for i, child in enumerate(orig_children) 
                         if i not in matched_orig_indices]
        mod_unmatched = [(i, child) for i, child in enumerate(mod_children) 
                        if i not in matched_mod_indices]
        
        # Try to match by tag and position
        for orig_idx, orig_child in orig_unmatched[:]:
            for mod_idx, mod_child in mod_unmatched[:]:
                if orig_child.tag == mod_child.tag:
                    # Match found
                    matched_orig_indices.add(orig_idx)
                    matched_mod_indices.add(mod_idx)
                    orig_unmatched.remove((orig_idx, orig_child))
                    mod_unmatched.remove((mod_idx, mod_child))
                    
                    # Recursively compare, passing down parent GUID
                    child_path = f"{parent_path}/{mod_child.tag}[{mod_idx}]"
                    child_changes = self.compare_elements(orig_child, mod_child, child_path, parent_guid)
                    changes.extend(child_changes)
                    break
        
        # Remaining unmatched original children are deletions
        for orig_idx, orig_child in orig_unmatched:
            element_id = orig_child.attrib.get('guid')
            child_path = f"{parent_path}/{orig_child.tag}"
            if element_id:
                child_path += f"[@guid='{element_id}']"
            else:
                child_path += f"[{orig_idx}]"
            
            changes.append(Change(
                change_type=ChangeType.REMOVE,
                element_path=child_path,
                element_id=element_id,
                attribute_name=None,
                old_value=None,
                new_value=None,
                mod_source=self.mod_name
            ))
        
        # Remaining unmatched mod children are additions
        for mod_idx, mod_child in mod_unmatched:
            element_id = mod_child.attrib.get('guid')
            child_path = f"{parent_path}/{mod_child.tag}"
            if element_id:
                child_path += f"[@guid='{element_id}']"
            else:
                child_path += f"[{mod_idx}]"
            
            changes.append(Change(
                change_type=ChangeType.ADD,
                element_path=child_path,
                element_id=element_id,
                attribute_name=None,
                old_value=None,
                new_value=None,
                mod_source=self.mod_name
            ))
        
        return changes
