import os
from xml.etree import ElementTree
from pathlib import Path
from .ymap_handler import YmapHandler


class OutputWriter:
    def write_xml(self, tree: ElementTree.ElementTree, output_path: str) -> None:
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Validate ymap structure if applicable
            if YmapHandler.is_ymap_file(tree):
                validation_errors = YmapHandler.validate_structure(tree)
                if validation_errors:
                    raise ValueError(f"Invalid ymap structure: {', '.join(validation_errors)}")
            
            # Format the XML with proper indentation
            formatted_xml = self.format_xml(tree)
            
            # Write to file
            with open(output_path, 'w', encoding='UTF-8') as f:
                f.write(formatted_xml)
                
        except (OSError, IOError) as e:
            raise IOError(f"Failed to write XML to {output_path}: {e}")
    
    def format_xml(self, tree: ElementTree.ElementTree) -> str:
        # Apply indentation to the tree
        self._indent(tree.getroot())
        
        # Convert to string with XML declaration
        xml_str = ElementTree.tostring(
            tree.getroot(),
            encoding='unicode',
            method='xml'
        )
        
        # Add XML declaration manually to ensure UTF-8 encoding is specified
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    
    def _indent(self, elem, level=0):
        indent = "\n" + " " * level
        
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + " "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent
