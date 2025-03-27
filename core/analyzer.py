import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Set, Tuple, Any, Optional, Union

# Import constants from utils
from utils.constants import EXCLUDED_FILTER_FIELDS

# Configure logging
logger = logging.getLogger('mortgage_pricing_tool.analyzer')

class DataFilterAnalyzer:
    """
    Analyzer for filtering and analyzing pricing data.
    
    This class provides functionality to filter pricing results based on
    various dimensions and analyze the filtered data to extract insights.
    """
    
    def __init__(self, pricing_results: List[Dict]):
        """
        Initialize the analyzer with pricing results.
        
        Args:
            pricing_results: List of pricing result dictionaries
        """
        self.pricing_results = pricing_results
        
        # Extract available dimensions
        self.dimensions = self._extract_dimensions()
        
        # Store analysis results
        self.analysis_results = {}
        
        logger.info(f"DataFilterAnalyzer initialized with {len(pricing_results)} pricing results")
        logger.info(f"Available dimensions: {len(self.dimensions)}")
    
    def _extract_dimensions(self) -> List[str]:
        """
        Extract all available dimensions from pricing results.
        
        Returns:
            List of dimension names
        """
        dimensions = set()
        
        # Process each result
        for result in self.pricing_results:
            # Add all keys as potential dimensions
            for key in result.keys():
                # Exclude certain fields
                if key not in EXCLUDED_FILTER_FIELDS:
                    dimensions.add(key)
        
        return sorted(list(dimensions))
    
    def get_available_dimensions(self) -> List[str]:
        """
        Get all available dimensions for filtering.
        
        Returns:
            List of dimension names
        """
        return self.dimensions
    
    def get_dimension_values(self, dimension: str) -> List:
        """
        Get all possible values for a dimension.
        
        Args:
            dimension: Dimension name
            
        Returns:
            List of possible values
        """
        values = set()
        
        # Process each result
        for result in self.pricing_results:
            # Add value if dimension exists
            if dimension in result:
                values.add(result[dimension])
        
        # Sort values if possible
        try:
            return sorted(list(values))
        except TypeError:
            # If values can't be sorted (e.g., mix of types), return as is
            return list(values)
    
    def filter_and_analyze(self, filters: Dict) -> Dict:
        """
        Filter pricing results and analyze the filtered data.
        
        Args:
            filters: Dictionary mapping dimensions to filter values
            
        Returns:
            Dictionary containing analysis results
        """
        # Reset analysis results
        self.analysis_results = {}
        
        try:
            # Apply filters
            filtered_results = self._apply_filters(filters)
            
            # Check if we have any results
            if not filtered_results:
                return {"Error": "No results match the selected filters"}
            
            # Analyze filtered results
            self.analysis_results = self._analyze_results(filtered_results, filters)
            
            return self.analysis_results
            
        except Exception as e:
            logger.error(f"Error filtering and analyzing data: {str(e)}")
            return {"Error": f"Analysis failed: {str(e)}"}
    
    def _apply_filters(self, filters: Dict) -> List[Dict]:
        """
        Apply filters to pricing results.
        
        Args:
            filters: Dictionary mapping dimensions to filter values
            
        Returns:
            List of filtered pricing result dictionaries
        """
        filtered_results = self.pricing_results
        
        # Process each filter
        for dimension, filter_value in filters.items():
            # Skip if dimension doesn't exist
            if dimension not in self.dimensions:
                logger.warning(f"Dimension {dimension} not found in available dimensions")
                continue
            
            # Handle range filters (e.g., for Rate)
            if isinstance(filter_value, tuple) and len(filter_value) == 2:
                min_value, max_value = filter_value
                filtered_results = [
                    result for result in filtered_results
                    if dimension in result and min_value <= result[dimension] <= max_value
                ]
            # Handle single value filters
            else:
                filtered_results = [
                    result for result in filtered_results
                    if dimension in result and result[dimension] == filter_value
                ]
        
        logger.info(f"Applied filters: {filters}")
        logger.info(f"Filtered results: {len(filtered_results)}")
        
        return filtered_results
    
    def _analyze_results(self, results: List[Dict], filters: Dict) -> Dict:
        """
        Analyze filtered results to extract insights.
        
        Args:
            results: List of filtered pricing result dictionaries
            filters: Dictionary mapping dimensions to filter values
            
        Returns:
            Dictionary containing analysis results
        """
        analysis = {}
        
        # Add basic information
        analysis["SampleSize"] = len(results)
        analysis["Scope"] = self._format_scope(filters)
        
        # Analyze margins
        margin_analysis = self._analyze_margins(results)
        analysis.update(margin_analysis)
        
        # Analyze by investor
        investor_analysis = self._analyze_by_investor(results)
        if investor_analysis:
            analysis["Margin_Distribution"] = investor_analysis
        
        return analysis
    
    def _format_scope(self, filters: Dict) -> str:
        """
        Format filter scope for display.
        
        Args:
            filters: Dictionary mapping dimensions to filter values
            
        Returns:
            Formatted scope string
        """
        if not filters:
            return "All scenarios"
        
        scope_parts = []
        
        # Process each filter
        for dimension, filter_value in filters.items():
            # Handle range filters
            if isinstance(filter_value, tuple) and len(filter_value) == 2:
                min_value, max_value = filter_value
                scope_parts.append(f"{dimension}: {min_value} to {max_value}")
            # Handle single value filters
            else:
                scope_parts.append(f"{dimension}: {filter_value}")
        
        return ", ".join(scope_parts)
    
    def _analyze_margins(self, results: List[Dict]) -> Dict:
        """
        Analyze margins in the filtered results.
        
        Args:
            results: List of filtered pricing result dictionaries
            
        Returns:
            Dictionary containing margin analysis
        """
        analysis = {}
        
        # Extract margins
        margins = []
        for result in results:
            if "Margin" in result:
                margins.append(result["Margin"])
            elif "Max_Margin" in result and "value" in result["Max_Margin"]:
                margins.append(result["Max_Margin"]["value"])
        
        # Calculate statistics
        if margins:
            analysis["Average_Margin"] = np.mean(margins)
            analysis["Max_Margin"] = np.max(margins)
            analysis["Min_Margin"] = np.min(margins)
        
        # Extract max margins
        max_margins = []
        for result in results:
            if "Max_Margin" in result and "value" in result["Max_Margin"]:
                max_margins.append(result["Max_Margin"]["value"])
        
        # Calculate max margin statistics
        if max_margins:
            analysis["Average_MaxMargin"] = np.mean(max_margins)
            
            # Find top investor by margin
            top_investor = None
            top_count = 0
            
            investor_counts = {}
            for result in results:
                if "Max_Margin" in result and "investor" in result["Max_Margin"]:
                    investor = result["Max_Margin"]["investor"]
                    investor_counts[investor] = investor_counts.get(investor, 0) + 1
            
            for investor, count in investor_counts.items():
                if count > top_count:
                    top_count = count
                    top_investor = investor
            
            if top_investor:
                analysis["Top_Investor_By_Margin"] = top_investor
        
        return analysis
    
    def _analyze_by_investor(self, results: List[Dict]) -> Dict:
        """
        Analyze results by investor.
        
        Args:
            results: List of filtered pricing result dictionaries
            
        Returns:
            Dictionary mapping investors to analysis results
        """
        investor_analysis = {}
        
        # Process each result
        for result in results:
            # Skip if no investors
            if "Investors" not in result:
                continue
            
            # Process each investor
            for investor, price_info in result["Investors"].items():
                # Skip if no margin
                if "Margin" not in price_info:
                    continue
                
                margin = price_info["Margin"]
                
                # Initialize investor entry if needed
                if investor not in investor_analysis:
                    investor_analysis[investor] = {
                        "margins": [],
                        "count": 0,
                        "sum": 0.0,
                        "max": None
                    }
                
                # Update investor statistics
                investor_analysis[investor]["margins"].append(margin)
                investor_analysis[investor]["count"] += 1
                investor_analysis[investor]["sum"] += margin
                
                if investor_analysis[investor]["max"] is None or margin > investor_analysis[investor]["max"]:
                    investor_analysis[investor]["max"] = margin
        
        # Calculate averages
        for investor, stats in investor_analysis.items():
            if stats["count"] > 0:
                stats["avg"] = stats["sum"] / stats["count"]
            else:
                stats["avg"] = 0.0
            
            # Remove intermediate data
            del stats["margins"]
            del stats["sum"]
        
        return investor_analysis
