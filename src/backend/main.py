"""
main.py - Main entry point for the Budget Management Application.

Orchestrates the weekly budget management workflow by sequentially executing the component pipeline:
transaction retrieval, categorization, budget analysis, insight generation, report distribution, and savings automation.
Implements error handling, logging, and health checks for the entire process.
"""

import os  # standard library
import sys  # standard library
import time  # standard library
import argparse  # standard library
import traceback  # standard library
import uuid  # standard library
from typing import Dict, List, Optional, Any  # standard library

# Internal imports from other modules in the application
from components.transaction_retriever import TransactionRetriever  # Import the TransactionRetriever class
from components.transaction_categorizer import TransactionCategorizer  # Import the TransactionCategorizer class
from components.budget_analyzer import BudgetAnalyzer  # Import the BudgetAnalyzer class
from components.insight_generator import InsightGenerator  # Import the InsightGenerator class
from components.report_distributor import ReportDistributor  # Import the ReportDistributor class
from components.savings_automator import SavingsAutomator  # Import the SavingsAutomator class
from config.settings import APP_SETTINGS, initialize_settings  # Import application settings and initialization function
from services.logging_service import initialize_logging, get_component_logger, LoggingContext, PerformanceLogger  # Import logging utilities

# Initialize logger for this module
logger = get_component_logger('main')

# Define the order in which components should be executed
COMPONENTS: List[Any] = [TransactionRetriever, TransactionCategorizer, BudgetAnalyzer, InsightGenerator, ReportDistributor, SavingsAutomator]


