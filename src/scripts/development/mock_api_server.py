"""
mock_api_server.py - Development utility that provides mock implementations of external APIs
used by the Budget Management Application.

This server simulates Capital One, Google Sheets, Gemini, and Gmail APIs to enable local
testing and development without requiring actual API credentials or making real API calls.

Usage:
    python mock_api_server.py [--port PORT] [--host HOST] [--debug]
    
    Or import and use programmatically:
    from scripts.development.mock_api_server import run_server, stop_server
    server_thread = run_server()
    # ... use the mock server ...
    stop_server()
"""

import os
import json
import logging
import re
import threading
import datetime
import decimal
import argparse
from decimal import Decimal

from flask import Flask, request, jsonify, Blueprint

from ..config.script_settings import DEVELOPMENT_SETTINGS
from ..config.logging_setup import get_script_logger
from ..config.path_constants import TEST_FIXTURES_DIR
from ...test.utils.fixture_loader import load_fixture

# Set up logger
logger = get_script_logger('mock_api_server')

# Initialize Flask app
app = Flask(__name__)

# Create blueprints for each API
capital_one_bp = Blueprint('capital_one', __name__, url_prefix='/capital-one')
google_sheets_bp = Blueprint('google_sheets', __name__, url_prefix='/sheets')
gemini_bp = Blueprint('gemini', __name__, url_prefix='/gemini')
gmail_bp = Blueprint('gmail', __name__, url_prefix='/gmail')

# Server thread tracking
server_thread = None
is_running = False


