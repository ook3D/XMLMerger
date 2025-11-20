from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree
from dataclasses import dataclass


@dataclass
class FileSet:
    original: Optional[Path]
    mods: Dict[str, Path]  # mod_name -> file_path


class FileManager:
    def discover_files(self, original_dir: str, mod_dirs: List[str]) -> Dict[str, FileSet]:
        file_sets: Dict[str, FileSet] = {}
        original_path = Path(original_dir)
        
        # Scan original directory for XML files
        if original_path.exists() and original_path.is_dir():
            for xml_file in original_path.glob("*.xml"):
                filename = xml_file.name
                file_sets[filename] = FileSet(original=xml_file, mods={})
        
        # Scan each mod directory for corresponding XML files
        for mod_dir in mod_dirs:
            mod_path = Path(mod_dir)
            if not mod_path.exists() or not mod_path.is_dir():
                continue
            
            mod_name = mod_path.name
            
            for xml_file in mod_path.glob("*.xml"):
                filename = xml_file.name
                
                # Create FileSet if this is a new file (not in original)
                if filename not in file_sets:
                    file_sets[filename] = FileSet(original=None, mods={})
                
                # Add mod file to the FileSet
                file_sets[filename].mods[mod_name] = xml_file
        
        return file_sets
    
    def load_xml(self, file_path: str) -> ElementTree.ElementTree:
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"XML file not found: {file_path}")
        
        if not path.is_file():
            raise FileNotFoundError(f"Path is not a file: {file_path}")
        
        try:
            tree = ElementTree.parse(path)
            return tree
        except ElementTree.ParseError as e:
            raise ElementTree.ParseError(
                f"Failed to parse XML file '{file_path}': {str(e)}"
            ) from e
