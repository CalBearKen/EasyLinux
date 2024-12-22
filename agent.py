from openai import OpenAI
import subprocess
from typing import List, Dict, Tuple, Set
import shlex
import os
import re
from pathlib import Path

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

    def execute_command(self, command_str: str) -> Tuple[str, bool]:
        """Execute a command safely and return its output."""
        try:
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
        
        system_prompt = """You are an AI assistant that helps users with Linux commands using natural language.
        When users ask questions in natural language, translate them to appropriate Linux commands.
        
        Available commands and capabilities:
        1. File Operations:
           - View file contents: cat <filename>
           - List files: ls -l, ls -la, ls -lh
           - Create files: echo "content" > filename
           - Append to files: echo "content" >> filename
        
        2. Python Operations:
           - Run Python files: python <filename>
           - Execute Python code: python -c "code"
           - Install packages: pip install <package>
           - List installed packages: pip list
           - Show package versions: pip freeze
        
        Common translations:
        - "install package numpy" → "pip install numpy"
        - "add package pandas" → "pip install pandas"
        - "show installed packages" → "pip list"
        - "what packages are installed" → "pip freeze"
        
        Example responses:
        User: "install numpy package"
        Response: Installing numpy package using pip
        EXECUTE: pip install numpy
        
        User: "show all installed python packages"
        Response: Listing all installed Python packages
        EXECUTE: pip list
        
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