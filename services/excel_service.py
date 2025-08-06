# services/excel_service.py
import pandas as pd
import os
from typing import Optional, Dict

EXCEL_FILE = "data/parcel_database.xlsx"
_df_cache: Optional[pd.DataFrame] = None

def _load_data() -> pd.DataFrame:
    """Loads the Excel data into a pandas DataFrame and caches it."""
    global _df_cache
    if _df_cache is not None:
        return _df_cache

    if not os.path.exists(EXCEL_FILE):
        raise FileNotFoundError(
            f"Database file not found: {EXCEL_FILE}. "
            "Please generate it and place it in the 'data' directory."
        )
    
    print("Loading parcel data from Excel file for the first time...")
    # Read the excel file and set 'Tracking ID' as the index for fast lookups
    df = pd.read_excel(EXCEL_FILE).set_index("Tracking ID")
    _df_cache = df
    print("Parcel data loaded and cached.")
    return _df_cache

def get_parcel_status(tracking_id: str) -> Optional[Dict]:
    """
    Retrieves the status of a parcel from the Excel sheet.

    Args:
        tracking_id (str): The tracking ID to search for.

    Returns:
        A dictionary with the parcel data if found, otherwise None.
    """
    df = _load_data()
    try:
        # Use .loc for fast lookup by index
        parcel_data = df.loc[tracking_id]
        # Convert the pandas Series result to a dictionary
        return parcel_data.to_dict()
    except KeyError:
        # The tracking ID was not found in the index
        print(f"Tracking ID '{tracking_id}' not found in the database.")
        return None