class MockResponseHandler:
    """Handler for generating appropriate mock API responses"""
    
    def __init__(self, mock_responses):
        """
        Initialize the mock response handler with loaded responses
        
        Args:
            mock_responses: Dictionary containing mock responses for different APIs
        """
        self.mock_responses = mock_responses
        self.request_history = {}
        # Initialize counters for generating unique IDs
        self._transfer_id_counter = 1000
        self._message_id_counter = 1000
    
    def record_request(self, endpoint, request_data):
        """
        Record an incoming API request for tracking
        
        Args:
            endpoint: The API endpoint that was called
            request_data: The request data that was sent
        """
        if endpoint not in self.request_history:
            self.request_history[endpoint] = []
        
        self.request_history[endpoint].append({
            'timestamp': datetime.datetime.now().isoformat(),
            'data': request_data
        })
        
        logger.debug(f"Recorded request to {endpoint}")
    
    def get_capital_one_auth_response(self):
        """
        Generate mock response for Capital One authentication
        
        Returns:
            tuple: (response_data, status_code)
        """
        self.record_request('capital_one_auth', {
            'grant_type': request.form.get('grant_type'),
            'client_id': '[REDACTED]',  # Don't log actual client ID
        })
        
        auth_response = self.mock_responses.get('capital_one', {}).get('auth', {
            'access_token': 'mock_access_token',
            'token_type': 'Bearer',
            'expires_in': 3600,
            'refresh_token': 'mock_refresh_token'
        })
        
        return auth_response, 200
    
    def get_capital_one_transactions(self, account_id):
        """
        Generate mock response for Capital One transactions
        
        Args:
            account_id: The account ID to get transactions for
            
        Returns:
            tuple: (response_data, status_code)
        """
        self.record_request('capital_one_transactions', {
            'account_id': account_id,
            'params': dict(request.args)
        })
        
        # Get all transactions from mock data
        all_transactions = self.mock_responses.get('capital_one', {}).get('transactions', [])
        
        # Filter transactions for the requested account
        account_transactions = [
            tx for tx in all_transactions 
            if tx.get('accountId') == account_id
        ]
        
        return {'transactions': account_transactions}, 200
    
    def get_capital_one_account(self, account_id):
        """
        Generate mock response for Capital One account details
        
        Args:
            account_id: The account ID to get details for
            
        Returns:
            tuple: (response_data, status_code)
        """
        self.record_request('capital_one_account', {
            'account_id': account_id
        })
        
        accounts = self.mock_responses.get('capital_one', {}).get('accounts', [])
        for account in accounts:
            if account.get('accountId') == account_id:
                return account, 200
        
        # If account not found
        return {'error': 'Account not found'}, 404
    
    def create_capital_one_transfer(self):
        """
        Generate mock response for Capital One transfer creation
        
        Returns:
            tuple: (response_data, status_code)
        """
        transfer_request = request.json
        self.record_request('capital_one_transfer', transfer_request)
        
        # Generate a unique transfer ID
        transfer_id = f"transfer-{self._transfer_id_counter}"
        self._transfer_id_counter += 1
        
        # Create a mock transfer response
        transfer_response = {
            'transferId': transfer_id,
            'sourceAccountId': transfer_request.get('sourceAccountId'),
            'destinationAccountId': transfer_request.get('destinationAccountId'),
            'amount': transfer_request.get('amount'),
            'status': 'pending',
            'createdDate': datetime.datetime.now().isoformat()
        }
        
        return transfer_response, 201
    
    def get_capital_one_transfer_status(self, transfer_id):
        """
        Generate mock response for Capital One transfer status
        
        Args:
            transfer_id: The transfer ID to get status for
            
        Returns:
            tuple: (response_data, status_code)
        """
        self.record_request('capital_one_transfer_status', {
            'transfer_id': transfer_id
        })
        
        # Create a mock transfer status response
        transfer_status = {
            'transferId': transfer_id,
            'status': 'completed',
            'completedDate': datetime.datetime.now().isoformat()
        }
        
        return transfer_status, 200
    
    def get_sheets_spreadsheet(self, spreadsheet_id):
        """
        Generate mock response for Google Sheets spreadsheet metadata
        
        Args:
            spreadsheet_id: The spreadsheet ID to get metadata for
            
        Returns:
            tuple: (response_data, status_code)
        """
        self.record_request('sheets_spreadsheet', {
            'spreadsheet_id': spreadsheet_id
        })
        
        # Create a mock spreadsheet response
        spreadsheet_data = self.mock_responses.get('google_sheets', {}).get('spreadsheet', {
            'spreadsheetId': spreadsheet_id,
            'properties': {
                'title': 'Mock Spreadsheet'
            },
            'sheets': [
                {
                    'properties': {
                        'sheetId': 0,
                        'title': 'Weekly Spending'
                    }
                },
                {
                    'properties': {
                        'sheetId': 1,
                        'title': 'Master Budget'
                    }
                }
            ]
        })
        
        return spreadsheet_data, 200
    
    def get_sheets_values(self, spreadsheet_id, range_name):
        """
        Generate mock response for Google Sheets values
        
        Args:
            spreadsheet_id: The spreadsheet ID to get values from
            range_name: The range to get values for
            
        Returns:
            tuple: (response_data, status_code)
        """
        self.record_request('sheets_values', {
            'spreadsheet_id': spreadsheet_id,
            'range_name': range_name,
            'params': dict(request.args)
        })
        
        # Determine which data to return based on the range name
        mock_data = None
        if 'Master Budget' in range_name:
            mock_data = self.mock_responses.get('google_sheets', {}).get('budget_data', {
                'range': range_name,
                'majorDimension': 'ROWS',
                'values': [
                    ['Groceries', '150.00'],
                    ['Dining Out', '75.00'],
                    ['Entertainment', '50.00'],
                    ['Transportation', '60.00'],
                    ['Utilities', '100.00']
                ]
            })
        else:  # Weekly Spending sheet
            mock_data = self.mock_responses.get('google_sheets', {}).get('transaction_data', {
                'range': range_name,
                'majorDimension': 'ROWS',
                'values': [
                    ['Grocery Store', '45.67', '2023-07-15 10:30:00', 'Groceries'],
                    ['Restaurant ABC', '28.50', '2023-07-16 19:15:00', 'Dining Out'],
                    ['Gas Station', '35.40', '2023-07-17 08:45:00', 'Transportation'],
                    ['Coffee Shop', '5.25', '2023-07-18 07:30:00', ''],
                    ['Online Store', '19.99', '2023-07-19 14:20:00', '']
                ]
            })
        
        return mock_data, 200
    
    def append_sheets_values(self, spreadsheet_id, range_name):
        """
        Generate mock response for appending values to Google Sheets
        
        Args:
            spreadsheet_id: The spreadsheet ID to append values to
            range_name: The range to append values to
            
        Returns:
            tuple: (response_data, status_code)
        """
        append_request = request.json
        values = append_request.get('values', [])
        
        self.record_request('sheets_append', {
            'spreadsheet_id': spreadsheet_id,
            'range_name': range_name,
            'values': values
        })
        
        # Create a mock append response
        updated_range = f"{range_name}!A{len(values) + 1}:D{len(values) + len(values)}"
        append_response = {
            'spreadsheetId': spreadsheet_id,
            'updates': {
                'spreadsheetId': spreadsheet_id,
                'updatedRange': updated_range,
                'updatedRows': len(values),
                'updatedColumns': 4,
                'updatedCells': len(values) * 4
            }
        }
        
        return append_response, 200
    
    def update_sheets_values(self, spreadsheet_id, range_name):
        """
        Generate mock response for updating values in Google Sheets
        
        Args:
            spreadsheet_id: The spreadsheet ID to update values in
            range_name: The range to update values for
            
        Returns:
            tuple: (response_data, status_code)
        """
        update_request = request.json
        values = update_request.get('values', [])
        
        self.record_request('sheets_update', {
            'spreadsheet_id': spreadsheet_id,
            'range_name': range_name,
            'values': values
        })
        
        # Create a mock update response
        update_response = {
            'spreadsheetId': spreadsheet_id,
            'updatedRange': range_name,
            'updatedRows': len(values),
            'updatedColumns': len(values[0]) if values and len(values) > 0 else 0,
            'updatedCells': sum(len(row) for row in values) if values else 0
        }
        
        return update_response, 200
    
    def batch_update_sheets(self, spreadsheet_id):
        """
        Generate mock response for batch updating Google Sheets
        
        Args:
            spreadsheet_id: The spreadsheet ID to batch update
            
        Returns:
            tuple: (response_data, status_code)
        """
        batch_request = request.json
        requests = batch_request.get('requests', [])
        
        self.record_request('sheets_batch_update', {
            'spreadsheet_id': spreadsheet_id,
            'requests': requests
        })
        
        # Create a mock batch update response
        batch_response = {
            'spreadsheetId': spreadsheet_id,
            'replies': [{} for _ in requests],
            'updatedSpreadsheet': {
                'spreadsheetId': spreadsheet_id,
                'properties': {
                    'title': 'Mock Spreadsheet'
                }
            }
        }
        
        return batch_response, 200
    
    def generate_gemini_content(self, model):
        """
        Generate mock response for Gemini AI content generation
        
        Args:
            model: The model to generate content with
            
        Returns:
            tuple: (response_data, status_code)
        """
        content_request = request.json
        prompt = content_request.get('contents', [{}])[0].get('parts', [{}])[0].get('text', '')
        
        self.record_request('gemini_generate', {
            'model': model,
            'prompt': prompt,
        })
        
        # Determine which type of response to return based on the prompt content
        response_data = None
        if 'categoriz' in prompt.lower() or 'transaction' in prompt.lower():
            # This is a transaction categorization request
            response_data = self.mock_responses.get('gemini', {}).get('categorization', {
                'candidates': [
                    {
                        'content': {
                            'parts': [
                                {
                                    'text': 'Location: Grocery Store -> Category: Groceries\nLocation: Restaurant ABC -> Category: Dining Out\nLocation: Gas Station -> Category: Transportation\nLocation: Coffee Shop -> Category: Dining Out\nLocation: Online Store -> Category: Shopping'
                                }
                            ],
                            'role': 'model'
                        },
                        'finishReason': 'STOP',
                        'safetyRatings': []
                    }
                ],
                'promptFeedback': {
                    'safetyRatings': []
                }
            })
        else:
            # This is a budget insights request
            response_data = self.mock_responses.get('gemini', {}).get('insights', {
                'candidates': [
                    {
                        'content': {
                            'parts': [
                                {
                                    'text': '# Weekly Budget Update\n\n## Overall Status: $45.19 under budget 🎉\n\nYou\'ve done well managing your finances this week! Here\'s a breakdown of your spending:\n\n### Category Analysis\n\n**Areas where you did great:**\n- **Groceries**: Spent $45.67 of your $150.00 budget (69.6% remaining)\n- **Transportation**: Spent $35.40 of your $60.00 budget (41.0% remaining)\n\n**Areas for attention:**\n- **Dining Out**: You\'ve spent $33.75 of your $75.00 budget (55.0% remaining)\n\n**Uncategorized spending:**\n- You have $19.99 in uncategorized transactions that should be assigned to a budget category\n\n### Recommendations\n1. Continue your good habits in grocery shopping\n2. Consider categorizing your "Online Store" purchase to better track your spending\n3. Your surplus of $45.19 will be automatically transferred to savings\n\nGreat job staying under budget this week!'
                                }
                            ],
                            'role': 'model'
                        },
                        'finishReason': 'STOP',
                        'safetyRatings': []
                    }
                ],
                'promptFeedback': {
                    'safetyRatings': []
                }
            })
        
        return response_data, 200
    
    def send_gmail(self, user_id):
        """
        Generate mock response for sending an email via Gmail API
        
        Args:
            user_id: The user ID to send the email as
            
        Returns:
            tuple: (response_data, status_code)
        """
        email_request = request.json
        raw_message = email_request.get('raw', '')
        
        self.record_request('gmail_send', {
            'user_id': user_id,
            'raw_message': raw_message[:50] + '...' if raw_message else '',  # Only log a preview
        })
        
        # Generate a unique message ID
        message_id = f"message-{self._message_id_counter}"
        self._message_id_counter += 1
        
        # Create a mock email send response
        email_response = {
            'id': message_id,
            'threadId': f"thread-{message_id}",
            'labelIds': ['SENT']
        }
        
        return email_response, 200
    
    def get_gmail_message(self, user_id, message_id):
        """
        Generate mock response for retrieving a Gmail message
        
        Args:
            user_id: The user ID to get the message for
            message_id: The message ID to retrieve
            
        Returns:
            tuple: (response_data, status_code)
        """
        self.record_request('gmail_get_message', {
            'user_id': user_id,
            'message_id': message_id
        })
        
        # Create a mock message response
        message_response = {
            'id': message_id,
            'threadId': f"thread-{message_id}",
            'labelIds': ['SENT'],
            'snippet': 'Budget Update: Weekly spending analysis',
            'payload': {
                'mimeType': 'multipart/alternative',
                'headers': [
                    {
                        'name': 'Subject',
                        'value': 'Budget Update: $45.19 under budget this week'
                    },
                    {
                        'name': 'From',
                        'value': 'njdifiore@gmail.com'
                    },
                    {
                        'name': 'To',
                        'value': 'njdifiore@gmail.com, nick@blitzy.com'
                    }
                ]
            }
        }
        
        return message_response, 200


