from agent import AIAgent
from dotenv import load_dotenv
import os

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from .env
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env file")
        return
    
    # Initialize the agent
    agent = AIAgent(api_key)
    
    print("AI Agent initialized. Type 'quit' to exit.")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            break
            
        response = agent.get_response(user_input)
        print(f"Agent: {response}")

if __name__ == "__main__":
    main() 