import pandas as pd
import numpy as np
import logging
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Set, Tuple, Any, Optional, Union

# Configure logging
logger = logging.getLogger('mortgage_pricing_tool.reverse_optimizer')

class ReversePricingAnalyzer:
    """
    Analyzer for reverse pricing optimization.
    
    This class analyzes pricing results to identify the factors that most
    influence achieving target margin ranges, providing recommendations for
    pricing strategy optimization.
    """
    
    def __init__(self, pricing_results: List[Dict]):
        """
        Initialize the analyzer with pricing results.
        
        Args:
            pricing_results: List of pricing result dictionaries
        """
        self.pricing_results = pricing_results
        
        # Store analysis results
        self.analysis_results = {}
        
        logger.info(f"ReversePricingAnalyzer initialized with {len(pricing_results)} pricing results")
    
    def analyze_target_margin(self, min_margin: float, max_margin: float, investor: Optional[str] = None) -> Dict:
        """
        Analyze scenarios with margins in the target range.
        
        Args:
            min_margin: Minimum target margin
            max_margin: Maximum target margin
            investor: Optional investor to focus on (None means any investor)
            
        Returns:
            Dictionary containing analysis results
        """
        # Reset analysis results
        self.analysis_results = {}
        
        try:
            # Filter scenarios with margins in the target range
            matching_scenarios = self._filter_by_margin_range(min_margin, max_margin, investor)
            
            # Check if we have any matching scenarios
            if not matching_scenarios:
                return {
                    "Total_Matching_Scenarios": 0,
                    "Target_Margin_Range": f"{min_margin:.3f} - {max_margin:.3f}",
                    "Error": "No scenarios found within the target margin range"
                }
            
            # Analyze matching scenarios
            self.analysis_results = self._analyze_matching_scenarios(matching_scenarios, min_margin, max_margin, investor)
            
            return self.analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing target margin: {str(e)}")
            return {
                "Total_Matching_Scenarios": 0,
                "Target_Margin_Range": f"{min_margin:.3f} - {max_margin:.3f}",
                "Error": f"Analysis failed: {str(e)}"
            }
    
    def _filter_by_margin_range(self, min_margin: float, max_margin: float, investor: Optional[str] = None) -> List[Dict]:
        """
        Filter scenarios with margins in the target range.
        
        Args:
            min_margin: Minimum target margin
            max_margin: Maximum target margin
            investor: Optional investor to focus on (None means any investor)
            
        Returns:
            List of matching scenario dictionaries
        """
        matching_scenarios = []
        
        # Process each result
        for result in self.pricing_results:
            # Skip if no investors
            if "Investors" not in result:
                continue
            
            # Check if this scenario has a margin in the target range
            if investor:
                # Check specific investor
                if investor in result["Investors"]:
                    price_info = result["Investors"][investor]
                    if "Margin" in price_info:
                        margin = price_info["Margin"]
                        if min_margin <= margin <= max_margin:
                            matching_scenarios.append(result)
            else:
                # Check any investor
                for inv, price_info in result["Investors"].items():
                    if "Margin" in price_info:
                        margin = price_info["Margin"]
                        if min_margin <= margin <= max_margin:
                            matching_scenarios.append(result)
                            break
        
        logger.info(f"Found {len(matching_scenarios)} scenarios with margins between {min_margin} and {max_margin}")
        return matching_scenarios
    
    def _analyze_matching_scenarios(self, scenarios: List[Dict], min_margin: float, max_margin: float, investor: Optional[str] = None) -> Dict:
        """
        Analyze scenarios with margins in the target range.
        
        Args:
            scenarios: List of matching scenario dictionaries
            min_margin: Minimum target margin
            max_margin: Maximum target margin
            investor: Optional investor to focus on (None means any investor)
            
        Returns:
            Dictionary containing analysis results
        """
        analysis = {}
        
        # Add basic information
        analysis["Total_Matching_Scenarios"] = len(scenarios)
        analysis["Target_Margin_Range"] = f"{min_margin:.3f} - {max_margin:.3f}"
        
        # Analyze by dimension
        dimension_analysis = self._analyze_by_dimension(scenarios)
        analysis["Dimension_Analysis"] = dimension_analysis
        
        # Find top modules by influence
        top_modules = self._find_top_modules_by_influence(dimension_analysis)
        analysis["Top_Modules_By_Influence"] = top_modules
        
        return analysis
    
    def _analyze_by_dimension(self, scenarios: List[Dict]) -> Dict:
        """
        Analyze scenarios by dimension.
        
        Args:
            scenarios: List of scenario dictionaries
            
        Returns:
            Dictionary mapping dimensions to analysis results
        """
        dimension_analysis = {}
        
        # Get all dimensions
        dimensions = set()
        for scenario in scenarios:
            for key in scenario.keys():
                if key not in ["Sheet", "SourceType", "Program", "Base_Price", "LLPA_Adjustments", 
                              "Final_Price", "AAA_Final_Price", "Margin", "Investors", "Max_Margin"]:
                    dimensions.add(key)
        
        # Analyze each dimension
        for dimension in dimensions:
            # Count occurrences of each value
            value_counts = {}
            for scenario in scenarios:
                if dimension in scenario:
                    value = scenario[dimension]
                    value_counts[value] = value_counts.get(value, 0) + 1
            
            # Sort by count
            sorted_values = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Add to analysis
            dimension_analysis[dimension] = {
                "value_counts": dict(sorted_values),
                "top_value": sorted_values[0][0] if sorted_values else None,
                "top_count": sorted_values[0][1] if sorted_values else 0
            }
        
        return dimension_analysis
    
    def _find_top_modules_by_influence(self, dimension_analysis: Dict) -> List[Dict]:
        """
        Find the top modules by influence on target margin.
        
        Args:
            dimension_analysis: Dictionary mapping dimensions to analysis results
            
        Returns:
            List of dictionaries with top module information
        """
        # Calculate influence score for each dimension
        influence_scores = []
        
        for dimension, analysis in dimension_analysis.items():
            # Skip dimensions with no values
            if not analysis["value_counts"]:
                continue
            
            # Calculate entropy (lower entropy means higher influence)
            total_count = sum(analysis["value_counts"].values())
            entropy = 0
            for count in analysis["value_counts"].values():
                p = count / total_count
                entropy -= p * np.log2(p)
            
            # Calculate dominance (higher dominance means higher influence)
            top_count = analysis["top_count"]
            dominance = top_count / total_count if total_count > 0 else 0
            
            # Calculate influence score (higher is better)
            influence_score = dominance * (1 - entropy / 4)  # Normalize entropy
            
            influence_scores.append({
                "Module": dimension,
                "Top_Condition": analysis["top_value"],
                "Frequency": top_count,
                "Influence_Score": influence_score
            })
        
        # Sort by influence score
        sorted_scores = sorted(influence_scores, key=lambda x: x["Influence_Score"], reverse=True)
        
        # Return top 10 or all if less than 10
        return sorted_scores[:10]
    
    def create_influence_chart(self) -> Optional[go.Figure]:
        """
        Create a chart visualizing the influence of different modules.
        
        Returns:
            Plotly figure object, or None if chart creation fails
        """
        try:
            # Check if we have analysis results
            if not self.analysis_results or "Top_Modules_By_Influence" not in self.analysis_results:
                logger.warning("No analysis results available for chart creation")
                return None
            
            # Get top modules
            top_modules = self.analysis_results["Top_Modules_By_Influence"]
            
            # Create dataframe for plotting
            df = pd.DataFrame(top_modules)
            
            # Sort by frequency
            df = df.sort_values("Frequency", ascending=True)
            
            # Create horizontal bar chart
            fig = px.bar(
                df,
                y="Module",
                x="Frequency",
                color="Frequency",
                color_continuous_scale="Viridis",
                labels={"Module": "Factor", "Frequency": "Frequency in Target Range"},
                title="Top Factors Influencing Target Margin Range",
                text="Top_Condition"
            )
            
            # Update layout
            fig.update_layout(
                height=500,
                margin=dict(l=20, r=20, t=40, b=20),
                coloraxis_showscale=False
            )
            
            # Add text annotations
            fig.update_traces(
                texttemplate="%{text}",
                textposition="inside"
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating influence chart: {str(e)}")
            return None
    
    def get_influence_dataframe(self) -> pd.DataFrame:
        """
        Get a DataFrame of influence analysis for export.
        
        Returns:
            DataFrame containing influence analysis
        """
        try:
            # Check if we have analysis results
            if not self.analysis_results or "Top_Modules_By_Influence" not in self.analysis_results:
                logger.warning("No analysis results available for export")
                return pd.DataFrame()
            
            # Get top modules
            top_modules = self.analysis_results["Top_Modules_By_Influence"]
            
            # Create dataframe
            df = pd.DataFrame(top_modules)
            
            # Add target margin range
            if "Target_Margin_Range" in self.analysis_results:
                df["Target_Margin_Range"] = self.analysis_results["Target_Margin_Range"]
            
            # Add total matching scenarios
            if "Total_Matching_Scenarios" in self.analysis_results:
                df["Total_Matching_Scenarios"] = self.analysis_results["Total_Matching_Scenarios"]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating influence dataframe: {str(e)}")
            return pd.DataFrame()
