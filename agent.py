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
            }
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

    def execute_command(self, command_str: str) -> Tuple[str, bool]:
        """Execute a command safely and return its output."""
        try:
            # Split command and arguments
            args = shlex.split(command_str)
            if not args:
                return "Empty command", False
                
            command = args[0]
            command_args = args[1:]
            
            # Add debug print
            print(f"Executing command: {command} with args: {command_args}")
            
            # Validate command and arguments
            is_valid, error_msg = self.validate_command(command, command_args)
            if not is_valid:
                print(f"Command validation failed: {error_msg}")
                return error_msg, False
            
            # Execute command with timeout and resource limits
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=10,  # 10 second timeout
                cwd=self.working_directory,
                env={"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"},  # Minimal PATH
            )
            
            # Add debug print
            print(f"Command output: {result.stdout}")
            print(f"Command error: {result.stderr}")
            
            if result.returncode == 0:
                return result.stdout.strip(), True
            else:
                return f"Command failed: {result.stderr.strip()}", False
                
        except subprocess.TimeoutExpired:
            return "Command timed out after 10 seconds", False
        except Exception as e:
            print(f"Command execution error: {str(e)}")
            return f"Error executing command: {str(e)}", False

    def get_response(self, user_input: str) -> str:
        """Get a response from the AI agent."""
        self.add_to_history("user", user_input)
        
        system_prompt = """You are an AI assistant that helps users with Linux commands using natural language.
        When users ask questions in natural language, translate them to appropriate Linux commands.
        
        ALWAYS respond in this format:
        1. Brief explanation of what you'll do
        2. The exact command line: "EXECUTE: <command>"
        
        Available commands and capabilities:
        1. File Operations:
           - List files and directories: ls -l, ls -la, ls -lh
           - Show file contents: cat <filename>
           - Show file sizes: ls -lh
           - Sort files by size: ls -lS
        
        2. Search Operations:
           - Find files by name: find . -name "pattern"
           - Search file contents: grep "pattern" files
           - Find and filter files: find + grep
        
        Example responses:
        User: "Show me the largest files"
        Response: I'll list all files sorted by size in descending order.
        EXECUTE: ls -lS
        
        User: "Find Python files"
        Response: I'll search for all files with .py extension.
        EXECUTE: find . -name "*.py"
        
        User: "Search for errors"
        Response: I'll search for the word 'error' in all files.
        EXECUTE: grep -r "error" .
        
        Always include the EXECUTE: prefix before the command."""
        
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
                
                response_text = f"{explanation}\nCommand: {command}\nOutput: {result}"
                self.add_to_history("assistant", response_text)
                return response_text
            
            self.add_to_history("assistant", ai_response)
            return ai_response
            
        except Exception as e:
            print(f"Error in get_response: {str(e)}")  # Debug print
            return f"Error: {str(e)}"