def load_mock_responses():
    """
    Load all mock API responses from fixture files
    
    Returns:
        dict: Dictionary containing all mock responses for different APIs
    """
    mock_responses = {}
    
    try:
        # Load Capital One mock responses
        mock_responses['capital_one'] = {
            'auth': load_fixture('api_responses/capital_one/auth'),
            'transactions': load_fixture('api_responses/capital_one/transactions'),
            'accounts': load_fixture('api_responses/capital_one/accounts'),
            'transfers': load_fixture('api_responses/capital_one/transfers')
        }
        
        # Load Google Sheets mock responses
        mock_responses['google_sheets'] = {
            'spreadsheet': load_fixture('api_responses/google_sheets/spreadsheet'),
            'budget_data': load_fixture('api_responses/google_sheets/budget_data'),
            'transaction_data': load_fixture('api_responses/google_sheets/transaction_data')
        }
        
        # Load Gemini mock responses
        mock_responses['gemini'] = {
            'categorization': load_fixture('api_responses/gemini/categorization'),
            'insights': load_fixture('api_responses/gemini/insights')
        }
        
        # Load Gmail mock responses
        mock_responses['gmail'] = {
            'send_confirmation': load_fixture('api_responses/gmail/send_confirmation'),
            'message': load_fixture('api_responses/gmail/message')
        }
        
        logger.info("Successfully loaded mock API responses")
    except Exception as e:
        logger.error(f"Error loading mock responses: {str(e)}")
        # Provide default mock responses if fixture loading fails
        if 'capital_one' not in mock_responses:
            mock_responses['capital_one'] = {
                'auth': {'access_token': 'mock_token', 'token_type': 'Bearer', 'expires_in': 3600},
                'transactions': [],
                'accounts': [],
                'transfers': []
            }
        if 'google_sheets' not in mock_responses:
            mock_responses['google_sheets'] = {
                'spreadsheet': {},
                'budget_data': {'values': []},
                'transaction_data': {'values': []}
            }
        if 'gemini' not in mock_responses:
            mock_responses['gemini'] = {
                'categorization': {'candidates': [{'content': {'parts': [{'text': ''}]}}]},
                'insights': {'candidates': [{'content': {'parts': [{'text': ''}]}}]}
            }
        if 'gmail' not in mock_responses:
            mock_responses['gmail'] = {
                'send_confirmation': {'id': 'mock_id'},
                'message': {'id': 'mock_id', 'labelIds': ['SENT']}
            }
    
    return mock_responses


