#!/usr/bin/env python3
"""
Performance Report Generator for Budget Management Application

This script generates comprehensive performance reports for the Budget Management Application
by analyzing execution metrics, API response times, and component performance. It collects data
from logs and Cloud Run job executions to provide insights on system efficiency and identify 
potential bottlenecks.

Usage:
    python performance_report.py --project-id=your-project-id --days=30 --visualize
"""

import argparse
import os
import sys
import json
import datetime
from typing import Dict, List, Optional, Any, Union

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS
from ..config.path_constants import LOGS_DIR, ensure_dir_exists
from .check_job_status import JobStatusChecker
from .analyze_logs import LogAnalyzer, extract_performance_metrics

# Initialize logger
logger = get_logger('performance_report')

# Default values
DEFAULT_PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', None)
DEFAULT_JOB_NAME = 'budget-management-job'
DEFAULT_REGION = 'us-east1'
DEFAULT_DAYS = 30
DEFAULT_OUTPUT_DIR = os.path.join(LOGS_DIR, 'performance')
DEFAULT_OUTPUT_FORMAT = 'html'

# Component names for categorizing performance metrics
COMPONENT_NAMES = [
    'transaction_retriever',
    'transaction_categorizer',
    'budget_analyzer',
    'insight_generator',
    'report_distributor',
    'savings_automator'
]

# Performance thresholds for each component/operation in seconds
PERFORMANCE_THRESHOLDS = {
    'job_execution': 300,  # 5 minutes total execution
    'transaction_retrieval': 30,
    'transaction_categorization': 60,
    'budget_analysis': 15,
    'insight_generation': 30,
    'email_delivery': 10,
    'savings_transfer': 30
}


