import base64
import logging
import os
from typing import Dict, Any, Optional, BinaryIO

import pandas as pd

# Configure logging
logger = logging.getLogger('mortgage_pricing_tool.io')

def save_workbook_data(data: Dict[str, Any], filename: str) -> bool:
    """
    Save workbook data to a file.
    
    Args:
        data: Dictionary containing workbook data
        filename: Path to save the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import pickle
        
        with open(filename, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Workbook data saved to {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving workbook data: {str(e)}")
        return False

def load_workbook_data(filename: str) -> Optional[Dict[str, Any]]:
    """
    Load workbook data from a file.
    
    Args:
        filename: Path to the file
        
    Returns:
        Dictionary containing workbook data, or None if loading failed
    """
    try:
        import pickle
        
        with open(filename, 'rb') as f:
            data = pickle.load(f)
        
        logger.info(f"Workbook data loaded from {filename}")
        return data
        
    except Exception as e:
        logger.error(f"Error loading workbook data: {str(e)}")
        return None

def create_download_link(df: pd.DataFrame, filename: str, link_text: str = "Download CSV") -> str:
    """
    Create a download link for a DataFrame.
    
    Args:
        df: DataFrame to download
        filename: Name of the file to download
        link_text: Text to display for the link
        
    Returns:
        HTML string containing the download link
    """
    try:
        # Generate CSV
        csv = df.to_csv(index=False)
        
        # Create download link
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{link_text}</a>'
        
        return href
        
    except Exception as e:
        logger.error(f"Error creating download link: {str(e)}")
        return f"Error creating download link: {str(e)}"

def read_excel_file(file: BinaryIO) -> Dict[str, pd.DataFrame]:
    """
    Read an Excel file into a dictionary of DataFrames.
    
    Args:
        file: File-like object containing Excel data
        
    Returns:
        Dictionary mapping sheet names to DataFrames
    """
    try:
        # Read all sheets
        excel_data = pd.read_excel(file, sheet_name=None)
        
        logger.info(f"Read Excel file with {len(excel_data)} sheets")
        return excel_data
        
    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}")
        return {}

def export_results_to_excel(data: Dict[str, pd.DataFrame], filename: str) -> bool:
    """
    Export results to an Excel file.
    
    Args:
        data: Dictionary mapping sheet names to DataFrames
        filename: Path to save the Excel file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with pd.ExcelWriter(filename) as writer:
            for sheet_name, df in data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"Results exported to {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Error exporting results: {str(e)}")
        return False
