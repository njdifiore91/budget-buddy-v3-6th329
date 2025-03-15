#!/usr/bin/env python3
"""
Log Analysis Script for Budget Management Application

This script analyzes application logs to extract insights, identify patterns,
and generate reports on system behavior. It provides functionality for loading,
filtering, and analyzing log data to monitor application health, track performance
metrics, and detect potential issues.

Usage:
    python analyze_logs.py --log-file=application.log --days=7 --format=html --visualize
"""

import argparse
import os
import sys
import json
import re
import datetime
from collections import Counter, defaultdict
import pandas as pd
import matplotlib.pyplot as plt

# Internal imports
from ..config.logging_setup import get_logger
from ..config.script_settings import SCRIPT_SETTINGS, MAINTENANCE_SETTINGS
from ..config.path_constants import LOGS_DIR, ensure_dir_exists

# Initialize logger
logger = get_logger('analyze_logs')

# Constants
DEFAULT_LOG_FILE = os.path.join(LOGS_DIR, 'application.log')
DEFAULT_OUTPUT_DIR = os.path.join(LOGS_DIR, 'analysis')
DEFAULT_DAYS = 7

# Patterns for matching common errors in logs
ERROR_PATTERNS = [
    r'error', r'exception', r'fail', r'timeout', r'unable to', r'invalid'
]

# Component name mapping patterns
COMPONENT_PATTERNS = {
    r'transaction_retriever': r'TransactionRetriever',
    r'transaction_categorizer': r'TransactionCategorizer', 
    r'budget_analyzer': r'BudgetAnalyzer',
    r'insight_generator': r'InsightGenerator',
    r'report_distributor': r'ReportDistributor',
    r'savings_automator': r'SavingsAutomator'
}

# Patterns for extracting performance metrics from logs
PERFORMANCE_METRICS = [
    r'execution time: (\d+\.?\d*)',
    r'duration: (\d+\.?\d*)',
    r'completed in (\d+\.?\d*)',
    r'response time: (\d+\.?\d*)'
]

