from openai import OpenAI
import subprocess
from typing import List, Dict, Tuple
import shlex

class AIAgent:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.conversation_history: List[Dict] = []
        
    def add_to_history(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})
        
    def execute_command(self, command: str) -> Tuple[str, bool]:
        """
        Safely execute a Linux command and return its output.
        Returns a tuple of (output, success)
        """
        try:
            # Use shlex.split to safely parse the command
            args = shlex.split(command)
            
            # List of allowed commands for safety
            allowed_commands = {'ls', 'pwd', 'echo', 'cat', 'grep', 'date', 'whoami', 'df', 'ps'}
            
            if args[0] not in allowed_commands:
                return f"Command '{args[0]}' is not allowed for security reasons.", False
            
            # Execute the command and capture output
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=10  # 10 second timeout
            )
            
            if result.returncode == 0:
                return result.stdout.strip(), True
            else:
                return f"Command failed: {result.stderr.strip()}", False
                
        except subprocess.TimeoutExpired:
            return "Command timed out after 10 seconds.", False
        except Exception as e:
            return f"Error executing command: {str(e)}", False
    
    def get_response(self, user_input: str) -> str:
        """Get a response from the AI agent."""
        # Add user input to conversation history
        self.add_to_history("user", user_input)
        
        system_prompt = """You are an AI assistant that can help with Linux commands. 
        If the user wants to execute a command, format your response as: 
        EXECUTE: <command>
        Otherwise, respond normally. Only use EXECUTE: for Linux commands."""
        
        try:
            # Get response from OpenAI using the new client format
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *self.conversation_history
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            # Extract AI response using the new response format
            ai_response = response.choices[0].message.content
            
            # Check if response contains a command to execute
            if ai_response.startswith("EXECUTE:"):
                command = ai_response[8:].strip()  # Remove "EXECUTE: " prefix
                result, success = self.execute_command(command)
                
                response_text = f"Command: {command}\nOutput: {result}"
                self.add_to_history("assistant", response_text)
                return response_text
            
            # Normal response
            self.add_to_history("assistant", ai_response)
            return ai_response
            
        except Exception as e:
            return f"Error: {str(e)}" 