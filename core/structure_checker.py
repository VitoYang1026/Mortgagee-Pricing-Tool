import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Set, Tuple, Any, Optional, Union

# Configure logging
logger = logging.getLogger('mortgage_pricing_tool.structure_checker')

class StructureValidator:
    """
    Validator for checking the structure of pricing sheets.
    
    This class validates the structure of investor sheets against the AAA sheet,
    checking for consistency in modules, LTV ranges, and other structural elements.
    """
    
    def __init__(self, llpa_adjustments: Dict, base_prices: Dict):
        """
        Initialize the validator with LLPA adjustments and base prices.
        
        Args:
            llpa_adjustments: Dictionary containing LLPA adjustment tables
            base_prices: Dictionary containing base price tables
        """
        self.llpa_adjustments = llpa_adjustments
        self.base_prices = base_prices
        
        # Find AAA sheet
        self.aaa_sheet = self._find_aaa_sheet()
        
        # Extract investor sheets
        self.investor_sheets = [
            sheet for sheet in llpa_adjustments.keys()
            if sheet != self.aaa_sheet
        ]
        
        # Store validation results
        self.validation_results = {}
        
        logger.info(f"StructureValidator initialized with {len(llpa_adjustments)} LLPA sheets and {len(base_prices)} base price sheets")
        logger.info(f"AAA sheet: {self.aaa_sheet}")
        logger.info(f"Investor sheets: {len(self.investor_sheets)}")
    
    def _find_aaa_sheet(self) -> Optional[str]:
        """
        Find the AAA sheet in the LLPA adjustments.
        
        Returns:
            Name of the AAA sheet if found, None otherwise
        """
        for sheet_name in self.llpa_adjustments.keys():
            if sheet_name.startswith("S-AAA"):
                return sheet_name
        
        return None
    
    def validate_all_sheets(self) -> Dict:
        """
        Validate all investor sheets against the AAA sheet.
        
        Returns:
            Dictionary containing validation results
        """
        # Reset validation results
        self.validation_results = {
            "summary": {
                "total_sheets": len(self.investor_sheets),
                "sheets_with_issues": 0
            },
            "details": {}
        }
        
        try:
            # Check if AAA sheet exists
            if not self.aaa_sheet:
                self.validation_results["summary"]["error"] = "AAA sheet not found"
                return self.validation_results
            
            # Get AAA modules
            aaa_modules = self._get_sheet_modules(self.aaa_sheet)
            
            # Get AAA LTV ranges
            aaa_ltv_ranges = self._get_sheet_ltv_ranges(self.aaa_sheet)
            
            # Get AAA rates
            aaa_rates = self._get_sheet_rates(self.aaa_sheet)
            
            # Validate each investor sheet
            for sheet in self.investor_sheets:
                sheet_issues = self._validate_sheet(sheet, aaa_modules, aaa_ltv_ranges, aaa_rates)
                
                # Add to results if issues found
                if sheet_issues:
                    self.validation_results["details"][sheet] = sheet_issues
                    self.validation_results["summary"]["sheets_with_issues"] += 1
            
            return self.validation_results
            
        except Exception as e:
            logger.error(f"Error validating sheets: {str(e)}")
            self.validation_results["summary"]["error"] = f"Validation failed: {str(e)}"
            return self.validation_results
    
    def _get_sheet_modules(self, sheet: str) -> List[str]:
        """
        Get all modules in a sheet.
        
        Args:
            sheet: Sheet name
            
        Returns:
            List of module names
        """
        if sheet not in self.llpa_adjustments:
            return []
        
        return list(self.llpa_adjustments[sheet].keys())
    
    def _get_sheet_ltv_ranges(self, sheet: str) -> Dict[str, Set[str]]:
        """
        Get all LTV ranges in a sheet by module.
        
        Args:
            sheet: Sheet name
            
        Returns:
            Dictionary mapping module names to sets of LTV ranges
        """
        ltv_ranges = {}
        
        if sheet not in self.llpa_adjustments:
            return ltv_ranges
        
        # Process each module
        for module_name, module_data in self.llpa_adjustments[sheet].items():
            module_ltv_ranges = set()
            
            # Process each condition
            for condition, condition_data in module_data.items():
                # Add all LTV ranges
                for ltv_range in condition_data.keys():
                    module_ltv_ranges.add(ltv_range)
            
            ltv_ranges[module_name] = module_ltv_ranges
        
        return ltv_ranges
    
    def _get_sheet_rates(self, sheet: str) -> List[float]:
        """
        Get all rates in a sheet.
        
        Args:
            sheet: Sheet name
            
        Returns:
            List of rates
        """
        if sheet not in self.base_prices:
            return []
        
        return list(self.base_prices[sheet].keys())
    
    def _validate_sheet(self, sheet: str, aaa_modules: List[str], aaa_ltv_ranges: Dict[str, Set[str]], aaa_rates: List[float]) -> Dict:
        """
        Validate a sheet against the AAA sheet.
        
        Args:
            sheet: Sheet name
            aaa_modules: List of AAA module names
            aaa_ltv_ranges: Dictionary mapping AAA module names to sets of LTV ranges
            aaa_rates: List of AAA rates
            
        Returns:
            Dictionary containing validation issues, or empty dict if no issues
        """
        issues = {}
        
        try:
            # Get sheet modules
            sheet_modules = self._get_sheet_modules(sheet)
            
            # Check for missing modules
            missing_modules = [m for m in aaa_modules if m not in sheet_modules]
            if missing_modules:
                issues["missing_modules"] = missing_modules
            
            # Check for extra modules
            extra_modules = [m for m in sheet_modules if m not in aaa_modules]
            if extra_modules:
                issues["extra_modules"] = extra_modules
            
            # Check module order
            if self._check_module_order(sheet_modules, aaa_modules) is False:
                issues["wrong_module_order"] = True
            
            # Check LTV ranges
            sheet_ltv_ranges = self._get_sheet_ltv_ranges(sheet)
            ltv_issues = self._check_ltv_ranges(sheet_ltv_ranges, aaa_ltv_ranges)
            if ltv_issues:
                issues["ltv_columns_mismatch"] = True
                issues["ltv_details"] = ltv_issues
            
            # Check base price rows
            sheet_rates = self._get_sheet_rates(sheet)
            missing_rates = self._check_missing_base_price_rows(sheet_rates, aaa_rates)
            if missing_rates:
                issues["base_price_missing_rows"] = len(missing_rates)
                issues["missing_rates"] = missing_rates
            
            return issues
            
        except Exception as e:
            logger.error(f"Error validating sheet {sheet}: {str(e)}")
            return {"error": f"Validation failed: {str(e)}"}
    
    def _check_module_order(self, sheet_modules: List[str], aaa_modules: List[str]) -> bool:
        """
        Check if modules are in the same order as the AAA sheet.
        
        Args:
            sheet_modules: List of sheet module names
            aaa_modules: List of AAA module names
            
        Returns:
            True if order is correct, False otherwise
        """
        # Create a mapping of module name to position
        aaa_positions = {module: i for i, module in enumerate(aaa_modules)}
        
        # Check if sheet modules are in the same order
        prev_pos = -1
        for module in sheet_modules:
            if module in aaa_positions:
                pos = aaa_positions[module]
                if pos < prev_pos:
                    return False
                prev_pos = pos
        
        return True
    
    def _check_ltv_ranges(self, sheet_ltv_ranges: Dict[str, Set[str]], aaa_ltv_ranges: Dict[str, Set[str]]) -> Dict:
        """
        Check if LTV ranges match the AAA sheet.
        
        Args:
            sheet_ltv_ranges: Dictionary mapping sheet module names to sets of LTV ranges
            aaa_ltv_ranges: Dictionary mapping AAA module names to sets of LTV ranges
            
        Returns:
            Dictionary containing LTV range issues, or empty dict if no issues
        """
        issues = {}
        
        # Check each module
        for module in aaa_ltv_ranges.keys():
            # Skip if module doesn't exist in sheet
            if module not in sheet_ltv_ranges:
                continue
            
            # Get LTV ranges
            aaa_ranges = aaa_ltv_ranges[module]
            sheet_ranges = sheet_ltv_ranges[module]
            
            # Check for missing ranges
            missing_ranges = [r for r in aaa_ranges if r not in sheet_ranges]
            if missing_ranges:
                if "missing_ltv_ranges" not in issues:
                    issues["missing_ltv_ranges"] = []
                issues["missing_ltv_ranges"].extend(missing_ranges)
            
            # Check for extra ranges
            extra_ranges = [r for r in sheet_ranges if r not in aaa_ranges]
            if extra_ranges:
                if "extra_ltv_ranges" not in issues:
                    issues["extra_ltv_ranges"] = []
                issues["extra_ltv_ranges"].extend(extra_ranges)
        
        return issues
    
    def _check_missing_base_price_rows(self, sheet_rates: List[float], aaa_rates: List[float]) -> List[float]:
        """
        Check for missing base price rows.
        
        Args:
            sheet_rates: List of sheet rates
            aaa_rates: List of AAA rates
            
        Returns:
            List of missing rates
        """
        return [r for r in aaa_rates if r not in sheet_rates]
    
    def _check_duplicate_modules(self, sheet: str) -> List[str]:
        """
        Check for duplicate modules in a sheet.
        
        Args:
            sheet: Sheet name
            
        Returns:
            List of duplicate module names
        """
        if sheet not in self.llpa_adjustments:
            return []
        
        # Count module occurrences
        module_counts = {}
        for module in self.llpa_adjustments[sheet].keys():
            module_counts[module] = module_counts.get(module, 0) + 1
        
        # Find duplicates
        duplicates = [module for module, count in module_counts.items() if count > 1]
        
        return duplicates
