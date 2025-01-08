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
import json
import time
import threading
import itertools
import sys
import docker
from docker.errors import NotFound, APIError

class AIAgent:
    def __init__(self, api_key: str):
        # First try to install docker package if not present
        try:
            import docker
        except ImportError:
            print("\rInstalling docker package...")
            import subprocess
            subprocess.check_call(["pip", "install", "docker"])
            import docker
        
        self.client = OpenAI(api_key=api_key)
        self.conversation_history: List[Dict] = []
        self.working_directory = "/app/test"  # Changed to test directory
        
        # Create test files if they don't exist
        self.initialize_test_environment()
        
        # Define allowed commands with their permitted arguments/flags
        self.command_rules = {
            'cd': {
                'allowed_flags': set(),  # cd doesn't typically use flags
                'max_args': 1,
                'description': 'Change directory'
            },
            'pwd': {
                'allowed_flags': set(),  # pwd doesn't typically use flags
                'max_args': 0,
                'description': 'Print working directory'
            },
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
                'allowed_flags': {'-h', '-s', '-a', '-sh'},
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
                'allowed_flags': {'-e', '--execute', '-D', '--database', 'USE'},
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
        
        # Special handling for python -c commands
        if command in {'python', 'python3'} and len(args) >= 2 and args[0] == '-c':
            return True, ""  # Allow python -c commands
        
        # Special handling for pip/pip3 install commands
        if command in {'pip', 'pip3'} and args and args[0] == 'install':
            return self.validate_pip_command(args)
        
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
            # If we explicitly disconnected, don't auto-reconnect
            if self.db_connection is None:
                return False
            
            # If connection exists but is stale, reconnect
            if not self.db_connection.is_connected():
                self.db_connection.ping(reconnect=True)
            
            return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            self.db_connection = None
            return False

    def execute_query(self, query: str) -> Tuple[str, bool]:
        """Execute SQL query and return results."""
        try:
            if not self.connect_to_db():
                return "Database Status: Not connected\nAction Required: Please connect to a database first", False

            cursor = self.db_connection.cursor(dictionary=True)
            
            # Handle USE database command
            if query.strip().upper().startswith('USE'):
                try:
                    cursor.execute(query)
                    self.db_connection.database = query.split()[1].strip(';')  # Update current database
                    return f"Successfully switched to database: {self.db_connection.database}", True
                except Error as e:
                    return f"Failed to switch database: {str(e)}", False
            
            cursor.execute(query)
            
            # Handle SHOW TABLES and DESCRIBE commands
            if query.strip().upper().startswith(('SHOW', 'DESCRIBE')):
                results = cursor.fetchall()
                if not results:
                    return "Query executed successfully\nResult: No tables found in database", True
                
                # Format results for SHOW TABLES
                if query.strip().upper().startswith('SHOW'):
                    tables = [list(row.values())[0] for row in results]
                    return f"Query executed successfully\nFound {len(tables)} table(s):\n- " + "\n- ".join(tables), True
                
                # Format results for DESCRIBE
                df = pd.DataFrame(results)
                return f"Query executed successfully\nTable Structure:\n{df.to_string()}", True
                
            elif query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                if not results:
                    return "Query executed successfully\nResult: No rows returned", True
                
                df = pd.DataFrame(results)
                row_count = len(results)
                col_count = len(df.columns)
                return f"Query executed successfully\nReturned: {row_count} row(s), {col_count} column(s)\n{df.to_string()}", True
            else:
                self.db_connection.commit()
                return f"Query executed successfully\nAffected rows: {cursor.rowcount}", True
                
        except Error as e:
            return f"Database Error: {str(e)}\nQuery: {query}", False
        finally:
            if 'cursor' in locals():
                cursor.close()

    def execute_loop(self, loop_type: str, operation: str) -> Tuple[str, bool]:
        """Execute a generalized loop operation."""
        try:
            result = []  # Initialize result list at the start
            
            if loop_type == "FILE":
                # Get all files in the current directory
                files = [f for f in os.listdir(self.working_directory) if os.path.isfile(os.path.join(self.working_directory, f))]
                
                if not files:
                    return "No files found in current directory", False
                
                # Split the operation into command and arguments
                cmd_parts = shlex.split(operation)
                command = cmd_parts[0]
                command_args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                
                # Validate command
                if command not in self.command_rules:
                    return f"Command '{command}' is not allowed", False
                
                # Process each file
                for file in files:
                    file_path = os.path.join(self.working_directory, file)
                    result.append(f"\n=== {file} ===")
                    
                    try:
                        # Execute command for this file
                        cmd_result = subprocess.run(
                            [command, *command_args, file_path],
                            capture_output=True,
                            text=True,
                            timeout=30,
                            cwd=self.working_directory,
                            env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
                        )
                        
                        if cmd_result.returncode == 0:
                            output = cmd_result.stdout.strip()
                            result.append(output if output else "(no output)")
                        else:
                            result.append(f"Error: {cmd_result.stderr.strip()}")
                    except Exception as e:
                        result.append(f"Error processing {file}: {str(e)}")
                
                return "\n".join(result), True
                
            elif loop_type == "TABLE":
                if not self.connect_to_db():
                    return "Failed to connect to database", False
                    
                cursor = self.db_connection.cursor(dictionary=True)
                cursor.execute("SHOW TABLES")
                tables = [list(row.values())[0] for row in cursor.fetchall()]
                
                if not tables:
                    return "No tables found in database", False
                    
                # Parse LIMIT from operation if present
                limit = None
                if "LIMIT" in operation:
                    parts = operation.split("LIMIT")
                    operation = parts[0].strip()
                    try:
                        limit = int(parts[1].strip())
                    except ValueError:
                        return "Invalid LIMIT value", False
                        
                for table in tables:
                    if operation == "SHOW":
                        result.append(f"\n=== Table: {table} ===")
                        query = f"SELECT * FROM {table}"
                        if limit:
                            query += f" LIMIT {limit}"
                        cursor.execute(query)
                        rows = cursor.fetchall()
                        if not rows:
                            result.append("(empty table)")
                        else:
                            df = pd.DataFrame(rows)
                            result.append(df.to_string())
                    elif operation == "COUNT":
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()['count']
                        result.append(f"Table {table}: {count} rows")
                    elif operation == "DESCRIBE":
                        cursor.execute(f"DESCRIBE {table}")
                        structure = cursor.fetchall()
                        df = pd.DataFrame(structure)
                        result.append(f"\n=== Structure of {table} ===")
                        result.append(df.to_string())
                        
                return "\n".join(result), True
                
            return "Invalid loop type", False
            
        except Exception as e:
            return f"Error executing loop: {str(e)}", False

    def execute_command(self, command_str: str) -> Tuple[str, bool]:
        """Execute a command safely and return its output."""
        try:
            prompt = f"$ {command_str}"
            
            # Special handling for SQL queries
            if command_str.strip().upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'SHOW', 'DESCRIBE', 'CREATE', 'USE')):
                result, success = self.execute_query(command_str)
                return f"{prompt}\n{result}", success

            args = shlex.split(command_str)
            if not args:
                return f"{prompt}\nEmpty command", False
            
            command = args[0]
            command_args = args[1:]

            # Special handling for cd command
            if command == 'cd':
                if len(command_args) == 0:
                    # cd without args goes to working_directory
                    os.chdir(self.working_directory)
                    return f"{prompt}\nChanged to {self.working_directory}", True
                elif len(command_args) == 1:
                    new_path = os.path.abspath(os.path.join(os.getcwd(), command_args[0]))
                    if not new_path.startswith(self.working_directory):
                        return f"{prompt}\nAccess denied: Cannot navigate outside of {self.working_directory}", False
                    os.chdir(new_path)
                    return f"{prompt}\nChanged to {new_path}", True
                else:
                    return f"{prompt}\nToo many arguments for cd command", False

            # Rest of the command handling...
            # ... existing code ...

            # Special handling for python -c commands
            if command_str.strip().startswith(('python -c', 'python3 -c')):
                args = shlex.split(command_str)
                command = args[0]
                command_args = args[1:]  # This will include -c and the code
                
                result = subprocess.run(
                    [command, *command_args],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=self.working_directory,
                    env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
                )
                
                if result.returncode == 0:
                    output = result.stdout.strip()
                    return f"{prompt}\n{output if output else '(no output)'}", True
                else:
                    return f"{prompt}\n{result.stderr.strip()}", False
            
            # Special handling for pip/pip3 install
            if command_str.strip().startswith(('pip install', 'pip3 install')):
                args = shlex.split(command_str)
                command = args[0]
                command_args = args[1:]
                
                # First run pip install
                result = subprocess.run(
                    [command, *command_args],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=self.working_directory,
                    env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
                )
                
                if result.returncode == 0:
                    # Verify installation by trying to import the package
                    package_name = command_args[1] if len(command_args) > 1 else ""
                    verify_cmd = f"python -c 'import {package_name}; print(f\"{package_name} version: \" + {package_name}.__version__)'"
                    verify_result = subprocess.run(
                        verify_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        cwd=self.working_directory
                    )
                    
                    if verify_result.returncode == 0:
                        return f"{prompt}\nPackage installed and verified: {verify_result.stdout.strip()}", True
                    else:
                        return f"{prompt}\nPackage installed but verification failed: {verify_result.stderr.strip()}", False
                else:
                    return f"{prompt}\nPackage installation failed: {result.stderr.strip()}", False
            
            # Special handling for echo commands with redirection
            if command_str.strip().startswith('echo') and ('>' in command_str or '>>' in command_str):
                # Split the command into echo part and redirection part
                parts = command_str.split('>', 1)
                echo_cmd = parts[0].strip()
                file_part = parts[1].strip().lstrip('>')  # Remove any extra '>' characters
                
                # Get the content and filename
                content = echo_cmd[5:].strip().strip('"').strip("'")  # Remove echo and quotes
                filename = file_part.strip()
                
                # Write to file
                file_path = os.path.join(self.working_directory, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                result, success = f'File "{filename}" overwritten with "{content}"', True
                return f"{prompt}\n{result}", success

            args = shlex.split(command_str)
            if not args:
                return f"{prompt}\nEmpty command", False
                
            command = args[0]
            command_args = args[1:]
            
            # Special handling for pip/pip3 install
            if command in {'pip', 'pip3'} and command_args and command_args[0] == 'install':
                is_valid, error_msg = self.validate_pip_command(command_args)
                if not is_valid:
                    return error_msg, False
                    
                # Use python -m pip to ensure we're using the right Python environment
                python_cmd = 'python' if command == 'pip' else 'python3'
                result = subprocess.run(
                    [python_cmd, '-m', 'pip'] + command_args,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=self.working_directory,
                    env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
                )
                
                if result.returncode == 0:
                    return f"{prompt}\nSuccessfully installed package(s): {' '.join(command_args[1:])}", True
                else:
                    return f"{prompt}\nPackage installation failed: {result.stderr.strip()}", False
            
            # Special handling for python commands
            elif command in {'python', 'python3'}:
                # Ensure the file exists and is in the working directory
                if len(command_args) > 0:
                    script_path = os.path.join(self.working_directory, command_args[0])
                    if not os.path.exists(script_path):
                        return f"{prompt}\nFile not found: {command_args[0]}", False
                    command_args[0] = script_path
            
            # Regular command validation
            is_valid, error_msg = self.validate_command(command, command_args)
            if not is_valid:
                return error_msg, False
            
            # Execute command
            result = subprocess.run(
                [command, *command_args],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.working_directory,
                env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                return f"{prompt}\n{output if output else '(no output)'}", True
            else:
                return f"{prompt}\n{result.stderr.strip()}", False
                
        except subprocess.TimeoutExpired:
            return f"{prompt}\nCommand timed out", False
        except Exception as e:
            return f"{prompt}\nError: {str(e)}", False

    def get_response(self, user_input: str) -> str:
        """Get a response from the AI agent using a two-step process."""
        self.add_to_history("user", user_input)
        
        # Step 1: Safety Check
        safety_prompt = """You are a security validator for shell commands. Your job is to determine if a natural language command could be harmful.
        
        Safe commands include:
        - File reading/listing (ls, cat, head, tail, less, pwd)
        - File searching/counting (find, grep, wc)
        - System information (pwd, ps, df, du)
        - Basic text processing (sort, uniq, echo)
        - Development tools (python, pip with allowed packages)
        
        Consider a command UNSAFE only if it could:
        1. Modify or delete files/directories (rm, mv, chmod, chown)
        2. Access sensitive system files (/etc/passwd, /etc/shadow)
        3. Change system settings or configuration
        4. Execute arbitrary downloaded code
        5. Access network services or open ports
        6. Attempt privilege escalation
        
        Output ONLY 'SAFE' or 'UNSAFE: <specific reason>'.
        When in doubt about a command's safety, consider it SAFE and let the command validator handle specific restrictions.
        """
        
        try:
            safety_check = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": safety_prompt},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.1,
                max_tokens=50
            )
            
            safety_result = safety_check.choices[0].message.content.strip()
            
            if not safety_result.startswith('SAFE'):
                return f"Command rejected: {safety_result.replace('UNSAFE: ', '')}"
            
            # Step 2: Command Translation
            translation_prompt = """You are an expert Linux command translator. Convert natural language into executable shell commands.
            
            Current working directory: /app/test
            Available commands: ls, cd, grep, find, cat, head, tail, wc, sort, uniq, echo, ps, df, du, pwd, python, pip
            
            Rules:
            1. For database operations, use format: EXECUTE: <sql_query>
            2. For operations on files, choose between:
               a) Single command (if possible): EXECUTE: <command>
               b) Loop over files: LOOP: FILE:<command>
            3. For database connections, use format: CONNECT: {connection_json}
            
            Examples:
            - "show size of each file" → LOOP: FILE:du -h
            - "show content of all files" → LOOP: FILE:cat
            - "count lines in each file" → LOOP: FILE:wc -l
            - "list files" → EXECUTE: ls
            - "show current directory" → EXECUTE: pwd
            - "find all python files" → EXECUTE: find . -name "*.py"
            - "show first 5 lines of each file" → LOOP: FILE:head -n 5
            
            Plan your translation:
            1. Identify if the operation needs to be applied to each file or can be done with a single command
            2. Choose the most appropriate command
            3. Add necessary flags and arguments
            4. Validate paths are within working directory
            
            Output format:
            PLAN: Brief explanation of what you'll do
            COMMAND: The actual command to execute
            """
            
            translation = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": translation_prompt},
                    *self.conversation_history[-4:],
                    {"role": "user", "content": user_input}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            translation_result = translation.choices[0].message.content.strip()
            self.add_to_history("assistant", translation_result)
            
            # Extract command from translation
            if "COMMAND:" in translation_result:
                command = translation_result.split("COMMAND:")[1].strip()
                
                # Handle different command types
                if command.startswith("EXECUTE:"):
                    cmd = command.split("EXECUTE:")[1].strip()
                    result, success = self.execute_command(cmd)
                    return f"{translation_result}\n\nResult:\n{result}"
                elif command.startswith("LOOP:"):
                    loop_cmd = command.split("LOOP:")[1].strip()
                    loop_type, operation = loop_cmd.split(":")
                    result, success = self.execute_loop(loop_type.strip(), operation.strip())
                    return f"{translation_result}\n\nResult:\n{result}"
                elif command.startswith("CONNECT:"):
                    conn_details = json.loads(command.split("CONNECT:")[1].strip())
                    result = self.connect_to_new_database(conn_details)
                    return f"{translation_result}\n\nResult:\n{result}"
                else:
                    result, success = self.execute_command(command)
                    return f"{translation_result}\n\nResult:\n{result}"
            
            return "Error: Could not extract command from translation"
            
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            print(error_msg)  # Print for debugging
            return error_msg

    def show_loading_animation(self, stop_event: threading.Event, message: str = "Connecting to database"):
        """Show a loading animation while waiting."""
        spinner = itertools.cycle(['��', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        while not stop_event.is_set():
            sys.stdout.write(f'\r{message} {next(spinner)}')
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(message) + 2) + '\r')  # Clear the line
        sys.stdout.flush()

    def ensure_docker_network(self) -> Tuple[bool, str]:
        """Ensure the Docker network exists and containers are connected."""
        try:
            # Initialize Docker client
            docker_client = docker.from_env()
            network_name = "myapp-network"
            
            # Check if network exists
            try:
                network = docker_client.networks.get(network_name)
                print(f"\rFound existing network: {network_name}")
            except NotFound:
                # Create network if it doesn't exist
                network = docker_client.networks.create(
                    network_name,
                    driver="bridge",
                    check_duplicate=True
                )
                print(f"\rCreated new network: {network_name}")
            
            # Get current container ID
            with open('/proc/self/cgroup', 'r') as f:
                for line in f:
                    if 'docker' in line:
                        current_container_id = line.split('/')[-1].strip()
                        break
            
            # Connect current container to network if not already connected
            try:
                current_container = docker_client.containers.get(current_container_id)
                network.connect(current_container)
                print(f"\rConnected current container to network")
            except APIError as e:
                if 'already exists' not in str(e):
                    raise
            
            # Connect MySQL container to network if not already connected
            try:
                mysql_container = docker_client.containers.get('mysql_container')
                network.connect(mysql_container)
                print(f"\rConnected MySQL container to network")
            except APIError as e:
                if 'already exists' not in str(e):
                    raise
            
            return True, f"Network {network_name} is ready"
            
        except Exception as e:
            return False, f"Failed to setup Docker network: {str(e)}"

    def connect_to_new_database(self, connection_details: dict) -> str:
        """Connect to a new database with provided credentials."""
        # First ensure network is setup
        network_success, network_message = self.ensure_docker_network()
        if not network_success:
            return network_message
        
        stop_loading = threading.Event()
        db_type = connection_details.get('type', 'mysql').lower()
        loading_thread = threading.Thread(
            target=self.show_loading_animation, 
            args=(stop_loading, f"Connecting to {db_type.upper()} at {connection_details.get('host', 'unknown host')}")
        )
        loading_thread.daemon = True
        
        try:
            print(f"\rStarting {db_type} connection process...")
            loading_thread.start()
            
            # Close existing connection if any
            if self.db_connection and self.db_connection.is_connected():
                print("\rClosing existing connection...")
                self.db_connection.close()
            
            # Validate required connection parameters
            required_params = {'type', 'host', 'user', 'password'}
            missing_params = required_params - set(connection_details.keys())
            if missing_params:
                return f"Connection Failed\nMissing required parameters: {', '.join(missing_params)}\nReceived: {connection_details}"
            
            print(f"\rAttempting {db_type} connection to {connection_details['host']}...")
            
            # Create new connection based on database type
            try:
                if db_type == 'mysql':
                    self.db_connection = mysql.connector.connect(
                        **{k: v for k, v in connection_details.items() if k != 'type'},
                        connect_timeout=10
                    )
                elif db_type == 'postgresql':
                    import psycopg2
                    self.db_connection = psycopg2.connect(
                        **{k: v for k, v in connection_details.items() if k != 'type'},
                        connect_timeout=10
                    )
                else:
                    return f"Unsupported database type: {db_type}"
                    
            except (Error, Exception) as e:
                return f"Connection Error\n{db_type.upper()} Error: {str(e)}\nHost: {connection_details['host']}\nUser: {connection_details['user']}"
            
            self.db_config = connection_details  # Update stored config
            
            # Test connection based on database type
            if hasattr(self.db_connection, 'is_connected') and self.db_connection.is_connected():
                cursor = self.db_connection.cursor()
                try:
                    print("\rTesting connection...")
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    print("\rConnection test passed...")
                    
                    # Get database info based on type
                    if db_type == 'mysql':
                        cursor.execute("SELECT DATABASE(), VERSION(), USER(), CURRENT_USER()")
                    elif db_type == 'postgresql':
                        cursor.execute("SELECT current_database(), version(), current_user, session_user")
                        
                    db_name, version, user, current_user = cursor.fetchone()
                    
                    return (
                        f"Connection Status: Success\n"
                        f"Type: {db_type.upper()}\n"
                        f"Server: {version}\n"
                        f"Host: {connection_details['host']}\n"
                        f"User: {user}\n"
                        f"Database: {db_name if db_name else 'None'}\n"
                        f"Connection Test: Passed\n"
                        f"Ready for queries"
                    )
                except (Error, Exception) as e:
                    return f"Connection Warning\nConnected but test query failed\nError: {str(e)}"
                finally:
                    cursor.close()
            else:
                return f"Connection Status: Failed\nCould not establish connection to {connection_details['host']}"
            
        except Exception as e:
            return f"Unexpected Error\nType: {type(e).__name__}\nDetails: {str(e)}"
        finally:
            print("\rCleaning up connection attempt...")
            stop_loading.set()
            loading_thread.join()

    def disconnect_database(self) -> str:
        """Disconnect from the current database."""
        try:
            if self.db_connection:
                if self.db_connection.is_connected():
                    db_info = f"host={self.db_config.get('host', 'unknown')}"
                    if 'database' in self.db_config:
                        db_info += f", database={self.db_config['database']}"
                    self.db_connection.close()
                    self.db_connection = None
                    return f"Disconnect Status: Success\nDisconnected from: {db_info}\nConnection state: Closed"
                return "Disconnect Status: No action needed\nReason: Connection already closed"
            return "Disconnect Status: No action needed\nReason: No active connection"
        except Error as e:
            self.db_connection = None  # Reset connection on error
            return f"Disconnect Warning\nError while disconnecting: {str(e)}\nConnection state: Reset"

    def get_current_database(self) -> str:
        """Get the name of the current database."""
        try:
            if not self.connect_to_db():
                return "Not connected to any database"

            cursor = self.db_connection.cursor()
            cursor.execute("SELECT DATABASE()")
            db_name = cursor.fetchone()[0]
            cursor.close()
            return db_name if db_name else "No database selected"
        except Error as e:
            return f"Error getting database name: {str(e)}"