class LogEntry:
    """Class representing a structured log entry"""
    
    def __init__(self, log_data):
        """
        Initialize a log entry from raw data
        
        Args:
            log_data: Dictionary containing log entry data
        """
        # Extract required fields with defaults
        self.timestamp = self._parse_timestamp(log_data.get('timestamp', ''))
        self.level = log_data.get('level', 'INFO').upper()
        self.component = log_data.get('component', 'unknown')
        self.message = log_data.get('message', '')
        self.correlation_id = log_data.get('correlation_id', '')
        self.context = log_data.get('context', {})
        
    def _parse_timestamp(self, timestamp_str):
        """Parse timestamp string into datetime object"""
        if not timestamp_str:
            return datetime.datetime.now()
        
        try:
            # Try parsing ISO format
            return datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Try common log formats
                formats = [
                    '%Y-%m-%d %H:%M:%S,%f',
                    '%Y-%m-%d %H:%M:%S.%f',
                    '%Y-%m-%dT%H:%M:%S.%fZ',
                    '%d/%b/%Y:%H:%M:%S %z'
                ]
                
                for fmt in formats:
                    try:
                        return datetime.datetime.strptime(timestamp_str, fmt)
                    except ValueError:
                        continue
                        
                # If all formats fail, use current time
                return datetime.datetime.now()
            except Exception:
                return datetime.datetime.now()
    
    def to_dict(self):
        """
        Convert log entry to dictionary
        
        Returns:
            Dictionary representation of log entry
        """
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'component': self.component,
            'message': self.message,
            'correlation_id': self.correlation_id,
            'context': self.context
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create a LogEntry from dictionary
        
        Args:
            data: Dictionary containing log entry data
            
        Returns:
            LogEntry instance
        """
        return cls(data)
    
    def matches_pattern(self, pattern):
        """
        Check if log entry matches a regex pattern
        
        Args:
            pattern: Regular expression pattern to match
            
        Returns:
            True if matches, False otherwise
        """
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
            return bool(compiled_pattern.search(self.message))
        except Exception:
            return False

class ErrorPattern:
    """Class representing an error pattern found in logs"""
    
    def __init__(self, pattern):
        """
        Initialize an error pattern
        
        Args:
            pattern: Regex pattern string
        """
        self.pattern = pattern
        self.count = 0
        self.examples = []
        self.components = []
    
    def add_occurrence(self, log_entry):
        """
        Add an occurrence of this error pattern
        
        Args:
            log_entry: LogEntry instance
        """
        self.count += 1
        
        # Store example messages (limit to 5)
        if len(self.examples) < 5 and log_entry.message not in self.examples:
            self.examples.append(log_entry.message)
            
        # Track components affected
        if log_entry.component not in self.components:
            self.components.append(log_entry.component)
    
    def to_dict(self):
        """
        Convert error pattern to dictionary
        
        Returns:
            Dictionary representation
        """
        return {
            'pattern': self.pattern,
            'count': self.count,
            'examples': self.examples,
            'components': self.components
        }

class LogAnalyzer:
    """Class that handles log loading, filtering, and analysis"""
    
    def __init__(self, log_file):
        """
        Initialize the log analyzer with log file path
        
        Args:
            log_file: Path to log file
        """
        self.log_file = log_file
        self.logs = []
        self.logs_df = None
        self._analysis_results = None
    
    def load_logs(self):
        """
        Load logs from file
        
        Returns:
            List of parsed log entries
        """
        self.logs = load_log_file(self.log_file)
        self._update_dataframe()
        return self.logs
    
    def _update_dataframe(self):
        """Convert logs to DataFrame for analysis"""
        if not self.logs:
            self.logs_df = pd.DataFrame(columns=['timestamp', 'level', 'component', 'message'])
            return
            
        # Convert logs to DataFrame
        data = [log.to_dict() for log in self.logs]
        self.logs_df = pd.DataFrame(data)
        
        # Ensure timestamp column is datetime
        if 'timestamp' in self.logs_df.columns:
            self.logs_df['timestamp'] = pd.to_datetime(self.logs_df['timestamp'])
    
    def filter_logs(self, days=None, level=None, component=None, pattern=None):
        """
        Apply multiple filters to logs
        
        Args:
            days: Number of days to include from today
            level: Log level to filter by
            component: Component name to filter by
            pattern: Regex pattern to filter by
            
        Returns:
            Filtered log entries
        """
        if not self.logs:
            return []
            
        filtered_logs = self.logs.copy()
        
        # Apply date filter
        if days is not None:
            filtered_logs = filter_logs_by_date(filtered_logs, days)
            
        # Apply level filter
        if level:
            filtered_logs = filter_logs_by_level(filtered_logs, level)
            
        # Apply component filter
        if component:
            filtered_logs = filter_logs_by_component(filtered_logs, component)
            
        # Apply pattern filter
        if pattern:
            filtered_logs = filter_logs_by_pattern(filtered_logs, pattern)
        
        # Update logs and DataFrame
        self.logs = filtered_logs
        self._update_dataframe()
        
        return filtered_logs
    
    def analyze(self):
        """
        Perform comprehensive log analysis
        
        Returns:
            Dictionary containing analysis results
        """
        if not self.logs:
            return {
                'error': 'No logs to analyze',
                'log_count': 0
            }
        
        # Perform various analyses
        level_counts = count_logs_by_level(self.logs)
        component_counts = count_logs_by_component(self.logs)
        error_patterns = extract_error_patterns(self.logs)
        performance_metrics = extract_performance_metrics(self.logs)
        trend_analysis = analyze_log_trends(self.logs)
        performance_analysis = analyze_performance_metrics(self.logs)
        
        # Combine results
        analysis_results = {
            'log_count': len(self.logs),
            'date_range': {
                'start': min(log.timestamp for log in self.logs).isoformat(),
                'end': max(log.timestamp for log in self.logs).isoformat()
            },
            'level_distribution': level_counts,
            'component_distribution': component_counts,
            'error_patterns': error_patterns,
            'performance_metrics': performance_metrics,
            'trend_analysis': trend_analysis,
            'performance_analysis': performance_analysis,
            'analysis_timestamp': datetime.datetime.now().isoformat()
        }
        
        self._analysis_results = analysis_results
        return analysis_results
    
    def get_summary(self):
        """
        Get a summary of the log analysis
        
        Returns:
            Summary text
        """
        if not self._analysis_results:
            return "No analysis results available. Call analyze() first."
        
        results = self._analysis_results
        
        # Create summary header
        summary = [
            f"Log Analysis Summary for {os.path.basename(self.log_file)}",
            f"Period: {results['date_range']['start']} to {results['date_range']['end']}",
            f"Total logs analyzed: {results['log_count']}",
            "\n"
        ]
        
        # Add level distribution
        summary.append("LOG LEVELS:")
        for level, count in results['level_distribution'].items():
            percentage = (count / results['log_count']) * 100
            summary.append(f"  {level}: {count} ({percentage:.1f}%)")
        summary.append("\n")
        
        # Add top components
        summary.append("TOP COMPONENTS:")
        sorted_components = sorted(
            results['component_distribution'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        for component, count in sorted_components:
            percentage = (count / results['log_count']) * 100
            summary.append(f"  {component}: {count} ({percentage:.1f}%)")
        summary.append("\n")
        
        # Add top error patterns
        if results['error_patterns']:
            summary.append("TOP ERROR PATTERNS:")
            for pattern in results['error_patterns'][:5]:
                summary.append(f"  Pattern: {pattern['pattern']}")
                summary.append(f"    Count: {pattern['count']}")
                summary.append(f"    Components: {', '.join(pattern['components'])}")
                if pattern['examples']:
                    summary.append(f"    Example: {pattern['examples'][0]}")
            summary.append("\n")
        
        # Add performance highlights
        if results['performance_analysis'].get('slowest_operations'):
            summary.append("PERFORMANCE HIGHLIGHTS:")
            for op in results['performance_analysis']['slowest_operations'][:3]:
                summary.append(f"  {op['component']} - {op['operation']}: {op['avg_time']:.2f}s avg")
        
        return "\n".join(summary)
    
    def export_to_dataframe(self):
        """
        Export logs to pandas DataFrame
        
        Returns:
            DataFrame containing log data
        """
        if self.logs_df is None:
            self._update_dataframe()
        return self.logs_df
    
    def export_to_csv(self, output_file):
        """
        Export logs to CSV file
        
        Args:
            output_file: Path to output CSV file
            
        Returns:
            Path to the exported CSV file
        """
        df = self.export_to_dataframe()
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            ensure_dir_exists(output_dir)
            
        # Export to CSV
        df.to_csv(output_file, index=False)
        return output_file

def parse_arguments(args=None):
    """
    Parse command line arguments for the script
    
    Args:
        args: Command line arguments (defaults to sys.argv[1:])
        
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Analyze application logs for the Budget Management Application'
    )
    
    parser.add_argument(
        '--log-file',
        default=DEFAULT_LOG_FILE,
        help=f'Path to the log file (default: {DEFAULT_LOG_FILE})'
    )
    
    parser.add_argument(
        '--output-dir',
        default=DEFAULT_OUTPUT_DIR,
        help=f'Directory to write output files (default: {DEFAULT_OUTPUT_DIR})'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=DEFAULT_DAYS,
        help=f'Number of days of logs to analyze (default: {DEFAULT_DAYS})'
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'csv', 'html', 'markdown'],
        default='json',
        help='Output format for the report (default: json)'
    )
    
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Generate visualizations of log analysis'
    )
    
    parser.add_argument(
        '--component',
        help='Filter logs by component name'
    )
    
    parser.add_argument(
        '--level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Filter logs by severity level'
    )
    
    parser.add_argument(
        '--pattern',
        help='Filter logs by regex pattern'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser.parse_args(args)

def load_log_file(log_file):
    """
    Load and parse log file into structured format
    
    Args:
        log_file: Path to log file
        
    Returns:
        List of LogEntry objects
    """
    if not os.path.exists(log_file):
        logger.error(f"Log file not found: {log_file}")
        return []
    
    log_entries = []
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            
        # Determine if logs are in JSON format
        is_json = False
        try:
            # Check if the first non-empty line is valid JSON
            for line in lines:
                if line.strip():
                    json.loads(line.strip())
                    is_json = True
                    break
        except json.JSONDecodeError:
            is_json = False
            
        # Parse logs based on format
        if is_json:
            # Parse JSON logs
            for line in lines:
                if not line.strip():
                    continue
                    
                try:
                    log_data = json.loads(line.strip())
                    log_entries.append(LogEntry(log_data))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON log line: {line[:100]}...")
        else:
            # Parse text logs using regex
            # Example pattern for common log format: TIMESTAMP - LEVEL - COMPONENT - MESSAGE
            pattern = r'(?P<timestamp>[\d\-T:\.Z]+) - level: (?P<level>\w+) - component: (?P<component>[^-]+) - correlation_id: (?P<correlation_id>[^-]*) - message: (?P<message>.*)'
            for line in lines:
                if not line.strip():
                    continue
                    
                match = re.search(pattern, line)
                if match:
                    log_data = match.groupdict()
                    log_entries.append(LogEntry(log_data))
                else:
                    # Fallback: try to extract basic info
                    parts = line.split(' - ')
                    if len(parts) >= 3:
                        log_data = {
                            'timestamp': parts[0],
                            'level': 'INFO', 
                            'component': 'unknown',
                            'message': line
                        }
                        
                        # Try to extract level and component
                        for part in parts[1:]:
                            if part.startswith('level:'):
                                log_data['level'] = part.split(':', 1)[1].strip()
                            elif part.startswith('component:'):
                                log_data['component'] = part.split(':', 1)[1].strip()
                            elif part.startswith('message:'):
                                log_data['message'] = part.split(':', 1)[1].strip()
                                
                        log_entries.append(LogEntry(log_data))
        
        logger.info(f"Loaded {len(log_entries)} log entries from {log_file}")
        return log_entries
    
    except Exception as e:
        logger.error(f"Error loading log file {log_file}: {e}")
        return []

def filter_logs_by_date(logs, days):
    """
    Filter logs by date range
    
    Args:
        logs: List of LogEntry objects
        days: Number of days to include (from today backwards)
        
    Returns:
        Filtered log entries
    """
    if not logs or days is None:
        return logs
        
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    filtered_logs = [log for log in logs if log.timestamp >= cutoff_date]
    
    logger.debug(f"Date filter applied: {len(filtered_logs)}/{len(logs)} logs retained")
    return filtered_logs

def filter_logs_by_level(logs, level):
    """
    Filter logs by severity level
    
    Args:
        logs: List of LogEntry objects
        level: Log level to filter by
        
    Returns:
        Filtered log entries
    """
    if not logs or not level:
        return logs
        
    level = level.upper()
    filtered_logs = [log for log in logs if log.level.upper() == level]
    
    logger.debug(f"Level filter applied: {len(filtered_logs)}/{len(logs)} logs retained")
    return filtered_logs

def filter_logs_by_component(logs, component):
    """
    Filter logs by component name
    
    Args:
        logs: List of LogEntry objects
        component: Component name to filter by
        
    Returns:
        Filtered log entries
    """
    if not logs or not component:
        return logs
        
    # Look for exact match first
    filtered_logs = [log for log in logs if log.component.lower() == component.lower()]
    
    # If no exact matches, try partial matches
    if not filtered_logs:
        filtered_logs = [log for log in logs if component.lower() in log.component.lower()]
    
    logger.debug(f"Component filter applied: {len(filtered_logs)}/{len(logs)} logs retained")
    return filtered_logs

def filter_logs_by_pattern(logs, pattern):
    """
    Filter logs by regex pattern
    
    Args:
        logs: List of LogEntry objects
        pattern: Regex pattern to filter by
        
    Returns:
        Filtered log entries
    """
    if not logs or not pattern:
        return logs
        
    try:
        filtered_logs = [log for log in logs if log.matches_pattern(pattern)]
        logger.debug(f"Pattern filter applied: {len(filtered_logs)}/{len(logs)} logs retained")
        return filtered_logs
    except re.error as e:
        logger.error(f"Invalid regex pattern '{pattern}': {e}")
        return logs

def count_logs_by_level(logs):
    """
    Count log entries by severity level
    
    Args:
        logs: List of LogEntry objects
        
    Returns:
        Dictionary mapping levels to counts
    """
    if not logs:
        return {}
        
    level_counts = Counter(log.level for log in logs)
    return dict(level_counts)

def count_logs_by_component(logs):
    """
    Count log entries by component
    
    Args:
        logs: List of LogEntry objects
        
    Returns:
        Dictionary mapping components to counts
    """
    if not logs:
        return {}
        
    component_counts = Counter(log.component for log in logs)
    return dict(component_counts)

def extract_error_patterns(logs):
    """
    Extract common error patterns from logs
    
    Args:
        logs: List of LogEntry objects
        
    Returns:
        List of dictionaries with error pattern information
    """
    if not logs:
        return []
    
    # Filter to error and critical logs
    error_logs = [log for log in logs if log.level in ('ERROR', 'CRITICAL')]
    if not error_logs:
        return []
    
    # Track error patterns
    patterns = {}
    
    # First pass: extract errors matching known patterns
    for pattern in ERROR_PATTERNS:
        for log in error_logs:
            if log.matches_pattern(pattern):
                if pattern not in patterns:
                    patterns[pattern] = ErrorPattern(pattern)
                patterns[pattern].add_occurrence(log)
    
    # Second pass: look for other common words in error messages
    if len(error_logs) > 10:
        # Extract words from error messages
        all_words = []
        for log in error_logs:
            words = re.findall(r'\b\w+\b', log.message.lower())
            all_words.extend(words)
        
        # Count word frequency
        word_counts = Counter(all_words)
        
        # Find common words not in stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                    'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of'}
        
        for word, count in word_counts.most_common(20):
            if count >= 3 and word not in stopwords and len(word) > 3:
                pattern = r'\b' + re.escape(word) + r'\b'
                
                # Skip if we already have this pattern
                if pattern in patterns:
                    continue
                
                # Check if this word appears in multiple error messages
                matches = 0
                for log in error_logs:
                    if re.search(pattern, log.message, re.IGNORECASE):
                        matches += 1
                
                if matches >= 3:
                    patterns[pattern] = ErrorPattern(pattern)
                    for log in error_logs:
                        if re.search(pattern, log.message, re.IGNORECASE):
                            patterns[pattern].add_occurrence(log)
    
    # Convert patterns to list of dictionaries and sort by count
    result = [pattern.to_dict() for pattern in patterns.values()]
    result.sort(key=lambda x: x['count'], reverse=True)
    
    return result

def extract_performance_metrics(logs):
    """
    Extract performance metrics from logs
    
    Args:
        logs: List of LogEntry objects
        
    Returns:
        Dictionary with performance metrics by component and operation
    """
    if not logs:
        return {}
    
    metrics = defaultdict(lambda: defaultdict(list))
    
    # Search for performance metrics in log messages
    for log in logs:
        component = log.component
        
        for pattern in PERFORMANCE_METRICS:
            matches = re.search(pattern, log.message, re.IGNORECASE)
            if matches:
                try:
                    # Extract timing value
                    time_value = float(matches.group(1))
                    
                    # Try to extract operation name from message
                    operation_match = re.search(r'(completed|executed|processed|finished) (.+?) in', log.message, re.IGNORECASE)
                    if operation_match:
                        operation = operation_match.group(2).strip()
                    else:
                        # Fallback: use the first part of the message
                        operation = log.message.split(' ')[0].strip()
                        if len(operation) > 30:
                            operation = 'operation'
                    
                    # Store metric
                    metrics[component][operation].append(time_value)
                except (ValueError, IndexError):
                    continue
    
    # Calculate statistics for each metric
    result = {}
    for component, operations in metrics.items():
        component_metrics = {}
        for operation, values in operations.items():
            if values:
                component_metrics[operation] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'median': sorted(values)[len(values) // 2],
                    'count': len(values)
                }
        
        if component_metrics:
            result[component] = component_metrics
    
    return result

def analyze_log_trends(logs):
    """
    Analyze trends in log data over time
    
    Args:
        logs: List of LogEntry objects
        
    Returns:
        Dictionary with trend analysis results
    """
    if not logs:
        return {}
    
    # Convert logs to DataFrame
    data = [log.to_dict() for log in logs]
    df = pd.DataFrame(data)
    
    # Ensure timestamp is datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Set timestamp as index
    df.set_index('timestamp', inplace=True)
    
    # Group by day and level
    daily_counts = df.groupby([pd.Grouper(freq='D'), 'level']).size().unstack(fill_value=0)
    
    # Calculate daily totals
    daily_counts['total'] = daily_counts.sum(axis=1)
    
    # Calculate 3-day moving averages
    moving_avgs = daily_counts.rolling(window=3, min_periods=1).mean()
    
    # Identify significant changes (more than 50% change from previous day)
    significant_changes = []
    for level in daily_counts.columns:
        for i in range(1, len(daily_counts)):
            prev_value = daily_counts[level].iloc[i-1]
            curr_value = daily_counts[level].iloc[i]
            
            if prev_value > 0 and abs(curr_value - prev_value) / prev_value > 0.5:
                change_pct = ((curr_value - prev_value) / prev_value) * 100
                significant_changes.append({
                    'date': daily_counts.index[i].strftime('%Y-%m-%d'),
                    'level': level,
                    'previous': int(prev_value),
                    'current': int(curr_value),
                    'change_pct': round(change_pct, 1)
                })
    
    # Convert results to dictionary
    result = {
        'daily_counts': daily_counts.reset_index().to_dict(orient='records'),
        'moving_averages': moving_avgs.reset_index().to_dict(orient='records'),
        'significant_changes': significant_changes
    }
    
    return result

def analyze_performance_metrics(logs):
    """
    Analyze performance metrics from logs
    
    Args:
        logs: List of LogEntry objects
        
    Returns:
        Dictionary with performance analysis results
    """
    if not logs:
        return {}
    
    # Extract raw performance metrics
    metrics = extract_performance_metrics(logs)
    if not metrics:
        return {'message': 'No performance metrics found'}
    
    # Calculate component averages
    component_avgs = {}
    for component, operations in metrics.items():
        total_time = 0
        total_ops = 0
        
        for operation, stats in operations.items():
            total_time += stats['avg'] * stats['count']
            total_ops += stats['count']
        
        if total_ops > 0:
            component_avgs[component] = total_time / total_ops
    
    # Find slowest operations
    all_operations = []
    for component, operations in metrics.items():
        for operation, stats in operations.items():
            all_operations.append({
                'component': component,
                'operation': operation,
                'avg_time': stats['avg'],
                'max_time': stats['max'],
                'count': stats['count']
            })
    
    # Sort by average time (descending)
    all_operations.sort(key=lambda x: x['avg_time'], reverse=True)
    
    # Define performance thresholds
    thresholds = {
        'TransactionRetriever': 30.0,  # seconds
        'TransactionCategorizer': 60.0,
        'BudgetAnalyzer': 15.0,
        'InsightGenerator': 30.0,
        'ReportDistributor': 10.0,
        'SavingsAutomator': 30.0,
        'default': 5.0
    }
    
    # Identify operations exceeding thresholds
    exceeding_threshold = []
    for op in all_operations:
        component = op['component']
        threshold = thresholds.get(component, thresholds['default'])
        
        if op['avg_time'] > threshold:
            exceeding_threshold.append({
                'component': component,
                'operation': op['operation'],
                'avg_time': op['avg_time'],
                'threshold': threshold,
                'excess_pct': ((op['avg_time'] - threshold) / threshold) * 100
            })
    
    # Compile results
    result = {
        'component_averages': [{'component': c, 'avg_time': t} for c, t in component_avgs.items()],
        'slowest_operations': all_operations[:10],  # Top 10 slowest
        'operations_exceeding_threshold': exceeding_threshold
    }
    
    return result

def generate_log_visualizations(analysis_results, output_dir):
    """
    Generate visualizations from log analysis
    
    Args:
        analysis_results: Dictionary with analysis results
        output_dir: Directory to save visualizations
        
    Returns:
        List of paths to generated visualization files
    """
    if not analysis_results:
        return []
    
    # Ensure output directory exists
    ensure_dir_exists(output_dir)
    
    visualization_paths = []
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Set style
    plt.style.use('ggplot')
    
    # 1. Log level distribution chart
    if 'level_distribution' in analysis_results:
        fig, ax = plt.subplots(figsize=(10, 6))
        levels = analysis_results['level_distribution'].keys()
        counts = analysis_results['level_distribution'].values()
        
        colors = {
            'DEBUG': '#808080',
            'INFO': '#4CAF50',
            'WARNING': '#FFC107',
            'ERROR': '#F44336',
            'CRITICAL': '#9C27B0'
        }
        
        bar_colors = [colors.get(level, '#2196F3') for level in levels]
        
        ax.bar(levels, counts, color=bar_colors)
        ax.set_title('Log Distribution by Severity Level')
        ax.set_xlabel('Log Level')
        ax.set_ylabel('Count')
        
        for i, count in enumerate(counts):
            ax.text(i, count + 0.1, str(count), ha='center')
        
        fig.tight_layout()
        filename = f"level_distribution_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)
        fig.savefig(filepath)
        plt.close(fig)
        
        visualization_paths.append(filepath)
    
    # 2. Component activity chart
    if 'component_distribution' in analysis_results:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        components = list(analysis_results['component_distribution'].keys())
        counts = list(analysis_results['component_distribution'].values())
        
        # Sort by count (descending)
        sorted_data = sorted(zip(components, counts), key=lambda x: x[1], reverse=True)
        components = [item[0] for item in sorted_data]
        counts = [item[1] for item in sorted_data]
        
        # Limit to top 10 components
        if len(components) > 10:
            components = components[:10]
            counts = counts[:10]
        
        ax.barh(components, counts, color='#2196F3')
        ax.set_title('Log Distribution by Component')
        ax.set_xlabel('Count')
        ax.set_ylabel('Component')
        
        for i, count in enumerate(counts):
            ax.text(count + 0.1, i, str(count), va='center')
        
        fig.tight_layout()
        filename = f"component_distribution_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)
        fig.savefig(filepath)
        plt.close(fig)
        
        visualization_paths.append(filepath)
    
    # 3. Error frequency chart
    if 'error_patterns' in analysis_results and analysis_results['error_patterns']:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        patterns = [f"Pattern {i+1}" for i in range(min(10, len(analysis_results['error_patterns'])))]
        counts = [item['count'] for item in analysis_results['error_patterns'][:10]]
        
        ax.bar(patterns, counts, color='#F44336')
        ax.set_title('Top Error Patterns')
        ax.set_xlabel('Error Pattern')
        ax.set_ylabel('Frequency')
        
        for i, count in enumerate(counts):
            ax.text(i, count + 0.1, str(count), ha='center')
        
        # Add a legend mapping pattern numbers to actual patterns
        legend_text = "\n".join([
            f"Pattern {i+1}: {item['pattern']}"
            for i, item in enumerate(analysis_results['error_patterns'][:10])
        ])
        
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.95, legend_text, transform=ax.transAxes, fontsize=8,
                verticalalignment='top', bbox=props)
        
        fig.tight_layout()
        filename = f"error_patterns_{timestamp}.png"
        filepath = os.path.join(output_dir, filename)
        fig.savefig(filepath)
        plt.close(fig)
        
        visualization_paths.append(filepath)
    
    # 4. Performance metrics chart
    if 'performance_analysis' in analysis_results and 'slowest_operations' in analysis_results['performance_analysis']:
        slowest_ops = analysis_results['performance_analysis']['slowest_operations']
        
        if slowest_ops:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Limit to top 10
            slowest_ops = slowest_ops[:min(10, len(slowest_ops))]
            
            operations = [f"{op['component']}\n{op['operation'][:20]}" for op in slowest_ops]
            avg_times = [op['avg_time'] for op in slowest_ops]
            
            ax.barh(operations, avg_times, color='#FF9800')
            ax.set_title('Slowest Operations (Average Execution Time)')
            ax.set_xlabel('Time (seconds)')
            ax.set_ylabel('Operation')
            
            for i, time_val in enumerate(avg_times):
                ax.text(time_val + 0.1, i, f"{time_val:.2f}s", va='center')
            
            fig.tight_layout()
            filename = f"performance_metrics_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)
            fig.savefig(filepath)
            plt.close(fig)
            
            visualization_paths.append(filepath)
    
    # 5. Log trend analysis chart
    if 'trend_analysis' in analysis_results and 'daily_counts' in analysis_results['trend_analysis']:
        daily_data = analysis_results['trend_analysis']['daily_counts']
        
        if daily_data:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Convert to DataFrame for easier plotting
            try:
                df = pd.DataFrame(daily_data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Plot log levels over time
                for level in ['ERROR', 'WARNING', 'INFO', 'DEBUG']:
                    if level in df.columns:
                        df[level].plot(ax=ax, marker='o', label=level)
                
                ax.set_title('Log Volume Trends by Severity Level')
                ax.set_xlabel('Date')
                ax.set_ylabel('Log Count')
                ax.legend()
                ax.grid(True)
                
                fig.tight_layout()
                filename = f"log_trends_{timestamp}.png"
                filepath = os.path.join(output_dir, filename)
                fig.savefig(filepath)
                plt.close(fig)
                
                visualization_paths.append(filepath)
            except Exception as e:
                logger.error(f"Error generating trend chart: {e}")
    
    return visualization_paths

def generate_log_report(analysis_results, output_format, output_dir, visualization_paths=None):
    """
    Generate a comprehensive log analysis report
    
    Args:
        analysis_results: Dictionary with analysis results
        output_format: Format of the report (json, csv, html, markdown)
        output_dir: Directory to save the report
        visualization_paths: List of paths to visualization files
        
    Returns:
        Path to the generated report file
    """
    if not analysis_results:
        return None
    
    # Ensure output directory exists
    ensure_dir_exists(output_dir)
    
    # Create report filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"log_analysis_{timestamp}.{output_format}"
    filepath = os.path.join(output_dir, filename)
    
    if output_format == 'json':
        # JSON format
        with open(filepath, 'w') as f:
            json.dump(analysis_results, f, indent=2)
    
    elif output_format == 'csv':
        # CSV format - flatten the nested structure
        flattened_data = []
        
        # Add general info
        flattened_data.append({
            'metric': 'log_count',
            'value': analysis_results.get('log_count', 0)
        })
        
        # Add level distribution
        for level, count in analysis_results.get('level_distribution', {}).items():
            flattened_data.append({
                'metric': f'level_{level}',
                'value': count
            })
        
        # Add component distribution
        for component, count in analysis_results.get('component_distribution', {}).items():
            flattened_data.append({
                'metric': f'component_{component}',
                'value': count
            })
        
        # Add error patterns
        for i, pattern in enumerate(analysis_results.get('error_patterns', [])):
            flattened_data.append({
                'metric': f'error_pattern_{i+1}',
                'value': pattern['count'],
                'description': pattern['pattern']
            })
        
        # Convert to DataFrame and save as CSV
        df = pd.DataFrame(flattened_data)
        df.to_csv(filepath, index=False)
    
    elif output_format == 'html':
        # HTML format
        html_content = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '  <title>Log Analysis Report</title>',
            '  <style>',
            '    body { font-family: Arial, sans-serif; margin: 20px; }',
            '    h1 { color: #2196F3; }',
            '    h2 { color: #607D8B; border-bottom: 1px solid #ddd; padding-bottom: 5px; }',
            '    table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }',
            '    th, td { text-align: left; padding: 8px; }',
            '    th { background-color: #f2f2f2; }',
            '    tr:nth-child(even) { background-color: #f9f9f9; }',
            '    .error { color: #F44336; }',
            '    .warning { color: #FF9800; }',
            '    .info { color: #2196F3; }',
            '    .image-container { margin: 20px 0; text-align: center; }',
            '    img { max-width: 100%; height: auto; border: 1px solid #ddd; }',
            '  </style>',
            '</head>',
            '<body>',
            f'  <h1>Log Analysis Report</h1>',
            f'  <p>Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>',
            f'  <p>Total logs analyzed: {analysis_results.get("log_count", 0)}</p>',
            f'  <p>Date range: {analysis_results.get("date_range", {}).get("start", "N/A")} to {analysis_results.get("date_range", {}).get("end", "N/A")}</p>'
        ]
        
        # Add visualizations if available
        if visualization_paths:
            html_content.append('  <h2>Visualizations</h2>')
            for path in visualization_paths:
                img_name = os.path.basename(path)
                # Use relative path for image src
                img_relative_path = os.path.relpath(path, output_dir)
                html_content.append('  <div class="image-container">')
                html_content.append(f'    <img src="{img_relative_path}" alt="{img_name}" />')
                html_content.append('  </div>')
        
        # Add level distribution
        if 'level_distribution' in analysis_results:
            html_content.append('  <h2>Log Level Distribution</h2>')
            html_content.append('  <table>')
            html_content.append('    <tr><th>Level</th><th>Count</th><th>Percentage</th></tr>')
            
            total = analysis_results.get('log_count', 0)
            for level, count in analysis_results['level_distribution'].items():
                percentage = (count / total * 100) if total > 0 else 0
                
                level_class = level.lower() if level.lower() in ['error', 'warning', 'info'] else ''
                html_content.append(f'    <tr><td class="{level_class}">{level}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>')
            
            html_content.append('  </table>')
        
        # Add component distribution
        if 'component_distribution' in analysis_results:
            html_content.append('  <h2>Component Distribution</h2>')
            html_content.append('  <table>')
            html_content.append('    <tr><th>Component</th><th>Count</th><th>Percentage</th></tr>')
            
            total = analysis_results.get('log_count', 0)
            
            # Sort by count (descending)
            sorted_components = sorted(
                analysis_results['component_distribution'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for component, count in sorted_components:
                percentage = (count / total * 100) if total > 0 else 0
                html_content.append(f'    <tr><td>{component}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>')
            
            html_content.append('  </table>')
        
        # Add error patterns
        if 'error_patterns' in analysis_results and analysis_results['error_patterns']:
            html_content.append('  <h2>Error Patterns</h2>')
            html_content.append('  <table>')
            html_content.append('    <tr><th>Pattern</th><th>Count</th><th>Components</th><th>Example</th></tr>')
            
            for pattern in analysis_results['error_patterns']:
                components = ', '.join(pattern['components']) if pattern['components'] else 'N/A'
                example = pattern['examples'][0] if pattern['examples'] else 'N/A'
                
                html_content.append(f'    <tr>')
                html_content.append(f'      <td>{pattern["pattern"]}</td>')
                html_content.append(f'      <td>{pattern["count"]}</td>')
                html_content.append(f'      <td>{components}</td>')
                html_content.append(f'      <td>{example}</td>')
                html_content.append(f'    </tr>')
            
            html_content.append('  </table>')
        
        # Add performance analysis
        if 'performance_analysis' in analysis_results:
            perf = analysis_results['performance_analysis']
            
            html_content.append('  <h2>Performance Analysis</h2>')
            
            # Slowest operations
            if 'slowest_operations' in perf and perf['slowest_operations']:
                html_content.append('  <h3>Slowest Operations</h3>')
                html_content.append('  <table>')
                html_content.append('    <tr><th>Component</th><th>Operation</th><th>Avg Time (s)</th><th>Max Time (s)</th><th>Count</th></tr>')
                
                for op in perf['slowest_operations'][:10]:  # Top 10
                    html_content.append(f'    <tr>')
                    html_content.append(f'      <td>{op["component"]}</td>')
                    html_content.append(f'      <td>{op["operation"]}</td>')
                    html_content.append(f'      <td>{op["avg_time"]:.2f}</td>')
                    html_content.append(f'      <td>{op["max_time"]:.2f}</td>')
                    html_content.append(f'      <td>{op["count"]}</td>')
                    html_content.append(f'    </tr>')
                
                html_content.append('  </table>')
            
            # Operations exceeding thresholds
            if 'operations_exceeding_threshold' in perf and perf['operations_exceeding_threshold']:
                html_content.append('  <h3>Operations Exceeding Performance Thresholds</h3>')
                html_content.append('  <table>')
                html_content.append('    <tr><th>Component</th><th>Operation</th><th>Avg Time (s)</th><th>Threshold (s)</th><th>Excess (%)</th></tr>')
                
                for op in perf['operations_exceeding_threshold']:
                    html_content.append(f'    <tr>')
                    html_content.append(f'      <td>{op["component"]}</td>')
                    html_content.append(f'      <td>{op["operation"]}</td>')
                    html_content.append(f'      <td>{op["avg_time"]:.2f}</td>')
                    html_content.append(f'      <td>{op["threshold"]:.2f}</td>')
                    html_content.append(f'      <td>{op["excess_pct"]:.1f}%</td>')
                    html_content.append(f'    </tr>')
                
                html_content.append('  </table>')
        
        # Add trend analysis
        if 'trend_analysis' in analysis_results:
            trends = analysis_results['trend_analysis']
            
            if 'significant_changes' in trends and trends['significant_changes']:
                html_content.append('  <h2>Significant Changes in Log Volume</h2>')
                html_content.append('  <table>')
                html_content.append('    <tr><th>Date</th><th>Level</th><th>Previous</th><th>Current</th><th>Change</th></tr>')
                
                for change in trends['significant_changes']:
                    direction = 'increase' if change['change_pct'] > 0 else 'decrease'
                    level_class = change['level'].lower() if change['level'].lower() in ['error', 'warning', 'info'] else ''
                    
                    html_content.append(f'    <tr>')
                    html_content.append(f'      <td>{change["date"]}</td>')
                    html_content.append(f'      <td class="{level_class}">{change["level"]}</td>')
                    html_content.append(f'      <td>{change["previous"]}</td>')
                    html_content.append(f'      <td>{change["current"]}</td>')
                    html_content.append(f'      <td>{change["change_pct"]}% {direction}</td>')
                    html_content.append(f'    </tr>')
                
                html_content.append('  </table>')
        
        # Close HTML
        html_content.extend([
            '</body>',
            '</html>'
        ])
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(html_content))
    
    elif output_format == 'markdown':
        # Markdown format
        md_content = [
            '# Log Analysis Report',
            '',
            f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'Total logs analyzed: {analysis_results.get("log_count", 0)}',
            f'Date range: {analysis_results.get("date_range", {}).get("start", "N/A")} to {analysis_results.get("date_range", {}).get("end", "N/A")}',
            ''
        ]
        
        # Add visualizations if available
        if visualization_paths:
            md_content.append('## Visualizations')
            md_content.append('')
            
            for path in visualization_paths:
                img_name = os.path.basename(path)
                # Use relative path for image reference
                img_relative_path = os.path.relpath(path, output_dir)
                md_content.append(f'![{img_name}]({img_relative_path})')
                md_content.append('')
        
        # Add level distribution
        if 'level_distribution' in analysis_results:
            md_content.append('## Log Level Distribution')
            md_content.append('')
            md_content.append('| Level | Count | Percentage |')
            md_content.append('| --- | --- | --- |')
            
            total = analysis_results.get('log_count', 0)
            for level, count in analysis_results['level_distribution'].items():
                percentage = (count / total * 100) if total > 0 else 0
                md_content.append(f'| {level} | {count} | {percentage:.1f}% |')
            
            md_content.append('')
        
        # Add component distribution
        if 'component_distribution' in analysis_results:
            md_content.append('## Component Distribution')
            md_content.append('')
            md_content.append('| Component | Count | Percentage |')
            md_content.append('| --- | --- | --- |')
            
            total = analysis_results.get('log_count', 0)
            
            # Sort by count (descending)
            sorted_components = sorted(
                analysis_results['component_distribution'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for component, count in sorted_components:
                percentage = (count / total * 100) if total > 0 else 0
                md_content.append(f'| {component} | {count} | {percentage:.1f}% |')
            
            md_content.append('')
        
        # Add error patterns
        if 'error_patterns' in analysis_results and analysis_results['error_patterns']:
            md_content.append('## Error Patterns')
            md_content.append('')
            md_content.append('| Pattern | Count | Components | Example |')
            md_content.append('| --- | --- | --- | --- |')
            
            for pattern in analysis_results['error_patterns']:
                components = ', '.join(pattern['components']) if pattern['components'] else 'N/A'
                example = pattern['examples'][0] if pattern['examples'] else 'N/A'
                # Escape pipe characters in markdown table
                pattern_str = pattern["pattern"].replace('|', '\\|')
                example = example.replace('|', '\\|')
                
                md_content.append(f'| {pattern_str} | {pattern["count"]} | {components} | {example} |')
            
            md_content.append('')
        
        # Add performance analysis
        if 'performance_analysis' in analysis_results:
            perf = analysis_results['performance_analysis']
            
            md_content.append('## Performance Analysis')
            md_content.append('')
            
            # Slowest operations
            if 'slowest_operations' in perf and perf['slowest_operations']:
                md_content.append('### Slowest Operations')
                md_content.append('')
                md_content.append('| Component | Operation | Avg Time (s) | Max Time (s) | Count |')
                md_content.append('| --- | --- | --- | --- | --- |')
                
                for op in perf['slowest_operations'][:10]:  # Top 10
                    # Escape pipe characters in markdown table
                    component = op["component"].replace('|', '\\|')
                    operation = op["operation"].replace('|', '\\|')
                    
                    md_content.append(f'| {component} | {operation} | {op["avg_time"]:.2f} | {op["max_time"]:.2f} | {op["count"]} |')
                
                md_content.append('')
            
            # Operations exceeding thresholds
            if 'operations_exceeding_threshold' in perf and perf['operations_exceeding_threshold']:
                md_content.append('### Operations Exceeding Performance Thresholds')
                md_content.append('')
                md_content.append('| Component | Operation | Avg Time (s) | Threshold (s) | Excess (%) |')
                md_content.append('| --- | --- | --- | --- | --- |')
                
                for op in perf['operations_exceeding_threshold']:
                    # Escape pipe characters in markdown table
                    component = op["component"].replace('|', '\\|')
                    operation = op["operation"].replace('|', '\\|')
                    
                    md_content.append(f'| {component} | {operation} | {op["avg_time"]:.2f} | {op["threshold"]:.2f} | {op["excess_pct"]:.1f}% |')
                
                md_content.append('')
        
        # Add trend analysis
        if 'trend_analysis' in analysis_results:
            trends = analysis_results['trend_analysis']
            
            if 'significant_changes' in trends and trends['significant_changes']:
                md_content.append('## Significant Changes in Log Volume')
                md_content.append('')
                md_content.append('| Date | Level | Previous | Current | Change |')
                md_content.append('| --- | --- | --- | --- | --- |')
                
                for change in trends['significant_changes']:
                    direction = 'increase' if change['change_pct'] > 0 else 'decrease'
                    md_content.append(f'| {change["date"]} | {change["level"]} | {change["previous"]} | {change["current"]} | {change["change_pct"]}% {direction} |')
                
                md_content.append('')
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(md_content))
    
    logger.info(f"Generated {output_format} report at {filepath}")
    return filepath

def main():
    """
    Main function that orchestrates log analysis
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Log script start
        logger.info(f"Starting log analysis for {args.log_file}")
        
        # Create log analyzer
        analyzer = LogAnalyzer(args.log_file)
        
        # Load logs
        logs = analyzer.load_logs()
        if not logs:
            logger.error(f"No logs found in {args.log_file}")
            return 1
        
        logger.info(f"Loaded {len(logs)} log entries")
        
        # Apply filters
        filtered_logs = analyzer.filter_logs(
            days=args.days,
            level=args.level,
            component=args.component,
            pattern=args.pattern
        )
        
        logger.info(f"After filtering: {len(filtered_logs)} log entries")
        
        if not filtered_logs:
            logger.warning("No logs remain after filtering")
            return 1
        
        # Perform analysis
        analysis_results = analyzer.analyze()
        
        # Generate visualizations if requested
        visualization_paths = []
        if args.visualize:
            logger.info("Generating visualizations")
            visualization_paths = generate_log_visualizations(analysis_results, args.output_dir)
            
            if visualization_paths:
                logger.info(f"Generated {len(visualization_paths)} visualizations")
            else:
                logger.warning("No visualizations were generated")
        
        # Generate report
        logger.info(f"Generating {args.format} report")
        report_path = generate_log_report(
            analysis_results,
            args.format,
            args.output_dir,
            visualization_paths
        )
        
        if report_path:
            logger.info(f"Report generated at {report_path}")
        else:
            logger.error("Failed to generate report")
            return 1
        
        # Display summary if verbose
        if args.verbose:
            summary = analyzer.get_summary()
            print("\n" + summary)
        
        logger.info("Log analysis completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Error during log analysis: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())