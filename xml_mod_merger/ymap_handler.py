from xml.etree import ElementTree
from typing import Optional, List


class YmapHandler:
    # Metadata elements that should be preserved from the original
    METADATA_ELEMENTS = {
        'name',
        'parent',
        'flags',
        'contentFlags',
        'streamingExtentsMin',
        'streamingExtentsMax',
        'entitiesExtentsMin',
        'entitiesExtentsMax'
    }
    
    @staticmethod
    def is_ymap_file(tree: ElementTree.ElementTree) -> bool:
        root = tree.getroot()
        return root.tag == 'CMapData'
    
    @staticmethod
    def preserve_metadata(
        original: ElementTree.ElementTree,
        merged: ElementTree.ElementTree
    ) -> ElementTree.ElementTree:
        if not YmapHandler.is_ymap_file(original):
            return merged
        
        orig_root = original.getroot()
        merged_root = merged.getroot()
        
        # Preserve metadata elements from original
        for elem in orig_root:
            if elem.tag in YmapHandler.METADATA_ELEMENTS:
                # Remove existing metadata element if present
                existing = merged_root.find(elem.tag)
                if existing is not None:
                    merged_root.remove(existing)
                
                # Insert metadata element at the beginning (before entities)
                # Find the position to insert (before entities container)
                insert_pos = 0
                for i, child in enumerate(merged_root):
                    if child.tag == 'entities':
                        insert_pos = i
                        break
                    insert_pos = i + 1
                
                # Create a copy of the metadata element
                metadata_copy = ElementTree.Element(elem.tag)
                metadata_copy.text = elem.text
                metadata_copy.tail = elem.tail
                metadata_copy.attrib.update(elem.attrib)
                
                # Insert at the appropriate position
                merged_root.insert(insert_pos, metadata_copy)
        
        return merged
    
    @staticmethod
    def ensure_entities_container(tree: ElementTree.ElementTree) -> ElementTree.ElementTree:
        if not YmapHandler.is_ymap_file(tree):
            return tree
        
        root = tree.getroot()
        
        # Check if entities container exists
        entities = root.find('entities')
        if entities is None:
            # Create entities container
            entities = ElementTree.Element('entities')
            root.append(entities)
        
        return tree
    
    @staticmethod
    def validate_structure(tree: ElementTree.ElementTree) -> List[str]:
        errors = []
        
        if not YmapHandler.is_ymap_file(tree):
            return errors
        
        root = tree.getroot()
        
        # Check for required CMapData root
        if root.tag != 'CMapData':
            errors.append("Root element must be CMapData")
        
        # Check for entities container
        entities = root.find('entities')
        if entities is None:
            errors.append("Missing entities container")
        else:
            # Check that entities contains Item elements
            items = list(entities)
            if items:
                for item in items:
                    if item.tag != 'Item':
                        errors.append(f"Entities container should only contain Item elements, found: {item.tag}")
                        break
        
        return errors
