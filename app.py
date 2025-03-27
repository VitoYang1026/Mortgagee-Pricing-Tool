import streamlit as st
import pandas as pd
import numpy as np
import base64
import json
import time
import logging
from typing import Dict, List, Any, Optional
import os
import sys

# Import core modules
from mortgage_pricing_tool.core.parser import PricingDataParser
from mortgage_pricing_tool.core.combiner import ScenarioGenerator
from mortgage_pricing_tool.core.calculator import PriceCalculator
from mortgage_pricing_tool.core.analyzer import DataFilterAnalyzer
from mortgage_pricing_tool.core.reverse_optimizer import ReversePricingAnalyzer
from mortgage_pricing_tool.core.outlier_detector import MarginAnomalyDetector
from mortgage_pricing_tool.core.structure_checker import StructureValidator

# Import utilities
from mortgage_pricing_tool.utils.io import save_workbook_data, load_workbook_data, create_download_link, read_excel_file
from mortgage_pricing_tool.utils.constants import DEFAULT_MIN_MARGIN, DEFAULT_MAX_MARGIN, DEFAULT_TARGET_MIN, DEFAULT_TARGET_MAX

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mortgage_pricing_tool')

# Set page config
st.set_page_config(
    page_title="Mortgage Pricing Comparison Tool",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
def initialize_session_state():
    """Initialize all required session state variables if they don't exist."""
    # Core data states
    if 'llpa_adjustments' not in st.session_state:
        st.session_state.llpa_adjustments = None
    if 'base_prices' not in st.session_state:
        st.session_state.base_prices = None
    if 'scenarios' not in st.session_state:
        st.session_state.scenarios = None
    if 'pricing_results' not in st.session_state:
        st.session_state.pricing_results = None
    if 'workbook_data' not in st.session_state:
        st.session_state.workbook_data = None
    
    # Filter states
    if 'filter_dimensions' not in st.session_state:
        st.session_state.filter_dimensions = []
    if 'filter_values' not in st.session_state:
        st.session_state.filter_values = {}
    if 'selected_filters' not in st.session_state:
        st.session_state.selected_filters = {}
    
    # Result states
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'reverse_pricing_results' not in st.session_state:
        st.session_state.reverse_pricing_results = None
    if 'margin_anomalies' not in st.session_state:
        st.session_state.margin_anomalies = None
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = None
    
    # UI control states
    if 'investor_sheets' not in st.session_state:
        st.session_state.investor_sheets = []
    if 'processing_complete' not in st.session_state:
        st.session_state.processing_complete = False
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Upload & Filter"
    
    # Advanced feature states
    if 'target_margin_min' not in st.session_state:
        st.session_state.target_margin_min = DEFAULT_TARGET_MIN
    if 'target_margin_max' not in st.session_state:
        st.session_state.target_margin_max = DEFAULT_TARGET_MAX
    if 'min_margin' not in st.session_state:
        st.session_state.min_margin = DEFAULT_MIN_MARGIN
    if 'max_margin' not in st.session_state:
        st.session_state.max_margin = DEFAULT_MAX_MARGIN


def create_sidebar_navigation():
    """Create the sidebar navigation menu."""
    with st.sidebar:
        st.title("Mortgage Pricing Tool")
        
        # Navigation section
        st.header("Navigation")
        
        # Navigation buttons
        if st.button("Upload & Filter", use_container_width=True, 
                     type="primary" if st.session_state.current_page == "Upload & Filter" else "secondary"):
            st.session_state.current_page = "Upload & Filter"
            st.rerun()
        
        # Only enable these buttons if data is loaded
        if st.session_state.data_loaded:
            if st.button("Structure Validation", use_container_width=True,
                        type="primary" if st.session_state.current_page == "Structure Validation" else "secondary"):
                st.session_state.current_page = "Structure Validation"
                st.rerun()
                
            if st.button("Reverse Pricing", use_container_width=True,
                        type="primary" if st.session_state.current_page == "Reverse Pricing" else "secondary"):
                st.session_state.current_page = "Reverse Pricing"
                st.rerun()
                
            if st.button("Margin Anomaly Detection", use_container_width=True,
                        type="primary" if st.session_state.current_page == "Margin Anomaly Detection" else "secondary"):
                st.session_state.current_page = "Margin Anomaly Detection"
                st.rerun()
        else:
            # Show disabled buttons when data isn't loaded
            st.button("Structure Validation", use_container_width=True, disabled=True)
            st.button("Reverse Pricing", use_container_width=True, disabled=True)
            st.button("Margin Anomaly Detection", use_container_width=True, disabled=True)


def upload_and_filter_page():
    """Render the Upload & Filter page."""
    st.header("Upload & Filter")
    
    # Create two columns for file upload
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("AAA DSCR File")
        aaa_file = st.file_uploader(
            "Upload AAA DSCR Excel file",
            type=["xlsx"],
            key="aaa_file_uploader"
        )
    
    with col2:
        st.subheader("Investor DSCR File")
        investor_file = st.file_uploader(
            "Upload Investor DSCR Excel file",
            type=["xlsx"],
            key="investor_file_uploader"
        )
    
    # Validation option
    validate_on_upload = st.checkbox("Validate structure on upload", value=True)
    
    # Process button
    if st.button("Process Files", type="primary", disabled=(aaa_file is None or investor_file is None)):
        if aaa_file is not None and investor_file is not None:
            with st.spinner("Processing files..."):
                process_uploaded_files(aaa_file, investor_file, validate_on_upload)
    
    # Only show filter controls and results if data is loaded
    if st.session_state.data_loaded:
        st.markdown("---")
        
        # Create two columns for filter and results
        filter_col, results_col = st.columns([1, 3])
        
        with filter_col:
            st.subheader("Filter Criteria")
            create_filter_controls()
        
        with results_col:
            if st.session_state.analysis_results:
                display_analysis_results()
            elif st.session_state.processing_complete:
                st.info("Apply filters to see results.")


def structure_validation_page():
    """Render the Structure Validation page."""
    st.header("Structure Validation")
    
    if not st.session_state.data_loaded:
        st.warning("Please upload and process data files first.")
        return
    
    # Structure validation button
    if st.button("Execute Structure Check", type="primary"):
        with st.spinner("Checking structure consistency..."):
            validate_structure()
    
    # Display validation results if available
    if 'validation_results' in st.session_state and st.session_state.validation_results is not None:
        display_validation_results()


def reverse_pricing_page():
    """Render the Reverse Pricing page."""
    st.header("Reverse Pricing Recommendations")
    
    if not st.session_state.data_loaded:
        st.warning("Please upload and process data files first.")
        return
    
    # Create two columns for controls and results
    control_col, results_col = st.columns([1, 3])
    
    with control_col:
        st.subheader("Target Margin Range")
        
        # Target margin range sliders
        target_min = st.number_input(
            "Minimum Target Margin",
            min_value=0.0,
            max_value=5.0,
            value=st.session_state.target_margin_min,
            step=0.1,
            format="%.2f"
        )
        
        target_max = st.number_input(
            "Maximum Target Margin",
            min_value=target_min,
            max_value=10.0,
            value=max(target_min, st.session_state.target_margin_max),
            step=0.1,
            format="%.2f"
        )
        
        # Investor selection
        investor_options = ["Any Investor"] + st.session_state.investor_sheets
        selected_investor = st.selectbox(
            "Focus on Investor",
            options=investor_options
        )
        
        # Convert "Any Investor" to None for the analyzer
        investor_param = None if selected_investor == "Any Investor" else selected_investor
        
        # Update session state
        st.session_state.target_margin_min = target_min
        st.session_state.target_margin_max = target_max
        
        # Analysis button
        if st.button("Analyze Target Margin", type="primary"):
            with st.spinner("Analyzing target margin range..."):
                analyze_target_margin(target_min, target_max, investor_param)
    
    with results_col:
        if 'reverse_pricing_results' in st.session_state and st.session_state.reverse_pricing_results is not None:
            display_reverse_pricing_results()


def margin_anomaly_page():
    """Render the Margin Anomaly Detection page."""
    st.header("Margin Anomaly Detection")
    
    if not st.session_state.data_loaded:
        st.warning("Please upload and process data files first.")
        return
    
    # Create two columns for controls and results
    control_col, results_col = st.columns([1, 3])
    
    with control_col:
        st.subheader("Acceptable Margin Range")
        
        # Margin range sliders
        min_margin = st.number_input(
            "Minimum Acceptable Margin",
            min_value=0.0,
            max_value=5.0,
            value=st.session_state.min_margin,
            step=0.1,
            format="%.2f"
        )
        
        max_margin = st.number_input(
            "Maximum Acceptable Margin",
            min_value=min_margin,
            max_value=10.0,
            value=max(min_margin, st.session_state.max_margin),
            step=0.1,
            format="%.2f"
        )
        
        # Update session state
        st.session_state.min_margin = min_margin
        st.session_state.max_margin = max_margin
        
        # Detection button
        if st.button("Detect Margin Anomalies", type="primary"):
            with st.spinner("Detecting margin anomalies..."):
                detect_margin_anomalies(min_margin, max_margin)
    
    with results_col:
        if 'margin_anomalies' in st.session_state and st.session_state.margin_anomalies is not None:
            display_margin_anomalies()


def process_uploaded_files(aaa_file, investor_file, validate=True):
    """
    Process uploaded Excel files and generate pricing scenarios.
    
    Args:
        aaa_file: AAA DSCR Excel file
        investor_file: Investor DSCR Excel file
        validate: Whether to validate structure on upload
    """
    try:
        # Reset session state for new uploads
        st.session_state.llpa_adjustments = None
        st.session_state.base_prices = None
        st.session_state.scenarios = None
        st.session_state.pricing_results = None
        st.session_state.analysis_results = None
        st.session_state.reverse_pricing_results = None
        st.session_state.margin_anomalies = None
        st.session_state.validation_results = None
        st.session_state.processing_complete = False
        st.session_state.data_loaded = False
        
        # Step 1: Parse the Excel files
        parser = PricingDataParser()
        
        # Read AAA file
        aaa_data = read_excel_file(aaa_file)
        
        # Read Investor file
        investor_data = read_excel_file(investor_file)
        
        # Parse LLPA adjustments and Base Prices
        llpa_adjustments, base_prices = parser.parse_workbooks(aaa_data, investor_data)
        
        # Store in session state
        st.session_state.llpa_adjustments = llpa_adjustments
        st.session_state.base_prices = base_prices
        
        # Extract investor sheets for UI
        st.session_state.investor_sheets = [
            sheet for sheet in llpa_adjustments.keys()
            if sheet != parser.find_aaa_sheet(llpa_adjustments)
        ]
        
        # Step 2: Generate all possible scenarios
        scenario_generator = ScenarioGenerator(llpa_adjustments)
        scenarios = scenario_generator.generate_all_scenarios()
        
        # Store in session state
        st.session_state.scenarios = scenarios
        
        # Step 3: Calculate prices for all scenarios
        calculator = PriceCalculator(llpa_adjustments, base_prices)
        pricing_results = calculator.calculate_all_prices(scenarios)
        
        # Store in session state
        st.session_state.pricing_results = pricing_results
        
        # Step 4: Initialize the analyzer
        analyzer = DataFilterAnalyzer(pricing_results)
        
        # Store filter dimensions
        st.session_state.filter_dimensions = analyzer.get_available_dimensions()
        
        # Initialize filter values
        filter_values = {}
        for dimension in st.session_state.filter_dimensions:
            values = analyzer.get_dimension_values(dimension)
            if values:
                filter_values[dimension] = values
        
        st.session_state.filter_values = filter_values
        
        # Step 5: Validate structure if requested
        if validate:
            validator = StructureValidator(llpa_adjustments, base_prices)
            validation_results = validator.validate_all_sheets()
            st.session_state.validation_results = validation_results
        
        # Update state
        st.session_state.processing_complete = True
        st.session_state.data_loaded = True
        
        # Show success message
        st.success(f"Files processed successfully. Generated {len(scenarios)} scenarios and {len(pricing_results)} pricing results.")
        
    except Exception as e:
        st.error(f"Error processing files: {str(e)}")
        logger.error(f"Error processing files: {str(e)}", exc_info=True)


def create_filter_controls():
    """Create filter controls based on available dimensions."""
    # Initialize selected filters if not already done
    if not st.session_state.selected_filters:
        st.session_state.selected_filters = {}
    
    # Create filter widgets
    for dimension in st.session_state.filter_dimensions:
        if dimension in st.session_state.filter_values:
            values = st.session_state.filter_values[dimension]
            
            # Special handling for Rate (allow range selection)
            if dimension == "Rate" and values:
                st.subheader(f"{dimension} Range")
                
                # Get min and max values
                min_rate = min(values)
                max_rate = max(values)
                
                # Create range slider
                rate_range = st.slider(
                    f"Select {dimension} Range",
                    min_value=min_rate,
                    max_value=max_rate,
                    value=(min_rate, max_rate),
                    step=0.125
                )
                
                # Store in selected filters
                st.session_state.selected_filters[dimension] = rate_range
                
            # Standard dropdown for other dimensions
            else:
                st.subheader(dimension)
                
                # Add "Any" option
                options = ["Any"] + values
                
                selected = st.selectbox(
                    f"Select {dimension}",
                    options=options,
                    key=f"filter_{dimension}"
                )
                
                # Store in selected filters (None for "Any")
                if selected != "Any":
                    st.session_state.selected_filters[dimension] = selected
                elif dimension in st.session_state.selected_filters:
                    del st.session_state.selected_filters[dimension]
    
    # Apply filters button
    if st.button("Apply Filters", type="primary"):
        with st.spinner("Analyzing data..."):
            apply_filters()


def apply_filters():
    """Apply selected filters and update analysis results."""
    try:
        # Create analyzer
        analyzer = DataFilterAnalyzer(st.session_state.pricing_results)
        
        # Apply filters
        results = analyzer.filter_and_analyze(st.session_state.selected_filters)
        
        # Store results
        st.session_state.analysis_results = results
        
    except Exception as e:
        st.error(f"Error applying filters: {str(e)}")
        logger.error(f"Error applying filters: {str(e)}", exc_info=True)


def display_analysis_results():
    """Display the analysis results."""
    results = st.session_state.analysis_results
    
    if not results:
        st.warning("No analysis results available.")
        return
    
    # Check if there's an error
    if "Error" in results:
        st.error(results["Error"])
        return
    
    # Create tabs for different views
    summary_tab, details_tab, export_tab = st.tabs(["Summary", "Details", "Export"])
    
    with summary_tab:
        # Create two columns for summary stats
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Filter Scope")
            st.write(results["Scope"])
            
            st.subheader("Sample Size")
            st.write(f"{results['SampleSize']} scenarios")
        
        with col2:
            st.subheader("Average Max Margin")
            if results.get("Average_MaxMargin") is not None:
                st.write(f"{results['Average_MaxMargin']:.3f}")
            else:
                st.write("N/A")
            
            st.subheader("Top Investor")
            if results.get("Top_Investor_By_Margin") is not None:
                st.write(results["Top_Investor_By_Margin"])
            else:
                st.write("N/A")
    
    with details_tab:
        st.subheader("Margin Distribution by Investor")
        
        # Create a DataFrame for the margin distribution
        if "Margin_Distribution" in results and results["Margin_Distribution"]:
            data = []
            
            for investor, stats in results["Margin_Distribution"].items():
                data.append({
                    "Investor": investor,
                    "Average Margin": stats["avg"],
                    "Max Margin": stats["max"],
                    "Count": stats["count"]
                })
            
            df = pd.DataFrame(data)
            df = df.sort_values("Average Margin", ascending=False)
            
            st.dataframe(df)
        else:
            st.write("No margin distribution data available.")
    
    with export_tab:
        st.subheader("Export Results")
        
        # Create a DataFrame for export
        if "Margin_Distribution" in results and results["Margin_Distribution"]:
            data = []
            
            for investor, stats in results["Margin_Distribution"].items():
                data.append({
                    "Investor": investor,
                    "Average Margin": stats["avg"],
                    "Max Margin": stats["max"],
                    "Count": stats["count"],
                    "Filter Scope": results["Scope"],
                    "Sample Size": results["SampleSize"]
                })
            
            df = pd.DataFrame(data)
            
            # Create download link
            st.markdown(create_download_link(df, "margin_analysis.csv"), unsafe_allow_html=True)


def validate_structure():
    """Validate the structure of investor sheets against AAA sheet."""
    try:
        # Create validator
        validator = StructureValidator(
            st.session_state.llpa_adjustments,
            st.session_state.base_prices
        )
        
        # Validate all sheets
        validation_results = validator.validate_all_sheets()
        
        # Store results
        st.session_state.validation_results = validation_results
        
    except Exception as e:
        st.error(f"Error validating structure: {str(e)}")
        logger.error(f"Error validating structure: {str(e)}", exc_info=True)


def display_validation_results():
    """Display the structure validation results."""
    results = st.session_state.validation_results
    
    if not results:
        st.warning("No validation results available.")
        return
    
    # Check if there's an error
    if "error" in results["summary"]:
        st.error(results["summary"]["error"])
        return
    
    # Display summary
    st.subheader("Validation Summary")
    
    # Create metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Sheets", results["summary"]["total_sheets"])
    
    with col2:
        st.metric("Sheets with Issues", results["summary"]["sheets_with_issues"])
    
    with col3:
        if results["summary"]["total_sheets"] > 0:
            percentage = (results["summary"]["sheets_with_issues"] / results["summary"]["total_sheets"]) * 100
            st.metric("Issue Percentage", f"{percentage:.1f}%")
        else:
            st.metric("Issue Percentage", "N/A")
    
    # Display details if there are issues
    if results["summary"]["sheets_with_issues"] > 0:
        st.subheader("Issue Details")
        
        # Create tabs for each sheet with issues
        tabs = st.tabs(list(results["details"].keys()))
        
        for i, (sheet_name, issues) in enumerate(results["details"].items()):
            with tabs[i]:
                # Display issues for this sheet
                if "error" in issues:
                    st.error(issues["error"])
                    continue
                
                # Missing modules
                if "missing_modules" in issues:
                    st.warning(f"Missing Modules: {len(issues['missing_modules'])}")
                    st.write(", ".join(issues["missing_modules"]))
                
                # Extra modules
                if "extra_modules" in issues:
                    st.warning(f"Extra Modules: {len(issues['extra_modules'])}")
                    st.write(", ".join(issues["extra_modules"]))
                
                # Wrong module order
                if "wrong_module_order" in issues:
                    st.warning("Module order is incorrect")
                
                # LTV mismatch
                if "ltv_columns_mismatch" in issues:
                    st.warning("LTV columns mismatch")
                    
                    if "ltv_details" in issues:
                        details = issues["ltv_details"]
                        
                        if "missing_ltv_ranges" in details and details["missing_ltv_ranges"]:
                            st.write("Missing LTV ranges:")
                            st.write(", ".join(details["missing_ltv_ranges"]))
                        
                        if "extra_ltv_ranges" in details and details["extra_ltv_ranges"]:
                            st.write("Extra LTV ranges:")
                            st.write(", ".join(details["extra_ltv_ranges"]))
                
                # Missing Base Price rows
                if "base_price_missing_rows" in issues:
                    st.warning(f"Missing Base Price Rows: {issues['base_price_missing_rows']}")
                    
                    if "missing_rates" in issues:
                        st.write("Missing rates:")
                        st.write(", ".join([str(rate) for rate in issues["missing_rates"]]))
    else:
        st.success("All sheets passed validation!")


def analyze_target_margin(min_margin, max_margin, investor=None):
    """
    Analyze scenarios with margins in the target range.
    
    Args:
        min_margin: Minimum target margin
        max_margin: Maximum target margin
        investor: Optional investor to focus on (None means any investor)
    """
    try:
        # Create analyzer
        analyzer = ReversePricingAnalyzer(st.session_state.pricing_results)
        
        # Analyze target margin
        results = analyzer.analyze_target_margin(min_margin, max_margin, investor)
        
        # Store results
        st.session_state.reverse_pricing_results = results
        
    except Exception as e:
        st.error(f"Error analyzing target margin: {str(e)}")
        logger.error(f"Error analyzing target margin: {str(e)}", exc_info=True)


def display_reverse_pricing_results():
    """Display the reverse pricing analysis results."""
    results = st.session_state.reverse_pricing_results
    
    if not results:
        st.warning("No reverse pricing results available.")
        return
    
    # Display summary
    st.subheader("Analysis Summary")
    
    # Create metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Matching Scenarios", results["Total_Matching_Scenarios"])
    
    with col2:
        st.metric("Target Margin Range", results["Target_Margin_Range"])
    
    # Check if we have any matching scenarios
    if results["Total_Matching_Scenarios"] == 0:
        st.warning("No scenarios found within the target margin range.")
        return
    
    # Display top modules
    st.subheader("Top Influential LLPA Modules")
    
    # Create tabs for different views
    table_tab, chart_tab, export_tab = st.tabs(["Table View", "Chart View", "Export"])
    
    with table_tab:
        # Create a DataFrame for the top modules
        if "Top_Modules_By_Influence" in results and results["Top_Modules_By_Influence"]:
            data = []
            
            for module_info in results["Top_Modules_By_Influence"]:
                data.append({
                    "Module": module_info["Module"],
                    "Top Condition": module_info["Top_Condition"],
                    "Frequency": module_info["Frequency"],
                    "Percentage": f"{module_info['Frequency']/results['Total_Matching_Scenarios']*100:.1f}%"
                })
            
            df = pd.DataFrame(data)
            
            st.dataframe(df)
        else:
            st.write("No module influence data available.")
    
    with chart_tab:
        # Create analyzer for chart
        analyzer = ReversePricingAnalyzer(st.session_state.pricing_results)
        analyzer.analysis_results = results
        
        # Create chart
        try:
            fig = analyzer.create_influence_chart()
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Chart creation failed. Plotly may not be available.")
        except Exception as e:
            st.error(f"Error creating chart: {str(e)}")
    
    with export_tab:
        st.subheader("Export Results")
        
        # Create analyzer for export
        analyzer = ReversePricingAnalyzer(st.session_state.pricing_results)
        analyzer.analysis_results = results
        
        # Get influence DataFrame
        df = analyzer.get_influence_dataframe()
        
        if not df.empty:
            # Create download link
            st.markdown(create_download_link(df, "reverse_pricing_analysis.csv"), unsafe_allow_html=True)
        else:
            st.warning("No data available for export.")


def detect_margin_anomalies(min_margin, max_margin):
    """
    Detect margin anomalies outside the acceptable range.
    
    Args:
        min_margin: Minimum acceptable margin
        max_margin: Maximum acceptable margin
    """
    try:
        # Create detector
        detector = MarginAnomalyDetector(st.session_state.pricing_results)
        
        # Detect anomalies
        anomalies = detector.find_margin_outliers(min_margin, max_margin)
        
        # Store results
        st.session_state.margin_anomalies = anomalies
        
    except Exception as e:
        st.error(f"Error detecting margin anomalies: {str(e)}")
        logger.error(f"Error detecting margin anomalies: {str(e)}", exc_info=True)


def display_margin_anomalies():
    """Display the margin anomaly detection results."""
    anomalies = st.session_state.margin_anomalies
    
    if not anomalies:
        st.warning("No margin anomalies detected.")
        return
    
    # Create detector for stats and export
    detector = MarginAnomalyDetector([])  # Empty detector just for the methods
    detector.anomalies = anomalies
    detector.stats = {
        "total_anomalies": len(anomalies),
        "high_margin_anomalies": len([a for a in anomalies if a.get("Status") == "Too High"]),
        "low_margin_anomalies": len([a for a in anomalies if a.get("Status") == "Too Low"])
    }
    
    # Display summary
    st.subheader("Anomaly Summary")
    
    # Create metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Anomalies", detector.stats["total_anomalies"])
    
    with col2:
        st.metric("Too High", detector.stats["high_margin_anomalies"])
    
    with col3:
        st.metric("Too Low", detector.stats["low_margin_anomalies"])
    
    # Create tabs for different views
    all_tab, high_tab, low_tab, export_tab = st.tabs(["All Anomalies", "Too High", "Too Low", "Export"])
    
    with all_tab:
        # Get DataFrame of all anomalies
        df = detector.get_anomalies_dataframe()
        
        if not df.empty:
            st.dataframe(df)
        else:
            st.write("No anomalies to display.")
    
    with high_tab:
        # Get high margin anomalies
        high_anomalies = detector.get_anomalies_by_status("Too High")
        
        if high_anomalies:
            st.dataframe(pd.DataFrame(high_anomalies))
        else:
            st.write("No high margin anomalies to display.")
    
    with low_tab:
        # Get low margin anomalies
        low_anomalies = detector.get_anomalies_by_status("Too Low")
        
        if low_anomalies:
            st.dataframe(pd.DataFrame(low_anomalies))
        else:
            st.write("No low margin anomalies to display.")
    
    with export_tab:
        st.subheader("Export Results")
        
        # Get anomalies DataFrame
        df = detector.get_anomalies_dataframe()
        
        if not df.empty:
            # Create download link
            st.markdown(create_download_link(df, "margin_anomalies.csv"), unsafe_allow_html=True)
        else:
            st.warning("No data available for export.")


def main():
    """Main application entry point."""
    # Initialize session state
    initialize_session_state()
    
    # Create sidebar navigation
    create_sidebar_navigation()
    
    # Render the current page
    if st.session_state.current_page == "Upload & Filter":
        upload_and_filter_page()
    elif st.session_state.current_page == "Structure Validation":
        structure_validation_page()
    elif st.session_state.current_page == "Reverse Pricing":
        reverse_pricing_page()
    elif st.session_state.current_page == "Margin Anomaly Detection":
        margin_anomaly_page()


if __name__ == "__main__":
    main()
