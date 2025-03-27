import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Set, Tuple, Any, Optional, Union

# Import constants from utils
from utils.constants import EXCLUDED_FILTER_FIELDS

# Configure logging
logger = logging.getLogger('mortgage_pricing_tool.parser')

class PricingDataParser:
    """
    Parser for extracting LLPA adjustments and Base Prices from Excel files.
    
    This class handles the parsing of Excel files containing mortgage pricing data,
    extracting LLPA (Loan Level Price Adjustment) tables and Base Price tables.
    """
    
    def __init__(self):
        """Initialize the parser."""
        # Store parsed data
        self.llpa_adjustments = {}
        self.base_prices = {}
        
        logger.info("PricingDataParser initialized")
    
    def parse_workbooks(self, aaa_data: Dict[str, pd.DataFrame], investor_data: Dict[str, pd.DataFrame]) -> Tuple[Dict, Dict]:
        """
        Parse AAA and Investor Excel workbooks.
        
        Args:
            aaa_data: Dictionary mapping sheet names to DataFrames for AAA workbook
            investor_data: Dictionary mapping sheet names to DataFrames for Investor workbook
            
        Returns:
            Tuple of (llpa_adjustments, base_prices) dictionaries
        """
        # Reset stored data
        self.llpa_adjustments = {}
        self.base_prices = {}
        
        # Process AAA workbook
        self._process_workbook(aaa_data, "AAA")
        
        # Process Investor workbook
        self._process_workbook(investor_data, "Investor")
        
        logger.info(f"Parsing complete. Extracted {len(self.llpa_adjustments)} LLPA sheets and {len(self.base_prices)} Base Price sheets.")
        
        return self.llpa_adjustments, self.base_prices
    
    def _process_workbook(self, workbook_data: Dict[str, pd.DataFrame], workbook_type: str) -> None:
        """
        Process a workbook and extract LLPA adjustments and Base Prices.
        
        Args:
            workbook_data: Dictionary mapping sheet names to DataFrames
            workbook_type: Type of workbook ("AAA" or "Investor")
        """
        # Process each sheet
        for sheet_name, df in workbook_data.items():
            # Skip empty sheets
            if df.empty:
                logger.warning(f"Skipping empty sheet: {sheet_name}")
                continue
            
            # Standardize sheet name
            std_sheet_name = self._standardize_sheet_name(sheet_name, workbook_type)
            
            # Extract LLPA adjustments
            llpa_data = self._extract_llpa_adjustments(df)
            if llpa_data:
                self.llpa_adjustments[std_sheet_name] = llpa_data
                logger.info(f"Extracted LLPA adjustments from {sheet_name} -> {std_sheet_name}")
            
            # Extract Base Prices
            base_prices = self._extract_base_prices(df)
            if base_prices:
                self.base_prices[std_sheet_name] = base_prices
                logger.info(f"Extracted Base Prices from {sheet_name} -> {std_sheet_name}")
    
    def _standardize_sheet_name(self, sheet_name: str, workbook_type: str) -> str:
        """
        Standardize sheet name for consistent referencing.
        
        Args:
            sheet_name: Original sheet name
            workbook_type: Type of workbook ("AAA" or "Investor")
            
        Returns:
            Standardized sheet name
        """
        # Remove any special characters and standardize spacing
        clean_name = sheet_name.strip()
        
        # Add prefix based on workbook type if not already present
        if workbook_type == "AAA" and not clean_name.startswith("S-AAA"):
            return f"S-AAA {clean_name}"
        elif workbook_type == "Investor" and not clean_name.startswith("S-"):
            return f"S-{clean_name}"
        
        return clean_name
    
    def _extract_llpa_adjustments(self, df: pd.DataFrame) -> Dict:
        """
        Extract LLPA adjustments from a DataFrame.
        
        Args:
            df: DataFrame containing LLPA adjustment tables
            
        Returns:
            Dictionary mapping module names to adjustment tables
        """
        llpa_data = {}
        
        try:
            # Find all tables in the sheet
            tables = self._identify_llpa_tables(df)
            
            # Process each table
            for table_info in tables:
                module_name = table_info["module_name"]
                start_row = table_info["start_row"]
                end_row = table_info["end_row"]
                
                # Extract the table
                table_df = df.iloc[start_row:end_row].copy()
                
                # Process the table to extract adjustments
                adjustments = self._process_llpa_table(table_df)
                
                # Add to LLPA data
                if adjustments:
                    llpa_data[module_name] = adjustments
            
            return llpa_data
            
        except Exception as e:
            logger.error(f"Error extracting LLPA adjustments: {str(e)}")
            return {}
    
    def _identify_llpa_tables(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify LLPA tables in the DataFrame.
        
        Args:
            df: DataFrame to search for tables
            
        Returns:
            List of dictionaries with table information
        """
        tables = []
        current_table = None
        
        # Iterate through rows to find table headers and boundaries
        for i, row in df.iterrows():
            row_values = row.astype(str).str.strip()
            
            # Check if this row contains a module header (e.g., "1. FICO/LTV")
            module_header = self._extract_module_header(row_values)
            
            if module_header:
                # If we were tracking a previous table, add it to the list
                if current_table:
                    current_table["end_row"] = i
                    tables.append(current_table)
                
                # Start tracking a new table
                current_table = {
                    "module_name": module_header,
                    "start_row": i,
                    "end_row": None
                }
            
            # Check for the end of the DataFrame
            if i == len(df) - 1 and current_table:
                current_table["end_row"] = i + 1
                tables.append(current_table)
        
        return tables
    
    def _extract_module_header(self, row_values: pd.Series) -> Optional[str]:
        """
        Extract module header from a row.
        
        Args:
            row_values: Series containing row values
            
        Returns:
            Module header if found, None otherwise
        """
        # Look for patterns like "1. FICO/LTV" or "2. DSCR"
        for value in row_values:
            if isinstance(value, str) and re.match(r'^\d+\.\s+\w+', value):
                return value.strip()
        
        return None
    
    def _process_llpa_table(self, table_df: pd.DataFrame) -> Dict:
        """
        Process an LLPA table to extract adjustments.
        
        Args:
            table_df: DataFrame containing the LLPA table
            
        Returns:
            Dictionary mapping conditions to LTV-based adjustments
        """
        adjustments = {}
        
        try:
            # Clean the table
            table_df = table_df.dropna(how='all').reset_index(drop=True)
            
            # Find the header row (contains LTV ranges)
            header_row = self._find_ltv_header_row(table_df)
            if header_row is None:
                return adjustments
            
            # Extract LTV columns
            ltv_columns = self._extract_ltv_columns(table_df.iloc[header_row])
            if not ltv_columns:
                return adjustments
            
            # Process each row as a condition
            for i in range(header_row + 1, len(table_df)):
                row = table_df.iloc[i]
                
                # Skip empty rows
                if row.isna().all() or (isinstance(row[0], str) and row[0].strip() == ''):
                    continue
                
                # Extract condition name
                condition = str(row[0]).strip()
                if not condition:
                    continue
                
                # Extract adjustments for each LTV column
                ltv_adjustments = {}
                for ltv_range, col_idx in ltv_columns.items():
                    if col_idx < len(row):
                        value = row[col_idx]
                        # Convert to float if possible
                        try:
                            if pd.notna(value):
                                value = float(value)
                            else:
                                value = None
                        except (ValueError, TypeError):
                            value = None
                        
                        ltv_adjustments[ltv_range] = value
                
                # Add to adjustments
                adjustments[condition] = ltv_adjustments
            
            return adjustments
            
        except Exception as e:
            logger.error(f"Error processing LLPA table: {str(e)}")
            return {}
    
    def _find_ltv_header_row(self, table_df: pd.DataFrame) -> Optional[int]:
        """
        Find the row containing LTV headers.
        
        Args:
            table_df: DataFrame containing the LLPA table
            
        Returns:
            Index of the header row, or None if not found
        """
        # Look for rows containing LTV patterns
        for i, row in table_df.iterrows():
            row_values = [str(x).strip() for x in row if pd.notna(x)]
            ltv_patterns = [
                x for x in row_values 
                if re.match(r'^\d+(\.\d+)?-\d+(\.\d+)?%?$', x) or 
                   re.match(r'^<=\d+(\.\d+)?%?$', x) or 
                   re.match(r'^>=\d+(\.\d+)?%?$', x)
            ]
            
            if len(ltv_patterns) >= 2:  # At least 2 LTV ranges
                return i
        
        return None
    
    def _extract_ltv_columns(self, header_row: pd.Series) -> Dict[str, int]:
        """
        Extract LTV column ranges and their indices.
        
        Args:
            header_row: Series containing the header row
            
        Returns:
            Dictionary mapping LTV ranges to column indices
        """
        ltv_columns = {}
        
        for i, value in enumerate(header_row):
            if pd.isna(value):
                continue
                
            value_str = str(value).strip()
            
            # Match LTV patterns
            if (re.match(r'^\d+(\.\d+)?-\d+(\.\d+)?%?$', value_str) or 
                re.match(r'^<=\d+(\.\d+)?%?$', value_str) or 
                re.match(r'^>=\d+(\.\d+)?%?$', value_str)):
                
                # Standardize format
                if not value_str.endswith('%'):
                    value_str = f"{value_str}%"
                
                ltv_columns[value_str] = i
        
        return ltv_columns
    
    def _extract_base_prices(self, df: pd.DataFrame) -> Dict:
        """
        Extract Base Prices from a DataFrame.
        
        Args:
            df: DataFrame containing Base Price table
            
        Returns:
            Dictionary mapping rates to base prices
        """
        base_prices = {}
        
        try:
            # Look for the Base Price table
            base_price_row = self._find_base_price_row(df)
            if base_price_row is None:
                return base_prices
            
            # Find the rate column
            rate_col = self._find_rate_column(df)
            if rate_col is None:
                return base_prices
            
            # Find the price column
            price_col = self._find_price_column(df, base_price_row)
            if price_col is None:
                return base_prices
            
            # Extract rates and prices
            for i in range(base_price_row + 1, len(df)):
                row = df.iloc[i]
                
                # Skip empty rows
                if pd.isna(row[rate_col]) or pd.isna(row[price_col]):
                    continue
                
                # Extract rate and price
                try:
                    rate = float(row[rate_col])
                    price = float(row[price_col])
                    base_prices[rate] = price
                except (ValueError, TypeError):
                    continue
            
            return base_prices
            
        except Exception as e:
            logger.error(f"Error extracting Base Prices: {str(e)}")
            return {}
    
    def _find_base_price_row(self, df: pd.DataFrame) -> Optional[int]:
        """
        Find the row containing the Base Price header.
        
        Args:
            df: DataFrame to search
            
        Returns:
            Index of the Base Price row, or None if not found
        """
        for i, row in df.iterrows():
            row_values = [str(x).lower().strip() for x in row if pd.notna(x)]
            if any('base price' in x for x in row_values):
                return i
        
        return None
    
    def _find_rate_column(self, df: pd.DataFrame) -> Optional[int]:
        """
        Find the column containing rates.
        
        Args:
            df: DataFrame to search
            
        Returns:
            Index of the rate column, or None if not found
        """
        for i, col in enumerate(df.columns):
            col_values = [str(x).lower().strip() for x in df.iloc[:, i] if pd.notna(x)]
            if any('rate' in x for x in col_values):
                return i
        
        return None
    
    def _find_price_column(self, df: pd.DataFrame, base_price_row: int) -> Optional[int]:
        """
        Find the column containing prices.
        
        Args:
            df: DataFrame to search
            base_price_row: Row index containing the Base Price header
            
        Returns:
            Index of the price column, or None if not found
        """
        row = df.iloc[base_price_row]
        
        for i, value in enumerate(row):
            if pd.isna(value):
                continue
                
            value_str = str(value).lower().strip()
            if 'base price' in value_str:
                return i
        
        return None
    
    def find_aaa_sheet(self, llpa_adjustments: Dict) -> Optional[str]:
        """
        Find the AAA sheet in the LLPA adjustments.
        
        Args:
            llpa_adjustments: Dictionary of LLPA adjustments
            
        Returns:
            Name of the AAA sheet if found, None otherwise
        """
        for sheet_name in llpa_adjustments.keys():
            if sheet_name.startswith("S-AAA"):
                return sheet_name
        
        return None


# Import regex module (used in the class)
import re