def setup_application() -> bool:
    """
    Initializes the application settings and logging.

    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        # Initialize application settings
        if not initialize_settings():
            logger.error("Failed to initialize application settings")
            return False

        # Initialize logging system
        if not initialize_logging():
            logger.error("Failed to initialize logging system")
            return False

        logger.info("Application started")
        return True

    except Exception as e:
        logger.error(f"Application initialization failed: {str(e)}")
        return False


def check_system_health() -> Dict:
    """
    Checks the health of all system components and their integrations.

    Returns:
        Dict: Health status of all components and integrations
    """
    health_status: Dict[str, Any] = {}

    # Instantiate each component
    for ComponentClass in COMPONENTS:
        try:
            component = ComponentClass()
            health_status[ComponentClass.__name__] = component.check_health()
        except Exception as e:
            logger.error(f"Failed to instantiate {ComponentClass.__name__}: {str(e)}")
            health_status[ComponentClass.__name__] = {'status': 'error', 'message': str(e)}

    # Log overall system health status
    logger.info(f"System health check completed: {health_status}")
    return health_status


def run_budget_management_process(correlation_id: Optional[str] = None) -> Dict:
    """
    Executes the complete budget management workflow.

    Args:
        correlation_id: Unique identifier for this execution

    Returns:
        Dict: Final execution status with results from all components
    """
    # Generate a new correlation_id if not provided
    correlation_id = correlation_id or str(uuid.uuid4())

    # Create a PerformanceLogger to track overall execution time
    perf_logger = PerformanceLogger(logger, "run_budget_management_process")

    # Start the performance timer
    perf_logger.start()

    # Initialize status dictionary with correlation_id
    status: Dict[str, Any] = {'correlation_id': correlation_id}

    # Create component instances in the correct execution order
    transaction_retriever = TransactionRetriever()
    transaction_categorizer = TransactionCategorizer()
    budget_analyzer = BudgetAnalyzer()
    insight_generator = InsightGenerator()
    report_distributor = ReportDistributor()
    savings_automator = SavingsAutomator()

    # Execute TransactionRetriever and update status with results
    with LoggingContext(logger, "TransactionRetriever.execute", {'correlation_id': correlation_id}) as log_ctx:
        retriever_status = transaction_retriever.execute()
        status['retriever'] = retriever_status
        log_ctx.update_context(retriever_status)

        # If TransactionRetriever fails, log error and return failure status
        if retriever_status.get('status') == 'error':
            logger.error("TransactionRetriever failed", extra={'correlation_id': correlation_id, 'status': retriever_status})
            perf_logger.stop()
            return status

    # Execute TransactionCategorizer with previous status and update status
    with LoggingContext(logger, "TransactionCategorizer.execute", {'correlation_id': correlation_id}) as log_ctx:
        categorizer_status = transaction_categorizer.execute(retriever_status)
        status['categorizer'] = categorizer_status
        log_ctx.update_context(categorizer_status)

        # If TransactionCategorizer fails, log error and return failure status
        if categorizer_status.get('status') == 'error':
            logger.error("TransactionCategorizer failed", extra={'correlation_id': correlation_id, 'status': categorizer_status})
            perf_logger.stop()
            return status

    # Execute BudgetAnalyzer with previous status and update status
    with LoggingContext(logger, "BudgetAnalyzer.execute", {'correlation_id': correlation_id}) as log_ctx:
        analyzer_status = budget_analyzer.execute(categorizer_status)
        status['analyzer'] = analyzer_status
        log_ctx.update_context(analyzer_status)

        # If BudgetAnalyzer fails, log error and return failure status
        if analyzer_status.get('status') == 'error':
            logger.error("BudgetAnalyzer failed", extra={'correlation_id': correlation_id, 'status': analyzer_status})
            perf_logger.stop()
            return status

    # Execute InsightGenerator with previous status and update status
    with LoggingContext(logger, "InsightGenerator.execute", {'correlation_id': correlation_id}) as log_ctx:
        insight_status = insight_generator.execute(analyzer_status)
        status['insight'] = insight_status
        log_ctx.update_context(insight_status)

        # If InsightGenerator fails, log error and return failure status
        if insight_status.get('status') == 'error':
            logger.error("InsightGenerator failed", extra={'correlation_id': correlation_id, 'status': insight_status})
            perf_logger.stop()
            return status

    # Execute ReportDistributor with previous status and update status
    with LoggingContext(logger, "ReportDistributor.execute", {'correlation_id': correlation_id}) as log_ctx:
        report_status = report_distributor.execute(insight_status)
        status['report'] = report_status
        log_ctx.update_context(report_status)

        # If ReportDistributor fails, log warning but continue (non-critical)
        if report_status.get('status') == 'error':
            logger.warning("ReportDistributor failed", extra={'correlation_id': correlation_id, 'status': report_status})

    # Execute SavingsAutomator with previous status and update status
    with LoggingContext(logger, "SavingsAutomator.execute", {'correlation_id': correlation_id}) as log_ctx:
        savings_status = savings_automator.execute(analyzer_status)
        status['savings'] = savings_status
        log_ctx.update_context(savings_status)

        # If SavingsAutomator fails, log warning but continue (non-critical)
        if savings_status.get('status') == 'error':
            logger.warning("SavingsAutomator failed", extra={'correlation_id': correlation_id, 'status': savings_status})

    # Stop the performance timer and log total execution time
    total_time = perf_logger.stop()
    logger.info(f"Budget management process completed in {total_time:.2f} seconds", extra={'correlation_id': correlation_id})

    # Return final status dictionary with results from all components
    return status


def parse_arguments() -> argparse.Namespace:
    """
    Parses command line arguments for manual execution.

    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(description="Run the Budget Management Application")
    parser.add_argument('--check-health', action='store_true', help='Run system health check')
    parser.add_argument('--correlation-id', type=str, help='Provide a custom correlation ID')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for the application.

    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse command line arguments
        args = parse_arguments()

        # Initialize application
        if not setup_application():
            logger.error("Application setup failed")
            return 1

        # If --check-health argument is provided, run system health check
        if args.check_health:
            health_status = check_system_health()
            logger.info(f"System health check results: {health_status}")

            # Exit with code 0 if all components are healthy, 1 otherwise
            if all(status.get('status') == 'healthy' for status in health_status.values() if isinstance(status, dict)):
                return 0
            else:
                return 1

        # If normal execution, run run_budget_management_process() with correlation_id
        results = run_budget_management_process(args.correlation_id)
        logger.info(f"Execution results: {results}")

        # Return exit code 0 if successful, 1 if failed
        if results.get('status') == 'error':
            return 1
        else:
            return 0

    except Exception as e:
        logger.critical(f"Unhandled exception in main: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())