class PerformanceMetric:
    """Class representing a performance metric with statistics"""
    
    def __init__(self, name: str, component: str, operation: str, values: List[float], threshold: float):
        """
        Initialize a performance metric
        
        Args:
            name: Name of the metric
            component: Component the metric belongs to
            operation: Specific operation being measured
            values: List of measured values
            threshold: Performance threshold for this metric
        """
        self.name = name
        self.component = component
        self.operation = operation
        self.values = values
        self.threshold = threshold
        
        # Calculate statistics
        if values:
            self.min = min(values)
            self.max = max(values)
            self.avg = sum(values) / len(values)
            
            # Calculate median
            sorted_values = sorted(values)
            self.median = sorted_values[len(sorted_values) // 2]
            
            # Calculate 95th percentile if we have enough data
            if len(values) >= 20:
                self.p95 = sorted_values[int(len(sorted_values) * 0.95)]
            else:
                self.p95 = None
        else:
            self.min = self.max = self.avg = self.median = 0
            self.p95 = None
    
    def exceeds_threshold(self) -> bool:
        """
        Check if metric exceeds threshold
        
        Returns:
            True if exceeds threshold, False otherwise
        """
        return self.avg > self.threshold
    
    def to_dict(self) -> Dict:
        """
        Convert metric to dictionary
        
        Returns:
            Dictionary representation of metric
        """
        return {
            'name': self.name,
            'component': self.component,
            'operation': self.operation,
            'min': self.min,
            'max': self.max,
            'avg': self.avg,
            'median': self.median,
            'p95': self.p95,
            'count': len(self.values),
            'threshold': self.threshold,
            'exceeds_threshold': self.exceeds_threshold()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PerformanceMetric':
        """
        Create a PerformanceMetric from dictionary
        
        Args:
            data: Dictionary containing metric data
            
        Returns:
            Created metric instance
        """
        name = data.get('name', 'unknown')
        component = data.get('component', 'unknown')
        operation = data.get('operation', 'unknown')
        values = data.get('values', [])
        threshold = data.get('threshold', 5.0)
        
        return cls(name, component, operation, values, threshold)


class PerformanceAnalyzer:
    """Class that handles performance data collection and analysis"""
    
    def __init__(self, project_id: str, job_name: str, region: str, log_file: str, days: int):
        """
        Initialize the performance analyzer with configuration
        
        Args:
            project_id: Google Cloud project ID
            job_name: Name of the Cloud Run job
            region: Region where the job is deployed
            log_file: Path to the log file
            days: Number of days of data to analyze
        """
        self.project_id = project_id
        self.job_name = job_name
        self.region = region
        self.log_file = log_file
        self.days = days
        
        # Initialize core services
        self.job_checker = JobStatusChecker(project_id, job_name, region)
        self.log_analyzer = LogAnalyzer(log_file)
        
        logger.info(
            "Performance Analyzer initialized",
            context={
                "project_id": project_id,
                "job_name": job_name,
                "log_file": log_file,
                "days": days
            }
        )
    
    def collect_all_metrics(self, component: Optional[str] = None) -> Dict:
        """
        Collect all performance metrics
        
        Args:
            component: Optional component name to filter by
            
        Returns:
            Complete performance metrics
        """
        logger.info("Collecting all performance metrics")
        
        # Collect job performance metrics
        job_metrics = collect_job_performance_data(self.project_id, self.job_name, self.region, self.days)
        
        # Load and filter logs
        self.log_analyzer.load_logs()
        self.log_analyzer.filter_logs(days=self.days, component=component)
        
        # Collect component performance metrics
        component_metrics = collect_component_performance_data(self.log_file, self.days, component)
        
        # Collect API performance metrics
        api_metrics = collect_api_performance_data(self.log_file, self.days)
        
        # Combine all metrics
        metrics = {
            "job_performance": job_metrics,
            "component_performance": component_metrics,
            "api_performance": api_metrics,
            "analysis_timestamp": datetime.datetime.now().isoformat(),
            "days_analyzed": self.days,
            "component_filter": component
        }
        
        logger.info("Performance metrics collection completed")
        return metrics
    
    def analyze_metrics(self, metrics: Dict) -> Dict:
        """
        Analyze collected performance metrics
        
        Args:
            metrics: Complete performance metrics
            
        Returns:
            Analysis results
        """
        logger.info("Analyzing performance metrics")
        
        # Analyze performance trends
        trend_analysis = analyze_performance_trends(
            metrics["job_performance"],
            metrics["component_performance"],
            metrics["api_performance"]
        )
        
        # Identify bottlenecks
        bottlenecks = identify_bottlenecks(metrics)
        
        # Compile analysis results
        analysis = {
            "trend_analysis": trend_analysis,
            "bottlenecks": bottlenecks,
            "analysis_timestamp": datetime.datetime.now().isoformat()
        }
        
        logger.info("Performance metrics analysis completed")
        return analysis
    
    def generate_visualizations(self, metrics: Dict, output_dir: str) -> List[str]:
        """
        Generate performance visualizations
        
        Args:
            metrics: Performance metrics data
            output_dir: Directory to save visualizations
            
        Returns:
            Visualization file paths
        """
        logger.info("Generating performance visualizations")
        
        # Generate visualizations
        visualization_paths = generate_performance_visualizations(metrics, output_dir)
        
        logger.info(f"Generated {len(visualization_paths)} visualizations")
        return visualization_paths
    
    def generate_report(self, metrics: Dict, analysis: Dict, visualizations: List[str], 
                       output_format: str, output_dir: str) -> str:
        """
        Generate performance report
        
        Args:
            metrics: Performance metrics data
            analysis: Analysis results
            visualizations: List of visualization file paths
            output_format: Output format (json, html, markdown)
            output_dir: Directory to save report
            
        Returns:
            Report file path
        """
        logger.info(f"Generating performance report in {output_format} format")
        
        # Combine metrics and analysis
        performance_data = {
            "metrics": metrics,
            "analysis": analysis
        }
        
        # Generate report
        report_path = generate_performance_report(
            performance_data,
            output_format,
            output_dir,
            visualizations
        )
        
        logger.info(f"Performance report generated at {report_path}")
        return report_path
    
    def get_summary(self, metrics: Dict, analysis: Dict) -> str:
        """
        Get a summary of performance metrics
        
        Args:
            metrics: Performance metrics data
            analysis: Analysis results
            
        Returns:
            Summary text
        """
        # Create summary header
        summary = [
            f"Performance Summary (Last {self.days} days)",
            f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # Add job execution summary
        job_perf = metrics.get("job_performance", {})
        execution_stats = job_perf.get("execution_time_stats", {})
        
        if execution_stats:
            summary.append("JOB EXECUTION TIMES:")
            summary.append(f"  Average: {execution_stats.get('avg', 0):.2f} seconds")
            summary.append(f"  Median: {execution_stats.get('median', 0):.2f} seconds")
            summary.append(f"  Min: {execution_stats.get('min', 0):.2f} seconds")
            summary.append(f"  Max: {execution_stats.get('max', 0):.2f} seconds")
            summary.append("")
        
        # Add component performance summary
        comp_perf = metrics.get("component_performance", {})
        if comp_perf:
            summary.append("COMPONENT PERFORMANCE:")
            for component, operations in comp_perf.items():
                summary.append(f"  {component}:")
                for operation, stats in operations.items():
                    avg_time = stats.get("avg", 0)
                    threshold = PERFORMANCE_THRESHOLDS.get(operation, 5.0)
                    status = "✓" if avg_time <= threshold else "⚠"
                    summary.append(f"    {operation}: {avg_time:.2f}s (threshold: {threshold}s) {status}")
            summary.append("")
        
        # Add API performance summary
        api_perf = metrics.get("api_performance", {})
        if api_perf:
            summary.append("API PERFORMANCE:")
            for api, stats in api_perf.items():
                avg_time = stats.get("avg_response_time", 0)
                success_rate = stats.get("success_rate", 100)
                summary.append(f"  {api}: {avg_time:.2f}s response time, {success_rate:.1f}% success rate")
            summary.append("")
        
        # Add bottleneck summary
        bottlenecks = analysis.get("bottlenecks", {}).get("identified_bottlenecks", [])
        if bottlenecks:
            summary.append("BOTTLENECKS:")
            for bottleneck in bottlenecks:
                summary.append(f"  {bottleneck.get('component')} - {bottleneck.get('operation')}: {bottleneck.get('avg_time', 0):.2f}s")
                summary.append(f"    {bottleneck.get('recommendation', '')}")
            summary.append("")
        
        return "\n".join(summary)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for the script
    
    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Generate performance reports for the Budget Management Application'
    )
    
    parser.add_argument(
        '--project-id',
        default=DEFAULT_PROJECT_ID,
        help='Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT env var)'
    )
    
    parser.add_argument(
        '--job-name',
        default=DEFAULT_JOB_NAME,
        help=f'Name of the Cloud Run job (default: {DEFAULT_JOB_NAME})'
    )
    
    parser.add_argument(
        '--region',
        default=DEFAULT_REGION,
        help=f'Region where the job is deployed (default: {DEFAULT_REGION})'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=DEFAULT_DAYS,
        help=f'Number of days of data to analyze (default: {DEFAULT_DAYS})'
    )
    
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Directory to write output files (default: {DEFAULT_OUTPUT_DIR})'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'html', 'markdown'],
        default=DEFAULT_OUTPUT_FORMAT,
        help=f'Output format for the report (default: {DEFAULT_OUTPUT_FORMAT})'
    )
    
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Generate visualizations of performance metrics'
    )
    
    parser.add_argument(
        '--component',
        choices=COMPONENT_NAMES,
        help='Filter analysis to a specific component'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args()


def collect_job_performance_data(project_id: str, job_name: str, region: str, days: int) -> Dict:
    """
    Collect performance data from Cloud Run job executions
    
    Args:
        project_id: Google Cloud project ID
        job_name: Name of the Cloud Run job
        region: Region where the job is deployed
        days: Number of days of history to retrieve
        
    Returns:
        Job performance metrics and execution data
    """
    logger.info(f"Collecting job performance data for {job_name}")
    
    # Initialize job status checker
    job_checker = JobStatusChecker(project_id, job_name, region)
    
    # Get job executions
    executions = job_checker.get_executions(days=days)
    
    # Analyze executions
    analysis = job_checker.analyze_executions(executions)
    
    # Extract execution time statistics
    execution_time_stats = {}
    if 'duration_stats' in analysis:
        execution_time_stats = analysis['duration_stats']
    
    # Extract execution time trend
    time_trend = analysis.get('time_trend', 'unknown')
    
    # Compile job performance data
    job_performance = {
        "executions": executions,
        "execution_time_stats": execution_time_stats,
        "time_trend": time_trend,
        "success_rate": analysis.get('success_rate', 0),
        "error_patterns": analysis.get('error_patterns', [])
    }
    
    logger.info(f"Collected performance data for {len(executions)} job executions")
    return job_performance


def collect_component_performance_data(log_file: str, days: int, component: Optional[str] = None) -> Dict:
    """
    Collect performance data for individual application components
    
    Args:
        log_file: Path to log file
        days: Number of days of data to analyze
        component: Optional component name to filter by
        
    Returns:
        Component performance metrics by operation
    """
    logger.info(f"Collecting component performance data from {log_file}")
    
    # Initialize log analyzer
    log_analyzer = LogAnalyzer(log_file)
    
    # Load logs
    log_analyzer.load_logs()
    
    # Filter logs by date and component
    log_analyzer.filter_logs(days=days, component=component)
    
    # Extract performance metrics
    metrics = extract_performance_metrics(log_analyzer.logs)
    
    # If no metrics found in the structured format, try to extract from log messages
    if not metrics:
        # Custom extraction logic for each component
        component_metrics = {}
        
        for comp in COMPONENT_NAMES if not component else [component]:
            # Filter logs for this component
            comp_logs = log_analyzer.filter_logs(component=comp)
            
            operations = {}
            
            # Look for common timing patterns in log messages
            for log in comp_logs:
                # Example: "Operation X completed in 1.23 seconds"
                # Example: "Function Y executed in 2.34s"
                # Example: "Processed Z in 3.45ms"
                
                if "completed in" in log.message:
                    parts = log.message.split("completed in")
                    if len(parts) == 2:
                        try:
                            operation = parts[0].strip()
                            time_str = parts[1].strip()
                            time_val = float(time_str.split()[0])
                            
                            if operation not in operations:
                                operations[operation] = []
                            
                            operations[operation].append(time_val)
                        except Exception:
                            pass
            
            # Calculate statistics for each operation
            for operation, values in operations.items():
                if values:
                    operations[operation] = {
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values),
                        "median": sorted(values)[len(values) // 2],
                        "count": len(values)
                    }
            
            if operations:
                component_metrics[comp] = operations
        
        metrics = component_metrics
    
    logger.info(f"Collected performance data for {len(metrics)} components")
    return metrics


def collect_api_performance_data(log_file: str, days: int) -> Dict:
    """
    Collect performance data for external API interactions
    
    Args:
        log_file: Path to log file
        days: Number of days of data to analyze
        
    Returns:
        API performance metrics by service
    """
    logger.info(f"Collecting API performance data from {log_file}")
    
    # Initialize log analyzer
    log_analyzer = LogAnalyzer(log_file)
    
    # Load logs
    log_analyzer.load_logs()
    
    # Filter logs by date
    log_analyzer.filter_logs(days=days)
    
    # Define API service names
    api_services = ['Capital One', 'Google Sheets', 'Gemini', 'Gmail']
    
    # Initialize result structure
    api_metrics = {}
    
    # For each API service, extract performance data
    for api in api_services:
        # Filter logs related to this API
        api_logs = log_analyzer.filter_logs(pattern=api.lower())
        
        # Extract response times
        response_times = []
        success_count = 0
        failure_count = 0
        
        for log in api_logs:
            # Look for response time information
            if "response time" in log.message.lower():
                try:
                    time_str = log.message.split("response time")[1].strip()
                    time_val = float(time_str.split()[0])
                    response_times.append(time_val)
                except Exception:
                    pass
            
            # Count successes and failures
            if log.level == "INFO" and ("success" in log.message.lower() or "succeeded" in log.message.lower()):
                success_count += 1
            elif log.level in ["ERROR", "CRITICAL"] or "fail" in log.message.lower() or "error" in log.message.lower():
                failure_count += 1
        
        # Calculate statistics
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            sorted_times = sorted(response_times)
            median_response_time = sorted_times[len(sorted_times) // 2]
            
            # Calculate success rate
            total_operations = success_count + failure_count
            success_rate = (success_count / total_operations * 100) if total_operations > 0 else 0
            
            api_metrics[api] = {
                "avg_response_time": avg_response_time,
                "min_response_time": min_response_time,
                "max_response_time": max_response_time,
                "median_response_time": median_response_time,
                "response_time_samples": len(response_times),
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": success_rate
            }
    
    logger.info(f"Collected performance data for {len(api_metrics)} API services")
    return api_metrics


def analyze_performance_trends(job_performance: Dict, component_performance: Dict, api_performance: Dict) -> Dict:
    """
    Analyze performance trends over time
    
    Args:
        job_performance: Job performance metrics
        component_performance: Component performance metrics
        api_performance: API performance metrics
        
    Returns:
        Performance trend analysis
    """
    logger.info("Analyzing performance trends")
    
    # Convert job executions to DataFrame for time series analysis
    executions_df = None
    if job_performance and 'executions' in job_performance:
        executions = job_performance['executions']
        if executions:
            # Create DataFrame
            exec_data = []
            for exec in executions:
                if exec.get('start_time') and exec.get('duration'):
                    exec_data.append({
                        'timestamp': exec['start_time'],
                        'duration': exec['duration'],
                        'status': exec['status']
                    })
            
            if exec_data:
                executions_df = pd.DataFrame(exec_data)
                executions_df['timestamp'] = pd.to_datetime(executions_df['timestamp'])
                executions_df.set_index('timestamp', inplace=True)
                executions_df.sort_index(inplace=True)
    
    # Initialize trend analysis results
    trend_analysis = {
        "job_execution_trend": job_performance.get('time_trend', 'unknown'),
        "component_trends": {},
        "api_trends": {},
        "significant_changes": [],
        "moving_averages": {}
    }
    
    # Analyze job execution trends
    if executions_df is not None and len(executions_df) >= 3:
        # Calculate moving average for execution duration
        trend_analysis["moving_averages"]["job_execution"] = executions_df['duration'].rolling(window=3).mean().tolist()
        
        # Detect significant changes (more than 25% change)
        for i in range(1, len(executions_df)):
            prev_duration = executions_df['duration'].iloc[i-1]
            curr_duration = executions_df['duration'].iloc[i]
            
            if prev_duration > 0:
                change_pct = ((curr_duration - prev_duration) / prev_duration) * 100
                
                if abs(change_pct) > 25:
                    trend_analysis["significant_changes"].append({
                        "timestamp": executions_df.index[i].isoformat(),
                        "metric": "job_execution_time",
                        "previous": float(prev_duration),
                        "current": float(curr_duration),
                        "change_pct": float(change_pct)
                    })
    
    # Analyze component performance trends (limited analysis without time series data)
    for component, operations in component_performance.items():
        component_trend = "stable"  # Default to stable
        
        # If time series data were available, we could do more here
        # For now, just compare to thresholds
        for operation, stats in operations.items():
            threshold = PERFORMANCE_THRESHOLDS.get(operation, 5.0)
            if stats.get("avg", 0) > threshold * 1.5:
                component_trend = "degrading"
                break
        
        trend_analysis["component_trends"][component] = component_trend
    
    # Analyze API performance trends (limited analysis without time series data)
    for api, stats in api_performance.items():
        # Default threshold: 2 seconds
        threshold = 2.0
        
        if api == "Gemini":
            threshold = 5.0  # AI operations can take longer
        
        if stats.get("avg_response_time", 0) > threshold:
            trend_analysis["api_trends"][api] = "slow"
        else:
            trend_analysis["api_trends"][api] = "normal"
    
    logger.info("Performance trend analysis completed")
    return trend_analysis


def identify_bottlenecks(performance_data: Dict) -> Dict:
    """
    Identify performance bottlenecks in the application
    
    Args:
        performance_data: Complete performance data
        
    Returns:
        Identified bottlenecks and recommendations
    """
    logger.info("Identifying performance bottlenecks")
    
    # Initialize bottleneck results
    bottlenecks = {
        "identified_bottlenecks": [],
        "recommendations": []
    }
    
    # Check job execution time
    job_perf = performance_data.get("job_performance", {})
    job_stats = job_perf.get("execution_time_stats", {})
    
    if job_stats.get("avg", 0) > PERFORMANCE_THRESHOLDS["job_execution"]:
        bottlenecks["identified_bottlenecks"].append({
            "component": "overall_job",
            "operation": "execution",
            "avg_time": job_stats.get("avg", 0),
            "threshold": PERFORMANCE_THRESHOLDS["job_execution"],
            "severity": "high"
        })
        
        bottlenecks["recommendations"].append(
            "Overall job execution time exceeds threshold. Review component bottlenecks to identify specific areas for optimization."
        )
    
    # Check component performance
    comp_perf = performance_data.get("component_performance", {})
    for component, operations in comp_perf.items():
        for operation, stats in operations.items():
            # Determine relevant threshold
            threshold = 5.0  # Default threshold
            
            for key, value in PERFORMANCE_THRESHOLDS.items():
                if key in operation.lower():
                    threshold = value
                    break
            
            # Check if average time exceeds threshold
            if stats.get("avg", 0) > threshold:
                bottlenecks["identified_bottlenecks"].append({
                    "component": component,
                    "operation": operation,
                    "avg_time": stats.get("avg", 0),
                    "threshold": threshold,
                    "severity": "medium" if stats.get("avg", 0) < threshold * 1.5 else "high"
                })
                
                # Add specific recommendation based on the component/operation
                if "transaction_retrieval" in operation.lower():
                    bottlenecks["recommendations"].append(
                        f"Optimize {component} {operation} by implementing request batching or caching frequently accessed data."
                    )
                elif "categorization" in operation.lower():
                    bottlenecks["recommendations"].append(
                        f"Improve {component} {operation} performance by optimizing Gemini API prompts or implementing a local cache for common transaction patterns."
                    )
                elif "analysis" in operation.lower():
                    bottlenecks["recommendations"].append(
                        f"Enhance {component} {operation} by optimizing data processing algorithms or implementing incremental calculations."
                    )
                elif "generation" in operation.lower():
                    bottlenecks["recommendations"].append(
                        f"Speed up {component} {operation} by simplifying AI prompts or implementing partial insight generation with asynchronous completion."
                    )
                elif "email" in operation.lower() or "delivery" in operation.lower():
                    bottlenecks["recommendations"].append(
                        f"Improve {component} {operation} by optimizing email content size or implementing asynchronous delivery."
                    )
                elif "transfer" in operation.lower() or "savings" in operation.lower():
                    bottlenecks["recommendations"].append(
                        f"Optimize {component} {operation} by implementing better error handling and retry logic for bank API interactions."
                    )
                else:
                    bottlenecks["recommendations"].append(
                        f"Review {component} {operation} for performance optimization opportunities."
                    )
    
    # Check API performance
    api_perf = performance_data.get("api_performance", {})
    for api, stats in api_perf.items():
        # Determine relevant threshold
        threshold = 2.0  # Default threshold
        if api == "Gemini":
            threshold = 5.0  # AI operations can take longer
        
        # Check if average response time exceeds threshold
        if stats.get("avg_response_time", 0) > threshold:
            bottlenecks["identified_bottlenecks"].append({
                "component": "api",
                "operation": f"{api} API",
                "avg_time": stats.get("avg_response_time", 0),
                "threshold": threshold,
                "severity": "medium" if stats.get("avg_response_time", 0) < threshold * 1.5 else "high"
            })
            
            # Add specific recommendation based on the API
            if api == "Capital One":
                bottlenecks["recommendations"].append(
                    f"Optimize {api} API interactions by implementing request batching, response caching, or more efficient data filtering."
                )
            elif api == "Google Sheets":
                bottlenecks["recommendations"].append(
                    f"Improve {api} API performance by batching read/write operations or implementing a more efficient data storage approach."
                )
            elif api == "Gemini":
                bottlenecks["recommendations"].append(
                    f"Enhance {api} API performance by optimizing prompt design, reducing token usage, or implementing response caching for similar requests."
                )
            elif api == "Gmail":
                bottlenecks["recommendations"].append(
                    f"Speed up {api} API interactions by optimizing email content size or implementing asynchronous sending."
                )
    
    # Attach recommendations to bottlenecks for more specific guidance
    for bottleneck in bottlenecks["identified_bottlenecks"]:
        # Find matching recommendation if any
        for recommendation in bottlenecks["recommendations"]:
            if bottleneck["component"] in recommendation and bottleneck["operation"] in recommendation:
                bottleneck["recommendation"] = recommendation
                break
        
        # Use generic recommendation if none matched
        if "recommendation" not in bottleneck:
            bottleneck["recommendation"] = f"Review {bottleneck['component']} {bottleneck['operation']} for optimization opportunities."
    
    logger.info(f"Identified {len(bottlenecks['identified_bottlenecks'])} performance bottlenecks")
    return bottlenecks


def generate_performance_visualizations(performance_data: Dict, output_dir: str) -> List[str]:
    """
    Generate visualizations of performance metrics
    
    Args:
        performance_data: Performance metrics data
        output_dir: Directory to save visualizations
        
    Returns:
        Paths to generated visualization files
    """
    logger.info(f"Generating performance visualizations in {output_dir}")
    
    # Ensure output directory exists
    ensure_dir_exists(output_dir)
    
    # Initialize list for visualization paths
    visualization_paths = []
    
    # Set the style for all visualizations
    plt.style.use('ggplot')
    
    # Generate timestamp for unique filenames
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. Job Execution Time Chart
    if "job_performance" in performance_data and "execution_time_stats" in performance_data["job_performance"]:
        job_perf = performance_data["job_performance"]
        
        if "executions" in job_perf and job_perf["executions"]:
            # Create DataFrame from executions
            exec_data = []
            for exec in job_perf["executions"]:
                if exec.get('start_time') and exec.get('duration'):
                    exec_data.append({
                        'timestamp': exec['start_time'],
                        'duration': exec['duration'],
                        'status': exec['status']
                    })
            
            if exec_data:
                df = pd.DataFrame(exec_data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.sort_values('timestamp', inplace=True)
                
                # Create figure
                fig, ax = plt.subplots(figsize=(12, 6))
                
                # Plot successful executions in green, failed in red
                for status, group in df.groupby('status'):
                    color = 'green' if status == 'SUCCEEDED' else 'red'
                    ax.scatter(group['timestamp'], group['duration'], c=color, label=status, alpha=0.7)
                
                # Add moving average line
                if len(df) >= 3:
                    df['moving_avg'] = df['duration'].rolling(window=3).mean()
                    ax.plot(df['timestamp'], df['moving_avg'], 'b-', label='3-point Moving Average', linewidth=2)
                
                # Add threshold line
                ax.axhline(y=PERFORMANCE_THRESHOLDS['job_execution'], color='orange', linestyle='--', 
                          label=f'Threshold ({PERFORMANCE_THRESHOLDS["job_execution"]}s)')
                
                # Customize chart
                ax.set_title('Job Execution Time Trend')
                ax.set_xlabel('Execution Date')
                ax.set_ylabel('Execution Time (seconds)')
                ax.legend()
                ax.grid(True)
                
                # Set y-axis to start from 0
                ax.set_ylim(bottom=0)
                
                # Format x-axis date labels
                fig.autofmt_xdate()
                
                # Save chart
                filename = f"job_execution_time_{timestamp}.png"
                filepath = os.path.join(output_dir, filename)
                fig.savefig(filepath, dpi=100, bbox_inches='tight')
                plt.close(fig)
                
                visualization_paths.append(filepath)
    
    # 2. Component Performance Chart
    if "component_performance" in performance_data:
        comp_perf = performance_data["component_performance"]
        
        if comp_perf:
            # Create data for bar chart
            components = []
            operations = []
            times = []
            threshold_values = []
            
            for component, ops in comp_perf.items():
                for operation, stats in ops.items():
                    components.append(component)
                    operations.append(operation)
                    times.append(stats.get("avg", 0))
                    
                    # Determine relevant threshold
                    threshold = 5.0  # Default threshold
                    for key, value in PERFORMANCE_THRESHOLDS.items():
                        if key in operation.lower():
                            threshold = value
                            break
                    
                    threshold_values.append(threshold)
            
            if components:
                # Create DataFrame
                df = pd.DataFrame({
                    'component': components,
                    'operation': operations,
                    'avg_time': times,
                    'threshold': threshold_values
                })
                
                # Sort by average time descending
                df.sort_values('avg_time', ascending=False, inplace=True)
                
                # Take top 15 operations for readability
                df = df.head(15)
                
                # Create figure
                fig, ax = plt.subplots(figsize=(12, 8))
                
                # Create labels for x-axis
                labels = [f"{row['component']}\n{row['operation'][:20]}" for _, row in df.iterrows()]
                
                # Create bar colors based on threshold comparison
                colors = ['green' if t <= th else 'red' for t, th in zip(df['avg_time'], df['threshold'])]
                
                # Plot bars
                bars = ax.bar(labels, df['avg_time'], color=colors)
                
                # Add threshold markers
                for i, threshold in enumerate(df['threshold']):
                    ax.plot([i-0.4, i+0.4], [threshold, threshold], 'k--', alpha=0.7)
                
                # Customize chart
                ax.set_title('Component Operation Performance')
                ax.set_xlabel('Component Operation')
                ax.set_ylabel('Average Time (seconds)')
                ax.grid(True, axis='y')
                
                # Set y-axis to start from 0
                ax.set_ylim(bottom=0)
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                           f'{height:.2f}s', ha='center', va='bottom')
                
                # Rotate x-axis labels for readability
                plt.xticks(rotation=45, ha='right')
                
                # Adjust layout
                fig.tight_layout()
                
                # Save chart
                filename = f"component_performance_{timestamp}.png"
                filepath = os.path.join(output_dir, filename)
                fig.savefig(filepath, dpi=100, bbox_inches='tight')
                plt.close(fig)
                
                visualization_paths.append(filepath)
    
    # 3. API Response Time Chart
    if "api_performance" in performance_data:
        api_perf = performance_data["api_performance"]
        
        if api_perf:
            # Create data for bar chart
            apis = []
            times = []
            success_rates = []
            
            for api, stats in api_perf.items():
                apis.append(api)
                times.append(stats.get("avg_response_time", 0))
                success_rates.append(stats.get("success_rate", 100))
            
            if apis:
                # Create figure with two y-axes
                fig, ax1 = plt.subplots(figsize=(10, 6))
                ax2 = ax1.twinx()
                
                # Plot response times as bars
                colors = ['green' if t <= 2.0 or (api == 'Gemini' and t <= 5.0) else 'red' for api, t in zip(apis, times)]
                bars = ax1.bar(apis, times, color=colors, alpha=0.7)
                
                # Plot success rates as line
                ax2.plot(apis, success_rates, 'bo-', linewidth=2, markersize=8)
                
                # Customize chart
                ax1.set_title('API Performance')
                ax1.set_xlabel('API Service')
                ax1.set_ylabel('Average Response Time (seconds)', color='tab:red')
                ax2.set_ylabel('Success Rate (%)', color='tab:blue')
                
                # Set y-axis limits
                ax1.set_ylim(bottom=0)
                ax2.set_ylim(50, 105)  # Success rate from 50% to 105%
                
                # Add grid
                ax1.grid(True, axis='y', alpha=0.3)
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                           f'{height:.2f}s', ha='center', va='bottom')
                
                # Add value labels for success rates
                for i, rate in enumerate(success_rates):
                    ax2.text(i, rate + 1, f'{rate:.1f}%', ha='center', va='bottom', color='blue')
                
                # Adjust layout
                fig.tight_layout()
                
                # Save chart
                filename = f"api_performance_{timestamp}.png"
                filepath = os.path.join(output_dir, filename)
                fig.savefig(filepath, dpi=100, bbox_inches='tight')
                plt.close(fig)
                
                visualization_paths.append(filepath)
    
    # 4. Bottleneck Analysis Chart
    if "analysis" in performance_data and "bottlenecks" in performance_data["analysis"]:
        bottlenecks = performance_data["analysis"]["bottlenecks"]
        
        if "identified_bottlenecks" in bottlenecks and bottlenecks["identified_bottlenecks"]:
            # Create data for bar chart
            bottleneck_list = bottlenecks["identified_bottlenecks"]
            labels = [f"{b['component']}\n{b['operation'][:20]}" for b in bottleneck_list]
            times = [b['avg_time'] for b in bottleneck_list]
            thresholds = [b['threshold'] for b in bottleneck_list]
            severities = [b['severity'] for b in bottleneck_list]
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Create bar colors based on severity
            colors = ['orange' if s == 'medium' else 'red' for s in severities]
            
            # Plot bars
            bars = ax.bar(labels, times, color=colors)
            
            # Add threshold markers
            for i, threshold in enumerate(thresholds):
                ax.plot([i-0.4, i+0.4], [threshold, threshold], 'k--', alpha=0.7)
            
            # Customize chart
            ax.set_title('Performance Bottlenecks')
            ax.set_xlabel('Component Operation')
            ax.set_ylabel('Average Time (seconds)')
            ax.grid(True, axis='y')
            
            # Set y-axis to start from 0
            ax.set_ylim(bottom=0)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{height:.2f}s', ha='center', va='bottom')
            
            # Rotate x-axis labels for readability
            plt.xticks(rotation=45, ha='right')
            
            # Add legend
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='red', label='High Severity'),
                Patch(facecolor='orange', label='Medium Severity'),
                Patch(facecolor='grey', alpha=0.3, label='Threshold')
            ]
            ax.legend(handles=legend_elements, loc='upper right')
            
            # Adjust layout
            fig.tight_layout()
            
            # Save chart
            filename = f"bottlenecks_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            visualization_paths.append(filepath)
    
    # 5. Performance Trend Chart (if we have time series data)
    if ("job_performance" in performance_data and 
        "executions" in performance_data["job_performance"] and 
        performance_data["job_performance"]["executions"]):
        
        executions = performance_data["job_performance"]["executions"]
        
        # Create DataFrame from executions
        exec_data = []
        for exec in executions:
            if exec.get('start_time') and exec.get('duration'):
                exec_data.append({
                    'timestamp': exec['start_time'],
                    'duration': exec['duration'],
                    'status': exec['status']
                })
        
        if len(exec_data) >= 5:  # Need enough data for trend analysis
            df = pd.DataFrame(exec_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.sort_values('timestamp', inplace=True)
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Calculate rolling statistics
            df['moving_avg'] = df['duration'].rolling(window=3, min_periods=1).mean()
            df['trend'] = df['moving_avg'].rolling(window=5, min_periods=3).mean()
            
            # Plot actual values as scatter
            ax.scatter(df['timestamp'], df['duration'], c='grey', alpha=0.5, label='Actual')
            
            # Plot moving average and trend
            ax.plot(df['timestamp'], df['moving_avg'], 'b-', label='3-point Moving Average', linewidth=2)
            ax.plot(df['timestamp'], df['trend'], 'r-', label='Trend', linewidth=3)
            
            # Add threshold line
            ax.axhline(y=PERFORMANCE_THRESHOLDS['job_execution'], color='orange', linestyle='--', 
                      label=f'Threshold ({PERFORMANCE_THRESHOLDS["job_execution"]}s)')
            
            # Customize chart
            ax.set_title('Performance Trend Analysis')
            ax.set_xlabel('Date')
            ax.set_ylabel('Execution Time (seconds)')
            ax.legend()
            ax.grid(True)
            
            # Set y-axis to start from 0
            ax.set_ylim(bottom=0)
            
            # Format x-axis date labels
            fig.autofmt_xdate()
            
            # Save chart
            filename = f"performance_trend_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            visualization_paths.append(filepath)
    
    logger.info(f"Generated {len(visualization_paths)} performance visualizations")
    return visualization_paths


def generate_performance_report(performance_data: Dict, output_format: str, output_dir: str, 
                              visualization_paths: Optional[List[str]] = None) -> str:
    """
    Generate a comprehensive performance report
    
    Args:
        performance_data: Performance metrics and analysis
        output_format: Format of the report (json, html, markdown)
        output_dir: Directory to save the report
        visualization_paths: Optional paths to visualization files
        
    Returns:
        Path to the generated report file
    """
    logger.info(f"Generating performance report in {output_format} format")
    
    # Ensure output directory exists
    ensure_dir_exists(output_dir)
    
    # Create report filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"performance_report_{timestamp}.{output_format}"
    filepath = os.path.join(output_dir, filename)
    
    if output_format == 'json':
        # JSON format - direct dump of performance data
        with open(filepath, 'w') as f:
            json.dump(performance_data, f, indent=2, default=str)
    
    elif output_format == 'html':
        # HTML format with embedded visualizations
        html_content = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '  <title>Performance Report - Budget Management Application</title>',
            '  <style>',
            '    body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }',
            '    h1 { color: #2196F3; }',
            '    h2 { color: #0D47A1; border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-top: 30px; }',
            '    h3 { color: #1976D2; }',
            '    table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }',
            '    th, td { text-align: left; padding: 8px; border: 1px solid #ddd; }',
            '    th { background-color: #f2f2f2; }',
            '    tr:nth-child(even) { background-color: #f9f9f9; }',
            '    .good { color: green; }',
            '    .warning { color: orange; }',
            '    .critical { color: red; }',
            '    .image-container { margin: 20px 0; text-align: center; }',
            '    img { max-width: 100%; height: auto; border: 1px solid #ddd; box-shadow: 0 0 10px rgba(0,0,0,0.1); }',
            '    .summary-box { background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }',
            '    .recommendations { background-color: #fff8e1; padding: 15px; border-radius: 5px; margin: 20px 0; }',
            '    .bottleneck { margin-bottom: 10px; padding: 10px; border-left: 4px solid #f44336; background-color: #ffebee; }',
            '    .threshold-met { border-left: 4px solid #4CAF50; background-color: #E8F5E9; }',
            '  </style>',
            '</head>',
            '<body>',
            f'  <h1>Performance Report - Budget Management Application</h1>',
            f'  <p>Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>'
        ]
        
        # Add summary section
        metrics = performance_data.get("metrics", {})
        analysis = performance_data.get("analysis", {})
        
        html_content.append('  <div class="summary-box">')
        html_content.append('    <h2>Executive Summary</h2>')
        
        # Job performance summary
        job_perf = metrics.get("job_performance", {})
        execution_stats = job_perf.get("execution_time_stats", {})
        
        if execution_stats:
            avg_time = execution_stats.get("avg", 0)
            threshold = PERFORMANCE_THRESHOLDS["job_execution"]
            status_class = "good" if avg_time <= threshold else "critical"
            
            html_content.append(f'    <p>Average job execution time: <span class="{status_class}">{avg_time:.2f} seconds</span> (threshold: {threshold} seconds)</p>')
            html_content.append(f'    <p>Success rate: {job_perf.get("success_rate", 0):.1f}%</p>')
        
        # Bottleneck summary
        bottlenecks = analysis.get("bottlenecks", {}).get("identified_bottlenecks", [])
        if bottlenecks:
            html_content.append(f'    <p>Identified <span class="critical">{len(bottlenecks)}</span> performance bottlenecks requiring attention.</p>')
        else:
            html_content.append(f'    <p>No significant performance bottlenecks identified.</p>')
        
        html_content.append('  </div>')
        
        # Add visualizations if available
        if visualization_paths:
            html_content.append('  <h2>Performance Visualizations</h2>')
            for path in visualization_paths:
                img_name = os.path.basename(path)
                # Use relative path for image src
                img_relative_path = os.path.relpath(path, output_dir)
                html_content.append('  <div class="image-container">')
                html_content.append(f'    <img src="{img_relative_path}" alt="{img_name}" />')
                html_content.append('  </div>')
        
        # Add job performance section
        html_content.append('  <h2>Job Execution Performance</h2>')
        
        if job_perf:
            html_content.append('  <h3>Execution Time Statistics</h3>')
            html_content.append('  <table>')
            html_content.append('    <tr><th>Metric</th><th>Value</th></tr>')
            
            for metric, value in execution_stats.items():
                html_content.append(f'    <tr><td>{metric.capitalize()}</td><td>{value:.2f} seconds</td></tr>')
            
            html_content.append('  </table>')
            
            html_content.append(f'  <p>Execution time trend: {job_perf.get("time_trend", "unknown")}</p>')
            
            # Add recent executions
            if "executions" in job_perf and job_perf["executions"]:
                html_content.append('  <h3>Recent Executions</h3>')
                html_content.append('  <table>')
                html_content.append('    <tr><th>Timestamp</th><th>Status</th><th>Duration</th></tr>')
                
                for exec in job_perf["executions"][:10]:  # Show the 10 most recent
                    status_class = "good" if exec.get("status") == "SUCCEEDED" else "critical"
                    html_content.append('    <tr>')
                    html_content.append(f'      <td>{exec.get("start_time", "N/A")}</td>')
                    html_content.append(f'      <td class="{status_class}">{exec.get("status", "N/A")}</td>')
                    html_content.append(f'      <td>{exec.get("duration", "N/A"):.2f} seconds</td>')
                    html_content.append('    </tr>')
                
                html_content.append('  </table>')
        
        # Add component performance section
        html_content.append('  <h2>Component Performance</h2>')
        
        comp_perf = metrics.get("component_performance", {})
        if comp_perf:
            html_content.append('  <table>')
            html_content.append('    <tr><th>Component</th><th>Operation</th><th>Avg Time</th><th>Min Time</th><th>Max Time</th><th>Count</th><th>Status</th></tr>')
            
            # Flatten and sort component operations by average time
            comp_ops = []
            for component, operations in comp_perf.items():
                for operation, stats in operations.items():
                    threshold = 5.0  # Default threshold
                    for key, value in PERFORMANCE_THRESHOLDS.items():
                        if key in operation.lower():
                            threshold = value
                            break
                    
                    comp_ops.append({
                        "component": component,
                        "operation": operation,
                        "avg": stats.get("avg", 0),
                        "min": stats.get("min", 0),
                        "max": stats.get("max", 0),
                        "count": stats.get("count", 0),
                        "threshold": threshold
                    })
            
            # Sort by average time (descending)
            comp_ops.sort(key=lambda x: x["avg"], reverse=True)
            
            for op in comp_ops:
                status_class = "critical" if op["avg"] > op["threshold"] else "good"
                status_text = "Exceeds threshold" if op["avg"] > op["threshold"] else "Within threshold"
                
                html_content.append('    <tr>')
                html_content.append(f'      <td>{op["component"]}</td>')
                html_content.append(f'      <td>{op["operation"]}</td>')
                html_content.append(f'      <td>{op["avg"]:.2f}s</td>')
                html_content.append(f'      <td>{op["min"]:.2f}s</td>')
                html_content.append(f'      <td>{op["max"]:.2f}s</td>')
                html_content.append(f'      <td>{op["count"]}</td>')
                html_content.append(f'      <td class="{status_class}">{status_text}<br>({op["threshold"]}s)</td>')
                html_content.append('    </tr>')
            
            html_content.append('  </table>')
        
        # Add API performance section
        html_content.append('  <h2>API Performance</h2>')
        
        api_perf = metrics.get("api_performance", {})
        if api_perf:
            html_content.append('  <table>')
            html_content.append('    <tr><th>API</th><th>Avg Response Time</th><th>Min</th><th>Max</th><th>Success Rate</th></tr>')
            
            for api, stats in api_perf.items():
                threshold = 5.0 if api == "Gemini" else 2.0
                status_class = "critical" if stats.get("avg_response_time", 0) > threshold else "good"
                
                html_content.append('    <tr>')
                html_content.append(f'      <td>{api}</td>')
                html_content.append(f'      <td class="{status_class}">{stats.get("avg_response_time", 0):.2f}s</td>')
                html_content.append(f'      <td>{stats.get("min_response_time", 0):.2f}s</td>')
                html_content.append(f'      <td>{stats.get("max_response_time", 0):.2f}s</td>')
                html_content.append(f'      <td>{stats.get("success_rate", 0):.1f}%</td>')
                html_content.append('    </tr>')
            
            html_content.append('  </table>')
        
        # Add bottlenecks section
        html_content.append('  <h2>Performance Bottlenecks</h2>')
        
        bottlenecks = analysis.get("bottlenecks", {})
        if bottlenecks and "identified_bottlenecks" in bottlenecks:
            if not bottlenecks["identified_bottlenecks"]:
                html_content.append('  <p>No significant performance bottlenecks identified.</p>')
            else:
                for bottleneck in bottlenecks["identified_bottlenecks"]:
                    severity_class = "critical" if bottleneck.get("severity") == "high" else "warning"
                    
                    html_content.append(f'  <div class="bottleneck">')
                    html_content.append(f'    <h3 class="{severity_class}">{bottleneck.get("component")} - {bottleneck.get("operation")}</h3>')
                    html_content.append(f'    <p>Average time: <span class="{severity_class}">{bottleneck.get("avg_time", 0):.2f}s</span> (threshold: {bottleneck.get("threshold", 0):.2f}s)</p>')
                    
                    if "recommendation" in bottleneck:
                        html_content.append(f'    <p><strong>Recommendation:</strong> {bottleneck["recommendation"]}</p>')
                    
                    html_content.append('  </div>')
        
        # Add recommendations section
        html_content.append('  <h2>Optimization Recommendations</h2>')
        html_content.append('  <div class="recommendations">')
        
        recommendations = bottlenecks.get("recommendations", [])
        if not recommendations:
            html_content.append('    <p>No specific optimization recommendations.</p>')
        else:
            html_content.append('    <ul>')
            for recommendation in recommendations:
                html_content.append(f'      <li>{recommendation}</li>')
            html_content.append('    </ul>')
        
        html_content.append('  </div>')
        
        # Close HTML
        html_content.extend([
            '</body>',
            '</html>'
        ])
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(html_content))
    
    elif output_format == 'markdown':
        # Markdown format with visualization links
        md_content = [
            '# Performance Report - Budget Management Application',
            '',
            f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            ''
        ]
        
        # Add summary section
        metrics = performance_data.get("metrics", {})
        analysis = performance_data.get("analysis", {})
        
        md_content.append('## Executive Summary')
        md_content.append('')
        
        # Job performance summary
        job_perf = metrics.get("job_performance", {})
        execution_stats = job_perf.get("execution_time_stats", {})
        
        if execution_stats:
            avg_time = execution_stats.get("avg", 0)
            threshold = PERFORMANCE_THRESHOLDS["job_execution"]
            
            md_content.append(f'Average job execution time: **{avg_time:.2f} seconds** (threshold: {threshold} seconds)')
            md_content.append(f'Success rate: **{job_perf.get("success_rate", 0):.1f}%**')
            md_content.append('')
        
        # Bottleneck summary
        bottlenecks = analysis.get("bottlenecks", {}).get("identified_bottlenecks", [])
        if bottlenecks:
            md_content.append(f'Identified **{len(bottlenecks)}** performance bottlenecks requiring attention.')
        else:
            md_content.append(f'No significant performance bottlenecks identified.')
        
        md_content.append('')
        
        # Add visualizations if available
        if visualization_paths:
            md_content.append('## Performance Visualizations')
            md_content.append('')
            
            for path in visualization_paths:
                img_name = os.path.basename(path)
                # Use relative path for image reference
                img_relative_path = os.path.relpath(path, output_dir)
                md_content.append(f'![{img_name}]({img_relative_path})')
                md_content.append('')
        
        # Add job performance section
        md_content.append('## Job Execution Performance')
        md_content.append('')
        
        if job_perf:
            md_content.append('### Execution Time Statistics')
            md_content.append('')
            md_content.append('| Metric | Value |')
            md_content.append('| ------ | ----- |')
            
            for metric, value in execution_stats.items():
                md_content.append(f'| {metric.capitalize()} | {value:.2f} seconds |')
            
            md_content.append('')
            md_content.append(f'Execution time trend: **{job_perf.get("time_trend", "unknown")}**')
            md_content.append('')
            
            # Add recent executions
            if "executions" in job_perf and job_perf["executions"]:
                md_content.append('### Recent Executions')
                md_content.append('')
                md_content.append('| Timestamp | Status | Duration |')
                md_content.append('| --------- | ------ | -------- |')
                
                for exec in job_perf["executions"][:10]:  # Show the 10 most recent
                    md_content.append(f'| {exec.get("start_time", "N/A")} | {exec.get("status", "N/A")} | {exec.get("duration", "N/A"):.2f} seconds |')
                
                md_content.append('')
        
        # Add component performance section
        md_content.append('## Component Performance')
        md_content.append('')
        
        comp_perf = metrics.get("component_performance", {})
        if comp_perf:
            md_content.append('| Component | Operation | Avg Time | Min Time | Max Time | Count | Status |')
            md_content.append('| --------- | --------- | -------- | -------- | -------- | ----- | ------ |')
            
            # Flatten and sort component operations by average time
            comp_ops = []
            for component, operations in comp_perf.items():
                for operation, stats in operations.items():
                    threshold = 5.0  # Default threshold
                    for key, value in PERFORMANCE_THRESHOLDS.items():
                        if key in operation.lower():
                            threshold = value
                            break
                    
                    comp_ops.append({
                        "component": component,
                        "operation": operation,
                        "avg": stats.get("avg", 0),
                        "min": stats.get("min", 0),
                        "max": stats.get("max", 0),
                        "count": stats.get("count", 0),
                        "threshold": threshold
                    })
            
            # Sort by average time (descending)
            comp_ops.sort(key=lambda x: x["avg"], reverse=True)
            
            for op in comp_ops:
                status_text = "❌ Exceeds threshold" if op["avg"] > op["threshold"] else "✅ Within threshold"
                
                md_content.append(f'| {op["component"]} | {op["operation"]} | {op["avg"]:.2f}s | {op["min"]:.2f}s | {op["max"]:.2f}s | {op["count"]} | {status_text} ({op["threshold"]}s) |')
            
            md_content.append('')
        
        # Add API performance section
        md_content.append('## API Performance')
        md_content.append('')
        
        api_perf = metrics.get("api_performance", {})
        if api_perf:
            md_content.append('| API | Avg Response Time | Min | Max | Success Rate |')
            md_content.append('| --- | ----------------- | --- | --- | ------------ |')
            
            for api, stats in api_perf.items():
                threshold = 5.0 if api == "Gemini" else 2.0
                status_marker = "❌" if stats.get("avg_response_time", 0) > threshold else "✅"
                
                md_content.append(f'| {api} | {status_marker} {stats.get("avg_response_time", 0):.2f}s | {stats.get("min_response_time", 0):.2f}s | {stats.get("max_response_time", 0):.2f}s | {stats.get("success_rate", 0):.1f}% |')
            
            md_content.append('')
        
        # Add bottlenecks section
        md_content.append('## Performance Bottlenecks')
        md_content.append('')
        
        bottlenecks = analysis.get("bottlenecks", {})
        if bottlenecks and "identified_bottlenecks" in bottlenecks:
            if not bottlenecks["identified_bottlenecks"]:
                md_content.append('No significant performance bottlenecks identified.')
                md_content.append('')
            else:
                for bottleneck in bottlenecks["identified_bottlenecks"]:
                    severity = "⚠️ HIGH" if bottleneck.get("severity") == "high" else "⚠️ MEDIUM"
                    
                    md_content.append(f'### {bottleneck.get("component")} - {bottleneck.get("operation")} ({severity})')
                    md_content.append('')
                    md_content.append(f'Average time: **{bottleneck.get("avg_time", 0):.2f}s** (threshold: {bottleneck.get("threshold", 0):.2f}s)')
                    
                    if "recommendation" in bottleneck:
                        md_content.append('')
                        md_content.append(f'**Recommendation:** {bottleneck["recommendation"]}')
                    
                    md_content.append('')
        
        # Add recommendations section
        md_content.append('## Optimization Recommendations')
        md_content.append('')
        
        recommendations = bottlenecks.get("recommendations", [])
        if not recommendations:
            md_content.append('No specific optimization recommendations.')
            md_content.append('')
        else:
            for recommendation in recommendations:
                md_content.append(f'- {recommendation}')
            
            md_content.append('')
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(md_content))
    
    logger.info(f"Generated {output_format} report at {filepath}")
    return filepath


