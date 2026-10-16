import csv
import json
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
from pycalphad import Database, binplot, variables as v
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = ROOT / "Databases" / "Binary"
INDEX_PATH = ROOT / "database_index.json"
REPORT_PATH = ROOT / "batch_results.csv"
ERROR_LOG_PATH = ROOT / "batch_errors.log"
TEMP_REPORT_PATH = ROOT / "batch_results.tmp"
CATEGORIZED_REPORT = ROOT / "failed_categorized.csv"

T_MIN = 300
T_MAX = 3000
T_STEP = 10
X_STEP = 0.02
PRESSURE = 101325

df= pd.read_csv(REPORT_PATH)

failed = df[df["status"] == "FAILED"].copy()
failed.sort_values(
    ["error"],
    ascending = [False],
    inplace = True
)
failed.to_csv(CATEGORIZED_REPORT, index=False)


