import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = Path(r"C:\Users\alfre\OneDrive\Documents\tesismestrado\Dados\tesisversionfinal\JSON")
OUTPUT_DIR = BASE_DIR / "output" / "fhir_bundles"
LOG_DIR = BASE_DIR / "logs"

ORGANIZATION_ID = "chuln"
ORGANIZATION_NAME = "Centro Hospitalar Universitário de Lisboa Norte"
ORGANIZATION_SYSTEM = "http://chuln.pt/organization"

PATIENT_ID_SYSTEM = "http://chuln.pt/patients"
ACCESSION_SYSTEM = "http://chuln.pt/accession"
ENCOUNTER_SYSTEM = "http://chuln.pt/encounters"
FHIR_BASE_URL = "http://chuln.pt/fhir"

NUM_WORKERS = max(1, (os.cpu_count() or 4) - 1)
BATCH_SIZE = 500
