import pandas as pd
from config import ROUNDING_STEP # Import from the central config

def custom_round(value):
    """Rounds a numeric value to the nearest configured step (e.g., 0.05)."""
    if pd.isna(value) or not isinstance(value, (int, float)):
        return value  # Return as is if NaN or not a number
    
    # Ensure ROUNDING_STEP is not zero to avoid division by zero error
    if ROUNDING_STEP == 0:
        return value # Or raise an error, or handle as per application's requirements
        
    return round(value / ROUNDING_STEP) * ROUNDING_STEP 