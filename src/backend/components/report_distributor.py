"""
report_distributor.py - Component responsible for sending budget reports via email

This module implements the ReportDistributor component which handles sending
AI-generated budget insights and visualizations to specified recipients using the
Gmail API, with support for retry logic, verification, and robust error handling.
"""

import time  # standard library
from typing import Dict, List, Optional  # standard library
import googleapiclient.errors  # google-api-python-client 2.100.0+

from ..api_clients.gmail_client import GmailClient
from ..models.report import Report
from ..config.settings import APP_SETTINGS
from ..services.authentication_service import AuthenticationService
from ..services.logging_service import get_component_logger
from ..services.error_handling_service import ErrorHandlingContext
from ..utils.error_handlers import retry_with_backoff, APIError, ValidationError

# Set up logger
logger = get_component_logger('report_distributor')


class ReportDistributor:
    """Component responsible for sending budget reports via email"""
    
    def __init__(
        self,
        gmail_client: Optional[GmailClient] = None,
        auth_service: Optional[AuthenticationService] = None,
        recipients: Optional[List[str]] = None,
        sender_email: Optional[str] = None
    ):
        """
        Initialize the ReportDistributor component
        
        Args:
            gmail_client: Optional GmailClient instance (created if not provided)
            auth_service: Optional AuthenticationService instance (created if not provided)
            recipients: Optional list of email recipients (defaults to APP_SETTINGS)
            sender_email: Optional sender email address (defaults to APP_SETTINGS)
        """
        # Initialize auth_service with provided service or create new instance
        self.auth_service = auth_service or AuthenticationService()
        
        # Initialize gmail_client with provided client or create new instance
        self.gmail_client = gmail_client or GmailClient(self.auth_service)
        
        # Set recipients to provided list or default from settings
        self.recipients = recipients or APP_SETTINGS.get('EMAIL_RECIPIENTS', [])
        
        # Set sender_email to provided value or default from settings
        self.sender_email = sender_email or APP_SETTINGS.get('EMAIL_SENDER', '')
        
        # Initialize correlation_id to None (will be set during execute)
        self.correlation_id = None
        
        logger.info(
            "ReportDistributor initialized",
            context={
                "recipients": self.recipients,
                "sender": self.sender_email
            }
        )
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API
        
        Returns:
            True if authentication successful, False otherwise
        """
        logger.info("Starting Gmail API authentication")
        try:
            # Authenticate with Gmail API using gmail_client
            result = self.gmail_client.authenticate()
            
            if result:
                logger.info("Gmail API authentication successful")
            else:
                logger.error("Gmail API authentication failed")
                
            return result
            
        except Exception as e:
            logger.error(
                f"Gmail API authentication error: {str(e)}",
                context={"error": str(e)}
            )
            return False
    
    def validate_report(self, report: Report) -> bool:
        """
        Validate that the report is complete and ready to send
        
        Args:
            report: Report to validate
            
        Returns:
            True if report is valid, False otherwise
            
        Raises:
            ValidationError: If report is invalid
        """
        # Check if report is an instance of Report class
        if not isinstance(report, Report):
            logger.error("Invalid report object: Not a Report instance")
            raise ValidationError("Invalid report object", "report")
        
        # Check if report is complete (has insights and charts)
        if not report.is_complete():
            logger.error("Report is incomplete - missing insights or charts")
            raise ValidationError("Report is incomplete", "report")
        
        logger.debug("Report validation successful")
        return True
    
    @retry_with_backoff(exceptions=(APIError, googleapiclient.errors.HttpError), max_retries=3)
    def send_report(self, report: Report) -> Dict:
        """
        Send the report via email
        
        Args:
            report: Report to send
            
        Returns:
            Email delivery status
            
        Raises:
            ValidationError: If report is invalid
            APIError: If email sending fails
        """
        try:
            # Validate the report is complete and ready to send
            self.validate_report(report)
            
            # Get email content (subject and body)
            subject, body = report.get_email_content()
            
            # Send email using gmail_client with subject, body, and chart files
            send_result = self.gmail_client.send_email(
                subject=subject,
                html_content=body,
                recipients=self.recipients,
                attachment_paths=report.chart_files
            )
            
            logger.info(
                f"Email sent successfully with subject: '{subject}'",
                context={
                    "message_id": send_result.get('message_id', ''),
                    "recipients": self.recipients
                }
            )
            
            return send_result
            
        except ValidationError:
            # Re-raise validation errors
            raise
            
        except (googleapiclient.errors.HttpError, Exception) as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(
                error_msg,
                context={"error": str(e), "recipients": self.recipients}
            )
            raise APIError(
                error_msg,
                "Gmail API",
                "send_email"
            )
    
    @retry_with_backoff(exceptions=(APIError, googleapiclient.errors.HttpError), max_retries=2)
    def verify_delivery(self, message_id: str) -> Dict:
        """
        Verify that the email was delivered successfully
        
        Args:
            message_id: Message ID of the sent email
            
        Returns:
            Delivery verification status
            
        Raises:
            APIError: If verification fails
        """
        try:
            # Verify delivery using gmail_client
            verification_result = self.gmail_client.verify_delivery(message_id)
            
            # Log verification result
            delivery_status = verification_result.get('status', 'unknown')
            logger.info(
                f"Email delivery verification: {delivery_status}",
                context=verification_result
            )
            
            return verification_result
            
        except (googleapiclient.errors.HttpError, Exception) as e:
            error_msg = f"Failed to verify email delivery: {str(e)}"
            logger.error(
                error_msg,
                context={"error": str(e), "message_id": message_id}
            )
            raise APIError(
                error_msg,
                "Gmail API",
                "verify_delivery"
            )
    
    def execute(self, previous_status: Dict) -> Dict:
        """
        Execute the report distribution process
        
        Args:
            previous_status: Status information from previous component
            
        Returns:
            Execution status and email delivery status
        """
        start_time = time.time()
        
        # Extract correlation_id from previous_status if available
        self.correlation_id = previous_status.get('correlation_id')
        
        logger.info(
            "Starting report distribution",
            context={"correlation_id": self.correlation_id}
        )
        
        # Extract report from previous_status
        report = previous_status.get('report')
        
        try:
            # Use ErrorHandlingContext for standardized error handling
            with ErrorHandlingContext('report_distributor', 'execute', {'correlation_id': self.correlation_id}):
                # First, authenticate with Gmail API
                if not self.authenticate():
                    return {
                        'status': 'error',
                        'message': 'Failed to authenticate with Gmail API',
                        'correlation_id': self.correlation_id
                    }
                
                # Send the report via email
                send_result = self.send_report(report)
                
                # If email sent successfully, verify delivery
                if send_result.get('status') == 'success':
                    message_id = send_result.get('message_id')
                    verification_result = self.verify_delivery(message_id)
                    
                    # Calculate execution duration
                    duration = time.time() - start_time
                    
                    return {
                        'status': 'success',
                        'message': 'Report distributed successfully',
                        'delivery_status': verification_result.get('status', 'unknown'),
                        'message_id': message_id,
                        'email_subject': report.email_subject,
                        'recipients': self.recipients,
                        'execution_time': duration,
                        'correlation_id': self.correlation_id
                    }
                else:
                    # Return error if sending failed
                    return {
                        'status': 'error',
                        'message': 'Failed to send email',
                        'correlation_id': self.correlation_id
                    }
                    
        except Exception as e:
            # Log the exception
            logger.error(
                f"Error during report distribution: {str(e)}",
                context={"error": str(e), "correlation_id": self.correlation_id}
            )
            
            # Return error status
            return {
                'status': 'error',
                'message': f'Report distribution error: {str(e)}',
                'error': str(e),
                'correlation_id': self.correlation_id
            }
        finally:
            # Log completion regardless of success/failure
            end_time = time.time()
            logger.info(
                f"Report distribution completed in {end_time - start_time:.2f}s",
                context={"execution_time": end_time - start_time}
            )
    
    def check_health(self) -> Dict:
        """
        Check health of Gmail API connection
        
        Returns:
            Health status of Gmail integration
        """
        health_status = {
            'service': 'Gmail API',
            'status': 'unknown'
        }
        
        try:
            # Check Gmail API connectivity by attempting authentication
            auth_success = self.authenticate()
            
            if auth_success:
                health_status['status'] = 'healthy'
            else:
                health_status['status'] = 'unhealthy'
                health_status['reason'] = 'Authentication failed'
                
            logger.info(
                f"Gmail API health check: {health_status['status']}",
                context=health_status
            )
            
            return health_status
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['reason'] = str(e)
            
            logger.error(
                f"Gmail API health check failed: {str(e)}",
                context=health_status
            )
            
            return health_status