def parse_arguments():
    """
    Parse command line arguments for the mock API server
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Run a mock API server for development and testing'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=DEVELOPMENT_SETTINGS.get('MOCK_API_PORT', 8081),
        help='Port to run the server on'
    )
    parser.add_argument(
        '--host', 
        type=str, 
        default=DEVELOPMENT_SETTINGS.get('MOCK_API_HOST', 'localhost'),
        help='Host to run the server on'
    )
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Run the server in debug mode'
    )
    
    return parser.parse_args()


def setup_capital_one_routes(mock_responses):
    """
    Set up routes for the Capital One API mock
    
    Args:
        mock_responses: Dictionary containing mock responses
    """
    handler = MockResponseHandler(mock_responses)
    
    @capital_one_bp.route('/oauth2/token', methods=['POST'])
    def oauth_token():
        response, status_code = handler.get_capital_one_auth_response()
        return jsonify(response), status_code
    
    @capital_one_bp.route('/accounts/<account_id>/transactions', methods=['GET'])
    def get_transactions(account_id):
        response, status_code = handler.get_capital_one_transactions(account_id)
        return jsonify(response), status_code
    
    @capital_one_bp.route('/accounts/<account_id>', methods=['GET'])
    def get_account(account_id):
        response, status_code = handler.get_capital_one_account(account_id)
        return jsonify(response), status_code
    
    @capital_one_bp.route('/transfers', methods=['POST'])
    def create_transfer():
        response, status_code = handler.create_capital_one_transfer()
        return jsonify(response), status_code
    
    @capital_one_bp.route('/transfers/<transfer_id>', methods=['GET'])
    def get_transfer_status(transfer_id):
        response, status_code = handler.get_capital_one_transfer_status(transfer_id)
        return jsonify(response), status_code
    
    @capital_one_bp.errorhandler(Exception)
    def handle_error(e):
        logger.error(f"Error in Capital One API mock: {str(e)}")
        return jsonify({'error': str(e)}), 500


def setup_google_sheets_routes(mock_responses):
    """
    Set up routes for the Google Sheets API mock
    
    Args:
        mock_responses: Dictionary containing mock responses
    """
    handler = MockResponseHandler(mock_responses)
    
    @google_sheets_bp.route('/v4/spreadsheets/<spreadsheet_id>', methods=['GET'])
    def get_spreadsheet(spreadsheet_id):
        response, status_code = handler.get_sheets_spreadsheet(spreadsheet_id)
        return jsonify(response), status_code
    
    @google_sheets_bp.route('/v4/spreadsheets/<spreadsheet_id>/values/<path:range_name>', methods=['GET'])
    def get_values(spreadsheet_id, range_name):
        response, status_code = handler.get_sheets_values(spreadsheet_id, range_name)
        return jsonify(response), status_code
    
    @google_sheets_bp.route('/v4/spreadsheets/<spreadsheet_id>/values/<path:range_name>:append', methods=['POST'])
    def append_values(spreadsheet_id, range_name):
        response, status_code = handler.append_sheets_values(spreadsheet_id, range_name)
        return jsonify(response), status_code
    
    @google_sheets_bp.route('/v4/spreadsheets/<spreadsheet_id>/values/<path:range_name>', methods=['PUT'])
    def update_values(spreadsheet_id, range_name):
        response, status_code = handler.update_sheets_values(spreadsheet_id, range_name)
        return jsonify(response), status_code
    
    @google_sheets_bp.route('/v4/spreadsheets/<spreadsheet_id>:batchUpdate', methods=['POST'])
    def batch_update(spreadsheet_id):
        response, status_code = handler.batch_update_sheets(spreadsheet_id)
        return jsonify(response), status_code
    
    @google_sheets_bp.errorhandler(Exception)
    def handle_error(e):
        logger.error(f"Error in Google Sheets API mock: {str(e)}")
        return jsonify({'error': str(e)}), 500


def setup_gemini_routes(mock_responses):
    """
    Set up routes for the Gemini AI API mock
    
    Args:
        mock_responses: Dictionary containing mock responses
    """
    handler = MockResponseHandler(mock_responses)
    
    @gemini_bp.route('/models/<model>:generateContent', methods=['POST'])
    def generate_content(model):
        response, status_code = handler.generate_gemini_content(model)
        return jsonify(response), status_code
    
    @gemini_bp.route('/models/<model>:streamGenerateContent', methods=['POST'])
    def stream_generate_content(model):
        # For simplicity, we'll use the same handler as non-streaming
        response, status_code = handler.generate_gemini_content(model)
        return jsonify(response), status_code
    
    @gemini_bp.errorhandler(Exception)
    def handle_error(e):
        logger.error(f"Error in Gemini API mock: {str(e)}")
        return jsonify({'error': str(e)}), 500


def setup_gmail_routes(mock_responses):
    """
    Set up routes for the Gmail API mock
    
    Args:
        mock_responses: Dictionary containing mock responses
    """
    handler = MockResponseHandler(mock_responses)
    
    @gmail_bp.route('/v1/users/<user_id>/messages/send', methods=['POST'])
    def send_email(user_id):
        response, status_code = handler.send_gmail(user_id)
        return jsonify(response), status_code
    
    @gmail_bp.route('/v1/users/<user_id>/messages/<message_id>', methods=['GET'])
    def get_message(user_id, message_id):
        response, status_code = handler.get_gmail_message(user_id, message_id)
        return jsonify(response), status_code
    
    @gmail_bp.errorhandler(Exception)
    def handle_error(e):
        logger.error(f"Error in Gmail API mock: {str(e)}")
        return jsonify({'error': str(e)}), 500


def setup_routes():
    """Set up all API routes for the mock server"""
    # Load mock responses
    mock_responses = load_mock_responses()
    
    # Set up routes for each API
    setup_capital_one_routes(mock_responses)
    setup_google_sheets_routes(mock_responses)
    setup_gemini_routes(mock_responses)
    setup_gmail_routes(mock_responses)
    
    # Register all blueprints with the app
    app.register_blueprint(capital_one_bp)
    app.register_blueprint(google_sheets_bp)
    app.register_blueprint(gemini_bp)
    app.register_blueprint(gmail_bp)
    
    # Add a root route for server status check
    @app.route('/')
    def root():
        return jsonify({
            'status': 'up',
            'services': [
                'capital-one',
                'google-sheets',
                'gemini',
                'gmail'
            ],
            'version': '1.0.0'
        })


def start_server(host, port, debug):
    """
    Start the mock API server
    
    Args:
        host: Host to run the server on
        port: Port to run the server on
        debug: Whether to run in debug mode
    """
    setup_routes()
    logger.info(f"Starting mock API server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


def run_server_thread(host, port, debug):
    """
    Run the mock API server in a separate thread
    
    Args:
        host: Host to run the server on
        port: Port to run the server on
        debug: Whether to run in debug mode
    """
    global is_running
    is_running = True
    try:
        start_server(host, port, debug)
    finally:
        is_running = False


def run_server(host=None, port=None, debug=False):
    """
    Start the mock API server in a separate thread
    
    Args:
        host: Host to run the server on (defaults to MOCK_API_HOST from settings)
        port: Port to run the server on (defaults to MOCK_API_PORT from settings)
        debug: Whether to run in debug mode
        
    Returns:
        threading.Thread: Thread running the mock API server
    """
    global server_thread
    
    # Use default values from settings if not provided
    if host is None:
        host = DEVELOPMENT_SETTINGS.get('MOCK_API_HOST', 'localhost')
    if port is None:
        port = DEVELOPMENT_SETTINGS.get('MOCK_API_PORT', 8081)
    
    # Create and start a new thread for the server
    thread = threading.Thread(
        target=run_server_thread,
        args=(host, port, debug),
        daemon=True
    )
    thread.start()
    server_thread = thread
    
    logger.info(f"Mock API server thread started on {host}:{port}")
    return thread


def stop_server():
    """
    Stop the running mock API server
    
    Returns:
        bool: True if server was stopped, False if not running
    """
    global server_thread, is_running
    
    if server_thread is not None and is_running:
        # Use Flask's shutdown functionality
        with app.test_client() as client:
            client.get('/shutdown')
        
        # Wait for the thread to terminate
        server_thread.join(timeout=5.0)
        server_thread = None
        logger.info("Mock API server stopped")
        return True
    else:
        logger.info("Mock API server not running")
        return False


def main():
    """
    Main entry point for running the mock API server directly
    
    Returns:
        int: Exit code (0 for success)
    """
    args = parse_arguments()
    start_server(args.host, args.port, args.debug)
    return 0


# Add route for server shutdown
@app.route('/shutdown')
def shutdown():
    """Shutdown the Flask server"""
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'


if __name__ == '__main__':
    main()