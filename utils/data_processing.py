import pandas as pd

def add_comp_date_to_meet_name(df: pd.DataFrame, meet_name_col: str = "MeetName", comp_year_col: str = "CompYear") -> pd.DataFrame:
    """
    Appends the competition year to the meet name.

    Args:
        df: DataFrame containing meet data.
        meet_name_col: Name of the column containing meet names.
        comp_year_col: Name of the column containing competition years.

    Returns:
        DataFrame with an updated meet name column.
    """
    if meet_name_col in df.columns and comp_year_col in df.columns:
        # Ensure CompYear is string, and handle potential NaNs
        df[comp_year_col] = df[comp_year_col].fillna('').astype(str).str.replace(r'\.0$', '', regex=True)
        
        # Create a copy to avoid modifying the original DataFrame slices if 'df' is a view
        df_copy = df.copy()
        
        df_copy[meet_name_col] = df_copy.apply(
            lambda row: f"{row[meet_name_col]} ({row[comp_year_col]})" 
            if pd.notna(row[meet_name_col]) and pd.notna(row[comp_year_col]) and row[comp_year_col] != '' 
            else row[meet_name_col],
            axis=1
        )
        return df_copy
    return df 