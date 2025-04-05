"""Main entry point for the react Agent."""

import argparse
from src.tools.serp import google_search
from src.react.agent import Agent

def parse_args():
    """Parse command line arguments."""
    
    parser = argparse.ArgumentParser(description="React Agent CLI")
    parser.add_argument("--query", type=str, help="Query to process")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    return parser.parse_args()

def interactive_mode(agent):
    """Run the agent in interactive mode."""
    
    print("React Agent Interactive Mode (type 'exit' to quit)")
    while True:
        query = input("\nEnter your query: ")
        if query.lower() == "exit":
            break
        result = agent.execute(query)
        
        if "warning" in result:
            print(f"\n{result['warning']}")
        elif "error" in result:
            print(f"\n{result['error']}")
        else:
            print(f"\nResponse:\n{result['response']}")

def main():
    """Main function to run the React Agent."""
    
    args = parse_args()
    
    agent = Agent()
    agent.add_tool(google_search)
    
    if args.interactive:
        interactive_mode(agent)
    elif args.query:
        result = agent.execute(args.query)
        print(f"\nQuery: {args.query}")
        
        if "warning" in result:
            print(f"\n{result['warning']}")
        elif "error" in result:
            print(f"\n{result['error']}")
        else:
            print(f"\nResponse:\n{result['response']}")
    else:
        print("Please provide a query or use interactive mode.")

if __name__ == "__main__":
    main()