def main() -> int:
    """
    Main function that orchestrates performance report generation
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        logger.info(
            "Starting performance report generation",
            context={
                "project_id": args.project_id,
                "job_name": args.job_name,
                "days": args.days,
                "output_format": args.format
            }
        )
        
        # Initialize performance analyzer
        analyzer = PerformanceAnalyzer(
            args.project_id,
            args.job_name,
            args.region,
            os.path.join(LOGS_DIR, 'application.log'),
            args.days
        )
        
        # Collect performance metrics
        metrics = analyzer.collect_all_metrics(args.component)
        
        # Analyze metrics
        analysis = analyzer.analyze_metrics(metrics)
        
        # Generate visualizations if requested
        visualization_paths = []
        if args.visualize:
            visualization_paths = analyzer.generate_visualizations(metrics, args.output_dir)
        
        # Generate performance report
        report_path = analyzer.generate_report(
            metrics,
            analysis,
            visualization_paths,
            args.format,
            args.output_dir
        )
        
        # Display summary if verbose output enabled
        if args.verbose:
            summary = analyzer.get_summary(metrics, analysis)
            print("\n" + summary)
        
        # Log completion
        logger.info(f"Performance report generation completed successfully. Report saved to {report_path}")
        
        # Return success
        return 0
    
    except Exception as e:
        logger.error(f"Error generating performance report: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())