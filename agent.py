from openai import OpenAI
import subprocess
from typing import List, Dict, Tuple, Set
import shlex
import os
import re
from pathlib import Path
import mysql.connector
from mysql.connector import Error
import pandas as pd

class AIAgent:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.conversation_history: List[Dict] = []
        self.working_directory = "/app/test"  # Changed to test directory
        
        # Create test files if they don't exist
        self.initialize_test_environment()
        
        # Define allowed commands with their permitted arguments/flags
        self.command_rules = {
            'ls': {
                'allowed_flags': {'-l', '-a', '-h', '-r', '--sort', '-S', '-lh', '-lS', '-la', '-lha'},
                'max_args': 2,
                'description': 'List directory contents'
            },
            'grep': {
                'allowed_flags': {'-i', '-v', '-n', '-r', '-l', '--recursive'},
                'max_args': 4,
                'description': 'Search for patterns'
            },
            'find': {
                'allowed_flags': {'-type', '-name', '-f'},
                'max_args': 4,
                'description': 'Search for files'
            },
            'cat': {
                'allowed_flags': {'-n', '--number'},
                'max_args': 2,
                'description': 'Display file contents'
            },
            'head': {
                'allowed_flags': {'-n'},
                'max_args': 2,
                'description': 'Output the first part of files'
            },
            'tail': {
                'allowed_flags': {'-n', '-f'},
                'max_args': 2,
                'description': 'Output the last part of files'
            },
            'wc': {
                'allowed_flags': {'-l', '-w', '-c'},
                'max_args': 2,
                'description': 'Print newline, word, and byte counts'
            },
            'sort': {
                'allowed_flags': {'-r', '-n'},
                'max_args': 2,
                'description': 'Sort lines of text files'
            },
            'uniq': {
                'allowed_flags': {'-c', '-d', '-u'},
                'max_args': 2,
                'description': 'Report or omit repeated lines'
            },
            'echo': {
                'allowed_flags': {'-n', '-e'},
                'max_args': 10,
                'description': 'Display a line of text'
            },
            'ps': {
                'allowed_flags': {'-e', '-f', '-a'},
                'max_args': 1,
                'description': 'Report process status'
            },
            'df': {
                'allowed_flags': {'-h', '-i'},
                'max_args': 1,
                'description': 'Report file system disk space usage'
            },
            'du': {
                'allowed_flags': {'-h', '-s', '-a'},
                'max_args': 2,
                'description': 'Estimate file space usage'
            },
            'python': {
                'allowed_flags': {'-u', '-m', '-c'},
                'max_args': 2,
                'description': 'Execute Python scripts'
            },
            'python3': {
                'allowed_flags': {'-u', '-m', '-c'},
                'max_args': 2,
                'description': 'Execute Python scripts'
            },
            'pip': {
                'allowed_flags': {'install', 'uninstall', 'list', 'freeze', '--version', '-r', '--user'},
                'max_args': 4,
                'description': 'Python package manager'
            },
            'pip3': {
                'allowed_flags': {'install', 'uninstall', 'list', 'freeze', '--version', '-r', '--user'},
                'max_args': 4,
                'description': 'Python package manager'
            },
            'mysql': {
                'allowed_flags': {'-e', '--execute', '-D', '--database'},
                'max_args': 5,
                'description': 'Execute MySQL commands'
            },
            'query': {
                'allowed_flags': set(),  # Custom command for SQL queries
                'max_args': 1,
                'description': 'Execute SQL queries'
            }
        }
        
        # Define allowed pip packages for security
        self.allowed_packages = {
            'requests',
            'pandas',
            'numpy',
            'matplotlib',
            'scikit-learn',
            'tensorflow',
            'torch',
            'flask',
            'django',
            'pytest',
            'beautifulsoup4',
            'pillow',
            'opencv-python',
            'sqlalchemy',
            'psycopg2-binary',
            'pymongo',
            'redis',
            'celery',
            'fastapi',
            'uvicorn',
            'aiohttp',
            'jupyter'
        }
        
        # Add MySQL connection
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'mysql'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', 'rootpassword'),
            'database': os.getenv('MYSQL_DATABASE', 'testdb')
        }
        self.db_connection = None

    def initialize_test_environment(self):
        """Create test files and directories if they don't exist."""
        try:
            os.makedirs(self.working_directory, exist_ok=True)
            test_files = {
                'test.txt': 'This is a test file\nIt has multiple lines\nSome lines have errors\nERROR: test error\nLet\'s break this down',
                'test.py': 'print("Hello from Python")\n# Test comment\nvar = "test"\nif True:\n    break',
                'logs/app.log': 'ERROR: Another error\nInfo: normal log\nDebug: break point hit',
                'data.txt': 'Test data 1\nTest data 2\nTest data 1\nBreak time'
            }
            
            for filename, content in test_files.items():
                filepath = os.path.join(self.working_directory, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, 'w') as f:
                    f.write(content)
        except Exception as e:
            print(f"Error initializing test environment: {e}")

    def add_to_history(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def validate_path(self, path: str) -> bool:
        """Validate if a path is safe to access."""
        try:
            # Convert to absolute path
            abs_path = os.path.abspath(os.path.join(self.working_directory, path))
            # Check if path is within allowed directory
            return abs_path.startswith(self.working_directory)
        except:
            return False

    def validate_command(self, command: str, args: List[str]) -> Tuple[bool, str]:
        """Validate command and its arguments."""
        if command not in self.command_rules:
            return False, f"Command '{command}' is not allowed"
            
        rules = self.command_rules[command]
        
        # Special handling for ls with combined flags
        if command == 'ls':
            # Allow common combined flags for ls
            combined_flags = {'-lS', '-lh', '-la', '-lha'}
            processed_args = []
            for arg in args:
                if arg in combined_flags or arg in rules['allowed_flags']:
                    processed_args.append(arg)
                else:
                    processed_args.append(arg)
            args = processed_args
        
        flags = {arg for arg in args if arg.startswith('-')}
        non_flags = [arg for arg in args if not arg.startswith('-')]
        
        # Validate flags
        invalid_flags = flags - rules['allowed_flags']
        if invalid_flags:
            return False, f"Invalid flags: {invalid_flags}"
            
        # Validate number of arguments
        if len(non_flags) > rules['max_args']:
            return False, f"Too many arguments. Maximum allowed: {rules['max_args']}"
            
        # Validate paths in arguments
        for arg in non_flags:
            if not self.validate_path(arg):
                return False, f"Invalid path: {arg}"
                
        return True, ""

    def validate_pip_command(self, args: List[str]) -> Tuple[bool, str]:
        """Special validation for pip commands."""
        if not args:
            return False, "No pip command specified"
            
        command = args[0]
        if command == 'install':
            # Check if package is in allowed list
            packages = [arg for arg in args[1:] if not arg.startswith('-')]
            for package in packages:
                # Remove version specifiers for checking
                base_package = package.split('==')[0].split('>=')[0].split('<=')[0]
                if base_package not in self.allowed_packages:
                    return False, f"Package '{base_package}' is not in the allowed list"
        elif command not in {'list', 'freeze', '--version'}:
            return False, f"Pip command '{command}' is not allowed"
            
        return True, ""

    def connect_to_db(self) -> bool:
        """Establish database connection."""
        try:
            if not self.db_connection or not self.db_connection.is_connected():
                self.db_connection = mysql.connector.connect(**self.db_config)
            return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False

    def execute_query(self, query: str) -> Tuple[str, bool]:
        """Execute SQL query and return results."""
        try:
            if not self.connect_to_db():
                return "Failed to connect to database", False

            cursor = self.db_connection.cursor(dictionary=True)
            cursor.execute(query)
            
            # Handle SHOW TABLES and DESCRIBE commands
            if query.strip().upper().startswith(('SHOW', 'DESCRIBE')):
                results = cursor.fetchall()
                if not results:
                    return "No tables found", True
                
                # Format results for SHOW TABLES
                if query.strip().upper().startswith('SHOW'):
                    tables = [list(row.values())[0] for row in results]
                    return "Tables in database:\n- " + "\n- ".join(tables), True
                
                # Format results for DESCRIBE
                df = pd.DataFrame(results)
                return df.to_string(), True
                
            elif query.strip().upper().startswith('SELECT'):
                # For SELECT queries, fetch and format results
                results = cursor.fetchall()
                if not results:
                    return "Query returned no results", True
                
                # Convert to pandas DataFrame for nice formatting
                df = pd.DataFrame(results)
                return df.to_string(), True
            else:
                # For INSERT, UPDATE, DELETE queries
                self.db_connection.commit()
                return f"Query executed successfully. Affected rows: {cursor.rowcount}", True
                
        except Error as e:
            return f"Database error: {str(e)}", False
        finally:
            if 'cursor' in locals():
                cursor.close()

    def execute_command(self, command_str: str) -> Tuple[str, bool]:
        """Execute a command safely and return its output."""
        try:
            # Special handling for SQL queries
            if command_str.strip().upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'SHOW', 'DESCRIBE', 'CREATE')):
                return self.execute_query(command_str)

            args = shlex.split(command_str)
            if not args:
                return "Empty command", False
                
            command = args[0]
            command_args = args[1:]
            
            # Special handling for pip commands
            if command in {'pip', 'pip3'}:
                is_valid, error_msg = self.validate_pip_command(command_args)
                if not is_valid:
                    return error_msg, False
            else:
                # Regular command validation
                is_valid, error_msg = self.validate_command(command, command_args)
                if not is_valid:
                    return error_msg, False
            
            # Execute command
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=300,  # Longer timeout for pip install
                cwd=self.working_directory,
                env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
            )
            
            if result.returncode == 0:
                return result.stdout.strip(), True
            else:
                return f"Command failed: {result.stderr.strip()}", False
                
        except subprocess.TimeoutExpired:
            return "Command timed out", False
        except Exception as e:
            return f"Error executing command: {str(e)}", False

    def get_response(self, user_input: str) -> str:
        """Get a response from the AI agent."""
        self.add_to_history("user", user_input)
        
        system_prompt = """You are an AI assistant that helps users with Linux commands and database queries using natural language.
        When users ask questions in natural language, ALWAYS translate them to proper SQL commands.
        
        For SELECT queries:
        - Use proper SQL SELECT syntax
        - For "what data" questions, use "SELECT * FROM table_name"
        - Always end SQL statements with a semicolon
        
        Example responses:
        User: "what data is in the users table"
        Response: Retrieving all data from users table
        EXECUTE: SELECT * FROM users;
        
        User: "show me the test table"
        Response: Retrieving all records from test table
        EXECUTE: SELECT * FROM test;
        
        IMPORTANT: Always respond with proper SQL syntax.
        Keep explanations brief and ensure EXECUTE: is the last line."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *self.conversation_history
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            ai_response = response.choices[0].message.content
            
            # Extract command if present
            if "EXECUTE:" in ai_response:
                parts = ai_response.split("EXECUTE:")
                explanation = parts[0].strip()
                command = parts[1].strip()
                
                print(f"Executing command: {command}")  # Debug print
                result, success = self.execute_command(command)
                
                # Format response without repeating the explanation
                response_text = f"Command: {command}\nOutput: {result}"
                self.add_to_history("assistant", response_text)
                return response_text
            
            self.add_to_history("assistant", ai_response)
            return ai_response
            
        except Exception as e:
            print(f"Error in get_response: {str(e)}")  # Debug print
            return f"Error: {str(e)}"