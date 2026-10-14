import json
from pathlib import Path

import matplotlib.pyplot as plt
from pycalphad import Database, binplot, variables as v

#all files are supposed to be in the same directory
ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = ROOT / "Databases" / "Binary"
INDEX_PATH = ROOT / "database_index.json"

def load_index():
    """Find and read the database index file"""
    index_path = ROOT / "database_index.json"
    
    if not index_path.exists():
        matches = list(ROOT.glob("*index*.json"))
        if len(matches) == 1:
            index_path = matches[0]
        else:
            raise FileNotFoundError("Ambiguous or missing database index file.")
        
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Supports both a list of databases and a dictionary of databases
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        entries = next(
            (
                value for value in data.values()
                if isinstance(value, list)
                and (not value or isinstance(value[0], dict))
            ),
            None,
        )
    else:
        raise ValueError("Invalid database index format.")
    
    return entries

def get_elements(entry):
    """Gets the elements"""
    elements = entry.get("elements",[])
    if isinstance(elements,str):
        elements = elements.replace(",", " ").split()
    if not elements:
        raise ValueError("Database entry missing 'elements' key.")
    
    return {str(element).upper() for element in elements}

def get_database_path(entry):
    """Gets the path to file"""
    filename = entry.get("file")
    if not filename:
        raise ValueError("Database entry missing 'file' key.")

    # database files are in the same directory
    path = DATABASE_DIR / Path(filename).name
    return path if path.is_file() else None

def choose_database(entries, element_a, element_b):
    """Chooses the database based on the elements"""
    required = {element_a.upper(), element_b.upper()}
    candidates = []
    
    for entry in entries:
        elements = get_elements(entry)
        path = get_database_path(entry)
        
        if path and required.issubset(elements):
            candidates.append((entry, path, elements))
    
    if not candidates:
        raise RuntimeError(f"No database found for elements: {required}")
    
    # Sort candidates by the number of elements (prefer fewer elements)
    candidates.sort(
        key=lambda item:(
            item[2] != required,
            item[0].get("number_of_elements", len(item[2])),
            item[1].name.lower(),
        )
    )
    
    print (f"\nDatabases found for elements {required}:")
    for i, (entry,path,elements) in enumerate(candidates, start=1):
        identifier = entry.get("identifier", "")
        print(f"{i}. {path.name} {identifier}")
    
    while True:
        choice = input("\nChoose a database by number: ").strip()
        try:
            selected = candidates[int(choice) - 1]
            return selected[1]  # Return the path of the selected database
        except (ValueError,IndexError):
            print("Enter a valid number.")

def choose_phases(database):
    phases = sorted(
        phase for phase in database.phases
        if phase.upper() not in {"VA"}
    )
    
    print("\nPhases available in this database:")
    for i, phase in enumerate(phases, start=1):
        print(f"{i}. {phase}")
    
    print(
        "\nEnter phase names separated by commas or type ALL to select all:"
    )
    
    while True:
        answer = input("Your choice: ").strip()
        
        if answer.upper() == "ALL":
            return phases
        
        selected = [name.strip().upper() for name in answer.split(",")]
        phase_lookup = {phase.upper(): phase for phase in phases}
        
        if selected and all(name in phase_lookup for name in selected):
            return list(dict.fromkeys(phase_lookup[name] for name in selected))  # Preserve order and remove duplicates
        
        print("one or more invalid phase names. try again.")
    
def ask_float(prompt, default, minimum=None, maximum=None):
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        try:
            value = float(raw) if raw else float(default)
            if minimum is not None and value < minimum:
                raise ValueError
            if maximum is not None and value > maximum:
                raise ValueError
            return value
        except ValueError:
            print(f"Enter a number within the range {minimum} to {maximum}.")

def main():
    print("=== Binary Phase Diagram Generator ===")
    
    entries = load_index()
    
    element_a = input("Enter the first element: ").strip().upper()
    element_b = input("Enter the second element: ").strip().upper()
    
    if not element_a or not element_b or element_a == element_b:
        raise ValueError("Invalid elements. Please enter two different elements.")
    
    t_min = ask_float("Enter minimum temperature (K)", 300, 1)
    t_max = ask_float("Enter maximum temperature (K)", 3000, t_min)
    t_step = ask_float("Enter temperature step (K)", 10, 0.1)
    
    x_step = ask_float("Enter composition step (mole fraction)", 0.02, 0.001, 1.0)
    pressure = ask_float("Enter pressure (Pa)", 101325, 1)
    
    if t_max <= t_min:
        raise ValueError("Maximum temperature must be greater than minimum temperature.")
    
    database_path = choose_database(entries, element_a, element_b)

    print(f"\nLoading {database_path.name} ...")
    database = Database(str(database_path))
    
    available_elements = {str(x).upper() for x in database.elements}
    missing = {element_a, element_b} - available_elements
    if missing:
        raise ValueError(f"Elements {missing} not found in the selected database.")
    
    phases = choose_phases(database)
    
    components = [element_a, element_b, "VA"]
    
    print("\nGenerating phase diagram...")
    try:
        binplot(
            database,
            components,
            phases,
            {
                v.X(element_a): (0, 1, x_step),
                v.T: (t_min, t_max, t_step),
                v.P: pressure,
            },
        )
    except Exception as e:
        plt.close("all")
        raise RuntimeError(f"Failed to generate phase diagram: {e}") from e

    output_path = ROOT / f"{element_a}_{element_b}_phase_diagram.png"
    plt.gcf().savefig(output_path, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close("all")
    
    print(f"\nDiagram saved to:\n{output_path}")
    
if __name__ == "__main__":
    main()