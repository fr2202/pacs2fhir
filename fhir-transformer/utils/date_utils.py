"""Date conversion utilities for Portuguese DD/MM/YYYY and DD-MM-YYYY formats."""
from datetime import datetime
from typing import Optional


def parse_pt_date(date_str: str) -> Optional[datetime]:
    """Parses Portuguese date formats: DD/MM/YYYY or DD-MM-YYYY."""
    if not date_str:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def to_fhir_date(date_str: str) -> Optional[str]:
    """Converts DD/MM/YYYY to FHIR date format YYYY-MM-DD."""
    dt = parse_pt_date(date_str)
    return dt.strftime("%Y-%m-%d") if dt else None


def to_fhir_datetime(date_str: str, time_str: str = "") -> Optional[str]:
    """Combines date and optional time into FHIR dateTime (ISO 8601)."""
    if not date_str:
        return None
    combined = f"{date_str.strip()} {time_str.strip()}" if time_str.strip() else date_str.strip()
    dt = parse_pt_date(combined)
    if dt:
        return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    dt = parse_pt_date(date_str.strip())
    return dt.strftime("%Y-%m-%dT00:00:00+00:00") if dt else None


def to_fhir_instant(timestamp_str: str) -> Optional[str]:
    """Converts extraction/validation timestamp (DD/MM/YYYY HH:MM:SS) to FHIR instant."""
    if not timestamp_str:
        return None
    dt = parse_pt_date(timestamp_str)
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00") if dt else None
