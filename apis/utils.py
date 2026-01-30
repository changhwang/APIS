import os
import datetime
import re

def get_timestamp_iso():
    """Return current timestamp in ISO 8601 format."""
    return datetime.datetime.now().isoformat()

def get_timestamp_file():
    """Return timestamp suitable for filenames (YYYYMMDD_HHMMSS)."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_dir(directory):
    """Ensure a directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)

def sanitize_filename(name):
    """Sanitize string for usage as filename."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)

def format_command(pp, aaa):
    """
    Format command string PPAAA.
    pp: int (2 digits)
    aaa: int (3 digits)
    Returns string 'PPAAA'
    """
    return f"{pp:02d}{aaa:03d}"
