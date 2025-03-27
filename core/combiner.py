import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Set, Tuple, Any, Optional, Union
from collections import defaultdict

# Import constants from utils
from utils.constants import EXCLUDED_FILTER_FIELDS

# Configure logging
logger = logging.getLogger('mortgage_pricing_tool.combiner')

class ScenarioGenerator:
    """
    Generator for creating all possible borrower scenarios.
    
    This class generates all possible combinations of borrower characteristics
    based on the LLPA adjustment tables, creating a comprehensive set of
    scenarios for pricing analysis.
    """
    
    def __init__(self, llpa_adjustments: Dict):
        """
        Initialize the generator with LLPA adjustment data.
        
        Args:
            llpa_adjustments: Dictionary containing LLPA adjustment tables
        """
        self.llpa_adjustments = llpa_adjustments
        
        # Extract available values for each dimension
        self.dimension_values = self._extract_dimension_values()
        
        # Store generated scenarios
        self.scenarios = []
        
        logger.info(f"ScenarioGenerator initialized with {len(llpa_adjustments)} sheets")
        logger.info(f"Extracted {len(self.dimension_values)} dimensions")
    
    def _extract_dimension_values(self) -> Dict[str, Set]:
        """
        Extract all possible values for each dimension from LLPA tables.
        
        Returns:
            Dictionary mapping dimension names to sets of possible values
        """
        dimension_values = defaultdict(set)
        
        # Process each sheet
        for sheet_name, sheet_data in self.llpa_adjustments.items():
            # Process each module
            for module_name, module_data in sheet_data.items():
                # Extract dimension name from module name
                dimension = self._extract_dimension_from_module(module_name)
                if not dimension:
                    continue
                
                # Add all condition values for this dimension
                for condition in module_data.keys():
                    dimension_values[dimension].add(condition)
        
        # Convert sets to sorted lists for consistent ordering
        return {
            dim: sorted(list(values)) 
            for dim, values in dimension_values.items()
        }
    
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
    
    def generate_all_scenarios(self) -> List[Dict]:
        """
        Generate all possible borrower scenarios.
        
        Returns:
            List of scenario dictionaries
        """
        # Reset scenarios
        self.scenarios = []
        
        # Get all possible rates
        rates = self._extract_rates()
        
        # Generate base scenarios without rates
        base_scenarios = self._generate_base_scenarios()
        
        # Add rates to each base scenario
        for base_scenario in base_scenarios:
            for rate in rates:
                scenario = base_scenario.copy()
                scenario["Rate"] = rate
                
                # Only add valid scenarios
                if self._is_valid_scenario(scenario):
                    self.scenarios.append(scenario)
        
        logger.info(f"Generated {len(self.scenarios)} scenarios")
        return self.scenarios
    
    def _extract_rates(self) -> List[float]:
        """
        Extract all possible rates from the AAA sheet.
        
        Returns:
            List of rate values
        """
        rates = set()
        
        # Find AAA sheet
        aaa_sheet = self._find_aaa_sheet()
        if not aaa_sheet:
            logger.warning("AAA sheet not found, using default rates")
            return [4.5, 4.625, 4.75, 4.875, 5.0, 5.125, 5.25, 5.375, 5.5]
        
        # Extract program from sheet name
        program = self._extract_program_from_sheet_name(aaa_sheet)
        
        # Add rates for this program
        for scenario in self.scenarios:
            if "Program" in scenario and scenario["Program"] == program:
                if "Rate" in scenario:
                    rates.add(scenario["Rate"])
        
        # If no rates found, use default rates
        if not rates:
            logger.warning("No rates found in scenarios, using default rates")
            return [4.5, 4.625, 4.75, 4.875, 5.0, 5.125, 5.25, 5.375, 5.5]
        
        return sorted(list(rates))
    
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
    
    def _extract_program_from_sheet_name(self, sheet_name: str) -> str:
        """
        Extract program name from sheet name.
        
        Args:
            sheet_name: Name of the sheet
            
        Returns:
            Program name
        """
        # Remove prefix and whitespace
        if sheet_name.startswith("S-AAA"):
            program = sheet_name[5:].strip()
        elif sheet_name.startswith("S-"):
            program = sheet_name[2:].strip()
        else:
            program = sheet_name.strip()
        
        return program
    
    def _generate_base_scenarios(self) -> List[Dict]:
        """
        Generate base scenarios without rates.
        
        Returns:
            List of base scenario dictionaries
        """
        # Start with an empty scenario
        base_scenarios = [{}]
        
        # Add each dimension one by one
        for dimension, values in self.dimension_values.items():
            new_scenarios = []
            
            # For each existing scenario, create variations with each value of this dimension
            for scenario in base_scenarios:
                for value in values:
                    new_scenario = scenario.copy()
                    new_scenario[dimension] = value
                    new_scenarios.append(new_scenario)
            
            base_scenarios = new_scenarios
        
        # Add sheet information to scenarios
        for sheet_name in self.llpa_adjustments.keys():
            # Extract program from sheet name
            program = self._extract_program_from_sheet_name(sheet_name)
            
            # Add program to all scenarios
            for scenario in base_scenarios:
                scenario["Program"] = program
                scenario["Sheet"] = sheet_name
                
                # Add source type
                if sheet_name.startswith("S-AAA"):
                    scenario["SourceType"] = "AAA"
                else:
                    scenario["SourceType"] = "Investor"
        
        return base_scenarios
    
    def _is_valid_scenario(self, scenario: Dict) -> bool:
        """
        Check if a scenario is valid based on business rules.
        
        Args:
            scenario: Scenario dictionary
            
        Returns:
            True if the scenario is valid, False otherwise
        """
        # Implement business rules for valid scenarios
        # For example, certain FICO scores might only be valid with certain LTV ranges
        
        # For now, consider all scenarios valid
        return True
    
    def get_dimension_values(self) -> Dict[str, List]:
        """
        Get all possible values for each dimension.
        
        Returns:
            Dictionary mapping dimension names to lists of possible values
        """
        return self.dimension_values
