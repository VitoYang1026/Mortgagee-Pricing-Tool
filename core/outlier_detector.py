import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Set, Tuple, Any, Optional, Union

# Configure logging
logger = logging.getLogger('mortgage_pricing_tool.outlier_detector')

class MarginAnomalyDetector:
    """
    Detector for identifying margin anomalies.
    
    This class analyzes pricing results to identify scenarios with margins
    that fall outside the acceptable range, helping to detect potential
    pricing issues or opportunities.
    """
    
    def __init__(self, pricing_results: List[Dict]):
        """
        Initialize the detector with pricing results.
        
        Args:
            pricing_results: List of pricing result dictionaries
        """
        self.pricing_results = pricing_results
        
        # Store anomalies
        self.anomalies = []
        
        # Store statistics
        self.stats = {}
        
        logger.info(f"MarginAnomalyDetector initialized with {len(pricing_results)} pricing results")
    
    def find_margin_outliers(self, min_margin: float, max_margin: float) -> List[Dict]:
        """
        Find scenarios with margins outside the acceptable range.
        
        Args:
            min_margin: Minimum acceptable margin
            max_margin: Maximum acceptable margin
            
        Returns:
            List of anomaly dictionaries
        """
        # Reset anomalies
        self.anomalies = []
        
        try:
            # Process each result
            for result in self.pricing_results:
                # Skip if no investors
                if "Investors" not in result:
                    continue
                
                # Check each investor
                for investor, price_info in result["Investors"].items():
                    # Skip if no margin
                    if "Margin" not in price_info:
                        continue
                    
                    margin = price_info["Margin"]
                    
                    # Check if margin is outside acceptable range
                    if margin < min_margin:
                        self._add_anomaly(result, investor, margin, "Too Low", min_margin, max_margin)
                    elif margin > max_margin:
                        self._add_anomaly(result, investor, margin, "Too High", min_margin, max_margin)
            
            # Calculate statistics
            self._calculate_statistics()
            
            logger.info(f"Found {len(self.anomalies)} margin anomalies")
            return self.anomalies
            
        except Exception as e:
            logger.error(f"Error finding margin outliers: {str(e)}")
            return []
    
    def _add_anomaly(self, result: Dict, investor: str, margin: float, status: str, min_margin: float, max_margin: float) -> None:
        """
        Add an anomaly to the list.
        
        Args:
            result: Scenario dictionary
            investor: Investor name
            margin: Margin value
            status: Anomaly status ("Too Low" or "Too High")
            min_margin: Minimum acceptable margin
            max_margin: Maximum acceptable margin
        """
        # Create anomaly dictionary
        anomaly = {
            "Investor": investor,
            "Margin": margin,
            "Status": status,
            "Acceptable_Range": f"{min_margin:.3f} - {max_margin:.3f}"
        }
        
        # Add scenario information
        for key, value in result.items():
            if key not in ["Investors", "Max_Margin"]:
                anomaly[key] = value
        
        # Add to anomalies
        self.anomalies.append(anomaly)
    
    def _calculate_statistics(self) -> None:
        """Calculate statistics about the anomalies."""
        # Count total anomalies
        self.stats["total_anomalies"] = len(self.anomalies)
        
        # Count by status
        self.stats["high_margin_anomalies"] = len([a for a in self.anomalies if a.get("Status") == "Too High"])
        self.stats["low_margin_anomalies"] = len([a for a in self.anomalies if a.get("Status") == "Too Low"])
        
        # Count by investor
        investor_counts = {}
        for anomaly in self.anomalies:
            investor = anomaly.get("Investor")
            if investor:
                investor_counts[investor] = investor_counts.get(investor, 0) + 1
        
        self.stats["investor_counts"] = investor_counts
    
    def get_anomalies_dataframe(self) -> pd.DataFrame:
        """
        Get a DataFrame of anomalies for display or export.
        
        Returns:
            DataFrame containing anomalies
        """
        try:
            # Check if we have anomalies
            if not self.anomalies:
                logger.warning("No anomalies available for export")
                return pd.DataFrame()
            
            # Create dataframe
            df = pd.DataFrame(self.anomalies)
            
            # Reorder columns
            if "Investor" in df.columns and "Margin" in df.columns and "Status" in df.columns:
                first_cols = ["Investor", "Margin", "Status", "Acceptable_Range"]
                other_cols = [col for col in df.columns if col not in first_cols]
                df = df[first_cols + other_cols]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating anomalies dataframe: {str(e)}")
            return pd.DataFrame()
    
    def get_anomalies_by_status(self, status: str) -> List[Dict]:
        """
        Get anomalies filtered by status.
        
        Args:
            status: Status to filter by ("Too Low" or "Too High")
            
        Returns:
            List of anomaly dictionaries
        """
        return [a for a in self.anomalies if a.get("Status") == status]
