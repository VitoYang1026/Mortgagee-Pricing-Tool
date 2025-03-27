import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Set, Tuple, Any, Optional, Union

# Import constants from utils
from utils.constants import EXCLUDED_FILTER_FIELDS

# Configure logging
logger = logging.getLogger('mortgage_pricing_tool.calculator')

class PriceCalculator:
    """
    Calculator for determining final prices and margins for borrower scenarios.
    
    This class calculates the final price for each borrower scenario by applying
    the appropriate LLPA adjustments to the base price, and then determines the
    margin between different investor prices.
    """
    
    def __init__(self, llpa_adjustments: Dict, base_prices: Dict):
        """
        Initialize the calculator with LLPA adjustments and base prices.
        
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
        
        # Store calculation results
        self.pricing_results = []
        
        logger.info(f"PriceCalculator initialized with {len(llpa_adjustments)} LLPA sheets and {len(base_prices)} base price sheets")
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
    
    def calculate_all_prices(self, scenarios: List[Dict]) -> List[Dict]:
        """
        Calculate prices for all scenarios.
        
        Args:
            scenarios: List of scenario dictionaries
            
        Returns:
            List of scenario dictionaries with pricing results
        """
        # Reset pricing results
        self.pricing_results = []
        
        # Process each scenario
        for scenario in scenarios:
            # Calculate price for this scenario
            pricing_result = self._calculate_scenario_price(scenario)
            
            # Add to results
            if pricing_result:
                self.pricing_results.append(pricing_result)
        
        # Log statistics
        self._log_statistics()
        
        logger.info(f"Price calculation complete. Generated {len(self.pricing_results)} pricing results.")
        return self.pricing_results
    
    def _calculate_scenario_price(self, scenario: Dict) -> Optional[Dict]:
        """
        Calculate price for a single scenario.
        
        Args:
            scenario: Scenario dictionary
            
        Returns:
            Enriched scenario dictionary with pricing results, or None if calculation failed
        """
        # Create a copy of the scenario to avoid modifying the original
        result = scenario.copy()
        
        # Get the sheet for this scenario
        sheet = scenario.get("Sheet")
        if not sheet or sheet not in self.llpa_adjustments:
            logger.warning(f"Sheet {sheet} not found in LLPA adjustments")
            return None
        
        # Get the rate for this scenario
        rate = scenario.get("Rate")
        if rate is None:
            logger.warning("Rate not specified in scenario")
            return None
        
        # Calculate base price
        base_price = self._get_base_price(sheet, rate)
        if base_price is None:
            logger.warning(f"Base price not found for sheet {sheet}, rate {rate}")
            return None
        
        # Calculate LLPA adjustments
        llpa_adjustments = self._calculate_llpa_adjustments(sheet, scenario)
        if llpa_adjustments is None:
            logger.warning(f"Failed to calculate LLPA adjustments for scenario")
            return None
        
        # Calculate final price
        final_price = base_price + llpa_adjustments
        
        # Add pricing information to result
        result["Base_Price"] = base_price
        result["LLPA_Adjustments"] = llpa_adjustments
        result["Final_Price"] = final_price
        
        # If this is an investor sheet, calculate AAA price for comparison
        if sheet != self.aaa_sheet:
            aaa_price = self._calculate_aaa_price(scenario)
            if aaa_price is not None:
                result["AAA_Final_Price"] = aaa_price
                
                # Calculate margin
                margin = final_price - aaa_price
                result["Margin"] = margin
        
        # Calculate investor comparisons if this is an AAA scenario
        if sheet == self.aaa_sheet:
            investor_prices = self._calculate_investor_prices(scenario)
            if investor_prices:
                result["Investors"] = investor_prices
                
                # Find maximum margin
                max_margin = self._find_max_margin(investor_prices)
                if max_margin:
                    result["Max_Margin"] = max_margin
        
        return result
    
    def _get_base_price(self, sheet: str, rate: float) -> Optional[float]:
        """
        Get the base price for a sheet and rate.
        
        Args:
            sheet: Sheet name
            rate: Interest rate
            
        Returns:
            Base price if found, None otherwise
        """
        # Check if sheet exists in base prices
        if sheet not in self.base_prices:
            logger.warning(f"Sheet {sheet} not found in base prices")
            return None
        
        # Check if rate exists in base prices for this sheet
        if rate not in self.base_prices[sheet]:
            logger.warning(f"Rate {rate} not found in base prices for sheet {sheet}")
            return None
        
        return self.base_prices[sheet][rate]
    
    def _calculate_llpa_adjustments(self, sheet: str, scenario: Dict) -> Optional[float]:
        """
        Calculate LLPA adjustments for a scenario.
        
        Args:
            sheet: Sheet name
            scenario: Scenario dictionary
            
        Returns:
            Total LLPA adjustment if calculable, None otherwise
        """
        total_adjustment = 0.0
        
        # Get LLPA adjustments for this sheet
        sheet_adjustments = self.llpa_adjustments.get(sheet, {})
        
        # Process each module
        for module_name, module_data in sheet_adjustments.items():
            # Extract dimension from module name
            dimension = self._extract_dimension_from_module(module_name)
            if not dimension:
                continue
            
            # Get the condition value for this dimension from the scenario
            condition = scenario.get(dimension)
            if condition is None:
                logger.warning(f"Dimension {dimension} not found in scenario")
                continue
            
            # Get adjustments for this condition
            condition_adjustments = module_data.get(condition)
            if not condition_adjustments:
                logger.warning(f"Condition {condition} not found in module {module_name}")
                continue
            
            # Find the appropriate LTV adjustment
            ltv_adjustment = self._find_ltv_adjustment(condition_adjustments, scenario)
            if ltv_adjustment is not None:
                total_adjustment += ltv_adjustment
        
        return total_adjustment
    
    def _extract_dimension_from_module(self, module_name: str) -> Optional[str]:
        """
        Extract dimension name from module name.
        
        Args:
            module_name: Name of the module (e.g., "1. FICO/LTV")
            
        Returns:
            Dimension name if extractable, None otherwise
        """
        # Skip if not a string
        if not isinstance(module_name, str):
            return None
        
        # Remove numeric prefix and whitespace
        parts = module_name.split('.')
        if len(parts) > 1:
            dimension = parts[1].strip()
        else:
            dimension = module_name.strip()
        
        return dimension
    
    def _find_ltv_adjustment(self, condition_adjustments: Dict, scenario: Dict) -> Optional[float]:
        """
        Find the appropriate LTV adjustment for a scenario.
        
        Args:
            condition_adjustments: Dictionary mapping LTV ranges to adjustments
            scenario: Scenario dictionary
            
        Returns:
            LTV adjustment if found, None otherwise
        """
        # Get LTV from scenario
        ltv = scenario.get("LTV")
        if ltv is None:
            logger.warning("LTV not specified in scenario")
            return None
        
        # Try to find an exact match
        for ltv_range, adjustment in condition_adjustments.items():
            if ltv_range == ltv:
                return adjustment
        
        # Try to find a range match
        for ltv_range, adjustment in condition_adjustments.items():
            # Skip if adjustment is None
            if adjustment is None:
                continue
                
            # Parse LTV range
            if '-' in ltv_range:
                # Range format: "65-70%"
                try:
                    range_parts = ltv_range.replace('%', '').split('-')
                    min_ltv = float(range_parts[0])
                    max_ltv = float(range_parts[1])
                    
                    if min_ltv <= ltv <= max_ltv:
                        return adjustment
                except (ValueError, IndexError):
                    continue
            elif '<=' in ltv_range:
                # Less than or equal format: "<=65%"
                try:
                    max_ltv = float(ltv_range.replace('<=', '').replace('%', ''))
                    if ltv <= max_ltv:
                        return adjustment
                except ValueError:
                    continue
            elif '>=' in ltv_range:
                # Greater than or equal format: ">=80%"
                try:
                    min_ltv = float(ltv_range.replace('>=', '').replace('%', ''))
                    if ltv >= min_ltv:
                        return adjustment
                except ValueError:
                    continue
        
        logger.warning(f"No matching LTV range found for LTV {ltv}")
        return None
    
    def _calculate_aaa_price(self, scenario: Dict) -> Optional[float]:
        """
        Calculate AAA price for a scenario.
        
        Args:
            scenario: Scenario dictionary
            
        Returns:
            AAA final price if calculable, None otherwise
        """
        # Check if AAA sheet exists
        if not self.aaa_sheet:
            logger.warning("AAA sheet not found")
            return None
        
        # Create AAA scenario
        aaa_scenario = scenario.copy()
        aaa_scenario["Sheet"] = self.aaa_sheet
        aaa_scenario["SourceType"] = "AAA"
        
        # Calculate AAA price
        aaa_result = self._calculate_scenario_price(aaa_scenario)
        if not aaa_result:
            logger.warning("Failed to calculate AAA price")
            return None
        
        return aaa_result.get("Final_Price")
    
    def _calculate_investor_prices(self, scenario: Dict) -> Dict:
        """
        Calculate prices for all investors for a scenario.
        
        Args:
            scenario: Scenario dictionary
            
        Returns:
            Dictionary mapping investor names to price information
        """
        investor_prices = {}
        
        # Process each investor sheet
        for investor_sheet in self.investor_sheets:
            # Create investor scenario
            investor_scenario = scenario.copy()
            investor_scenario["Sheet"] = investor_sheet
            investor_scenario["SourceType"] = "Investor"
            
            # Calculate investor price
            investor_result = self._calculate_scenario_price(investor_scenario)
            if not investor_result:
                continue
            
            # Extract investor name
            investor_name = self._extract_investor_name(investor_sheet)
            
            # Add to investor prices
            investor_prices[investor_name] = {
                "Final_Price": investor_result.get("Final_Price"),
                "Margin": investor_result.get("Margin")
            }
        
        return investor_prices
    
    def _extract_investor_name(self, sheet_name: str) -> str:
        """
        Extract investor name from sheet name.
        
        Args:
            sheet_name: Name of the sheet
            
        Returns:
            Investor name
        """
        # Remove prefix and whitespace
        if sheet_name.startswith("S-"):
            investor_name = sheet_name[2:].strip()
        else:
            investor_name = sheet_name.strip()
        
        return investor_name
    
    def _find_max_margin(self, investor_prices: Dict) -> Dict:
        """
        Find the investor with the maximum margin.
        
        Args:
            investor_prices: Dictionary mapping investor names to price information
            
        Returns:
            Dictionary with maximum margin information
        """
        max_margin = None
        max_investor = None
        
        # Find maximum margin
        for investor, price_info in investor_prices.items():
            margin = price_info.get("Margin")
            if margin is not None and (max_margin is None or margin > max_margin):
                max_margin = margin
                max_investor = investor
        
        # Return result
        if max_margin is not None and max_investor is not None:
            return {
                "investor": max_investor,
                "value": max_margin
            }
        
        return {}
    
    def _log_statistics(self) -> None:
        """Log statistics about the pricing results."""
        if not self.pricing_results:
            logger.info("No pricing results to analyze")
            return
        
        # Count scenarios by sheet
        sheet_counts = {}
        for result in self.pricing_results:
            sheet = result.get("Sheet", "Unknown")
            sheet_counts[sheet] = sheet_counts.get(sheet, 0) + 1
        
        logger.info(f"Scenarios by sheet: {sheet_counts}")
        
        # Count scenarios with margins
        margin_count = sum(1 for result in self.pricing_results if "Margin" in result)
        logger.info(f"Scenarios with margins: {margin_count}")
        
        # Count scenarios with max margins
        max_margin_count = sum(1 for result in self.pricing_results if "Max_Margin" in result)
        logger.info(f"Scenarios with max margins: {max_margin_count}")
    
    def _create_enriched_scenario(self, scenario: Dict, pricing_info: Dict) -> Dict:
        """
        Create an enriched scenario with pricing information.
        
        Args:
            scenario: Original scenario dictionary
            pricing_info: Dictionary containing pricing information
            
        Returns:
            Enriched scenario dictionary
        """
        # Create a copy of the scenario
        enriched = scenario.copy()
        
        # Add pricing information
        for key, value in pricing_info.items():
            enriched[key] = value
        
        return enriched
