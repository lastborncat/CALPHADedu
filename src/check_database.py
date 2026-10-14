from pathlib import Path
import re
import json

PROJECT = Path(__file__).parent.parent
DATABASE_DIR = PROJECT / "Databases" / "Binary"
OUTPUT = PROJECT / "database_index.json"

def get_elements(tdb_file):
    """Extracts ELEMENT names from a .tdb file"""
    
    elements = []
    
    with open (tdb_file, "r", encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            
            if line.upper().startswith("ELEMENT"):
                parts = line.split()
                
                if len(parts) >= 2:
                    element = parts[1].upper()
                    
                    #ignore vacancy
                    if element != "VA" and element != "/-":
                        elements.append(element)
    
    return elements

def get_identifier(tdb_file):
    """Extracts the name for user friendliness"""
    
    pattern = re.compile(r'\bfrom\s+(.*?\(?\b(?:19|20)\d{2}\b\)?)')
    
    with open(tdb_file, "r", encoding="latin-1") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                return match.group(1).strip()

def get_phases(tdb_file):
    """Extracts the phase names from a .tdb file"""
    
    phases = []

    with open(tdb_file, "r", encoding='latin-1') as f:
        for line in f:
            line = line.strip()
            
            if line.upper().startswith("PHASE"):
                line = line.split()
                if len(line) >= 2:
                    phase = line[1].upper()
                    
                    if "LIQUID" in phase: #some issue with database where "LIQUID" is not cleanly written, so we just replace it with "LIQUID"
                        phase = "LIQUID"
                    if "GAS" in phase: #some issue with database where "GAS" is not cleanly written, so we just replace it with "GAS"
                        phase = "GAS"
                    if phase not in phases:
                        phases.append(phase)
                
    return phases

database_index = []

tdb_files = list(DATABASE_DIR.glob("*.tdb"))

print(f"Found {len(tdb_files)} TDB files.")
print("Reading databases...\n")

for i, tdb_file in enumerate(tdb_files, 1):
    identifier = get_identifier(tdb_file)
    elements = get_elements(tdb_file)
    phases = get_phases(tdb_file)
    
    database_index.append({
        "file": tdb_file.name,
        "identifier": identifier,
        "elements": elements,
        "phases": phases,
        "number_of_elements": len(elements)
    })
    
    if i % 100 == 0:
        print(f"processed {i}/{len(tdb_files)} files.")
        
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(database_index, f, indent=2)
    
print("\nDONE!")
print(f"index saved to {OUTPUT}")