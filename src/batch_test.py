import csv
import json
import time
from datetime import datetime
import traceback
from pathlib import Path

import matplotlib
matplotlib.use("Agg") #no GUI

import matplotlib.pyplot as plt
from pycalphad import Database, binplot, variables as v

ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = ROOT / "Databases" / "Binary"
INDEX_PATH = ROOT / "database_index.json"

REPORT_PATH = ROOT / "batch_results.csv"
ERROR_LOG_PATH = ROOT / "batch_errors.log"
TEMP_REPORT_PATH = ROOT / "batch_results.tmp"

#identical variables
T_MIN = 300
T_MAX = 3000
T_STEP = 10
X_STEP = 0.02
PRESSURE = 101325

COLUMNS = [
    "database", "elements", "status", "seconds", "error"
]

def load_index():
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    #takes both list and dictionary although the structure of my current index is dictionary    
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict): #I have eno idea
        entries = next(
            (
                value for value in data.values()
                if isinstance(value, list)
                and (not value or isinstance(value[0], dict))
            ),
            None,
        )
    else:
        raise ValueError("invalid database index format.")
    
    if entries is None:
        raise ValueError("could not find database entry in the index")
    
    return entries

def get_elements(entry):
    elements = entry.get("elements", [])
    
    if isinstance(elements, str):
        elements = elements.replace(",", " ").split()
        
    if not isinstance(elements, (list, tuple, set)):
        raise ValueError(f"invalid elements field: {elements!r}")
    
    elements = {
        str(element).strip().upper()
        for element in elements
        if str(element).strip()
    }
    
    if len(elements) != 2:
        raise ValueError(f"expected two elements, found {sorted(elements)}")
    
    return (sorted(elements))

def get_database_path(entry):
    filename = entry.get("file")
    
    if not filename:
        raise ValueError("missing 'file' field in the index entry")
    
    #matching folder structor of generator
    path = DATABASE_DIR / Path(filename).name
    
    if not path.is_file():
        raise FileNotFoundError(f"Database not found: {path}")
    
    return path

def save_results(results):
    #writes a temporary CSV
    with open(
        TEMP_REPORT_PATH, "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(results)
        f.flush()
    
    TEMP_REPORT_PATH.replace(REPORT_PATH)
    
def load_previous_results():
    if not REPORT_PATH.exists():
        return []

    try:
        with open(
            REPORT_PATH, "r", newline="", encoding="utf-8-sig"
        ) as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return []
            return [
                row for row in reader
                if row.get("database")
            ]
    except (OSError, csv.Error, UnicodeError) as exc:
        print(f"could not read previous CSV: {exc}")
        print("Starting a fresh report. old file is prreserved")
        backup = REPORT_PATH.with_name("batch_results_old.csv")
        if not backup.exists():
            REPORT_PATH.replace(backup)
        return []

def log_error(filename, elements, exc):
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as log:
        log.write("\n" + "=" * 80 + "\n")
        log.write(f"Database: {filename}\n")
        log.write(f"Elements: {elements}\n")
        log.write(traceback.format_exc())

def test_database(entry):
    start = time.perf_counter()
    
    filename = str(entry.get("file", "<unknown>"))
    elements = ""
    status = "FAILED"
    error = ""
    
    try:
        pair = get_elements(entry)
        elements = "-".join(pair)
        path = get_database_path(entry)
        filename = path.name
        
        database = Database(str(path))
        
        available_elements = {
            str(element).upper()
            for element in database.elements
        }
        
        missing = set(pair) - available_elements
        
        if missing:
            raise ValueError(f"missing indexed elements from database: {sorted(missing)}")
        
        components = [*pair, "VA"]
        
        #use all phases
        phases = sorted(
            phase for phase in database.phases
            if str(phase).upper() != "VA"
        )

        if not phases:
            raise ValueError("no phases found")
        
        #same calculator as generator
        binplot(
            database,
            components,
            phases,
            {
                v.X(pair[0]): (0, 1, X_STEP),
                v.T: (T_MIN, T_MAX, T_STEP),
                v.P: PRESSURE,
            },
        )
        
        #reaching here means the diagram was generatod (not necessarily correctly tho)
        status = "SUCCESS"
        
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        log_error(filename, elements, exc)

            
    finally:
        plt.close("all")
        
    elapsed = round(time.perf_counter() - start, 2)
    
    return {
        "database": filename,
        "elements": elements,
        "status": status,
        "seconds": elapsed,
        "error": error,
    }
    
def main():
    print("=== CALPHAD Database Batch Tester ===")
    
    entries = load_index()
    results = load_previous_results()
    
    #successful databases are skipped; failed ones retried.
    successful = {
        row["database"].lower()
        for row in results
        if row.get("status") == ("SUCCESS")
    }
    
    #most recent result for each file
    results_by_name = {
        row["database"].lower(): row for row in results
    }
    
    total = len(entries)
    print(f"Databases in index: {total}")
    print(f"Already successful: {len(successful)}")
    print("Saving results after each database.\n")
    
    for number, entry in enumerate(entries, start=1):
        filename = str(entry.get("file", "<unknown>"))
        
        #avoid testing duplicates
        key = Path(filename).name.lower()
        
        if key in successful:
            print(f"[{number}/{total}] [SKIP] {filename}")
            continue
        
        print(f"\n[{number}/{total}] Testing {filename}")
        print(f"Started: {datetime.now().isoformat(timespec='seconds')}")
        
        result = test_database(entry)
        results_by_name[key] = result
        
        #save immediately
        results = list(results_by_name.values())
        save_results(results)
        
        print(
            f"[{result['status']}] {result['database']}"
            f"| {result['seconds']}s"
            + (f" | {result['error']}" if result["error"] else "")
        )
        print(f"Progress saved at {datetime.now().isoformat(timespec='seconds')}")
        
        if result["status"] == "SUCCESS":
            successful.add(key)
    
    results = list(results_by_name.values())
    save_results(results)
    
    passed = sum(r["status"] == "SUCCESS" for r in results)
    failed = len(results) - passed
    
    print("\n=== BATCH TEST COMPLETE ===")
    print(f"Tested: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"CSV: {REPORT_PATH}")
    print(f"Error log: {ERROR_LOG_PATH}")
    


if __name__ == "__main__":
    main()
    
        