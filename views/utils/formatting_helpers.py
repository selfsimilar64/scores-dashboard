import pandas as pd

def format_place_emoji(place_val):
    """Converts a place value to an emoji or string representation."""
    if pd.isna(place_val):
        return ""  # Empty string for NaN/None
    try:
        place_int = int(place_val)
        if place_int == 1:
            return "🥇"
        elif place_int == 2:
            return "🥈"
        elif place_int == 3:
            return "🥉"
        elif place_int == 4:
            return "4️⃣"
        elif place_int == 5:
            return "5️⃣"
        elif place_int == 6:
            return "6️⃣"
        elif place_int == 7:
            return "7️⃣"
        elif place_int == 8:
            return "8️⃣"
        elif place_int == 9:
            return "9️⃣"
        elif place_int == 0: # Explicitly handle 0 if it means something other than NaN
            return ""
        return str(place_int)
    except ValueError:
        return str(place_val) # Return original if not convertible to int

def format_meet_name_special(meet_name: str) -> str:
    """Formats special meet names with emojis."""
    if meet_name == 'States':
        return 'States ⭐'
    if meet_name == 'Regionals':
        return 'Regionals 🌟'
    return meet_name

def format_comp_year_emoji(year_series: pd.Series) -> pd.Series:
    """Formats competition years with color-coded emojis."""
    if not isinstance(year_series, pd.Series):
        raise TypeError("Input must be a pandas Series.")
    
    # Ensure years are strings for consistent processing, handle potential NA/NaN converted to '<NA>'
    # Convert to numeric first to sort correctly, then to string.
    # Handle potential errors if year_series contains non-convertible values.
    try:
        numeric_years = pd.to_numeric(year_series, errors='coerce').dropna()
        if numeric_years.empty:
            return year_series.astype(str) # Return as string if all are NaN or non-numeric
        
        unique_years_sorted_numeric = sorted(numeric_years.unique())
        unique_years_sorted_str = [str(int(y)) for y in unique_years_sorted_numeric] # Convert to int then str
    except Exception:
        # Fallback if conversion or sorting fails, use string representation
        unique_years_sorted_str = sorted(year_series.astype(str).unique())


    year_colors = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣'] # Add more if needed
    year_to_color_emoji = {
        year_str: year_colors[i % len(year_colors)] 
        for i, year_str in enumerate(unique_years_sorted_str)
    }
    
    def apply_format(year):
        year_str = str(year) if pd.notna(year) else "N/A"
        # Correctly handle cases where year might have been float (e.g. 2023.0) before string conversion
        if '.' in year_str: 
            year_str_lookup = str(int(float(year_str)))
        else:
            year_str_lookup = year_str
            
        emoji = year_to_color_emoji.get(year_str_lookup, '⚫')
        return f"{emoji} {year_str_lookup}"

    return year_series.apply(apply_format) 