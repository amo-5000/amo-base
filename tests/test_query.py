#!/usr/bin/env python3
"""
Simple test script for querying the AMO Events knowledge base
"""
import os
import sys
from dotenv import load_dotenv
import logging

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_query")

# Load environment variables
load_dotenv()

# Import our modules
from query_knowledge import initialize_knowledge_base, process_query

def main():
    """Run a test query against the knowledge base"""
    # Initialize the knowledge base
    logger.info("Initializing knowledge base...")
    success, vector_store, error = initialize_knowledge_base()
    
    if not success:
        logger.error(f"Failed to initialize knowledge base: {error}")
        return
    
    # Test query
    test_query = "Tell me about insights for product teams"
    logger.info(f"Running test query: '{test_query}'")
    
    # Process the query
    result = process_query(
        query=test_query,
        vector_store=vector_store,
        model_name="gpt-3.5-turbo",
        top_k=3
    )
    
    # Print the results
    if result["success"]:
        print("\n" + "="*50)
        print(f"Query: {test_query}")
        print("="*50)
        print(f"Answer: {result['answer']}")
        print("-"*50)
        print("Sources:")
        for source in result["sources"]:
            print(f"- {source['title']} ({source['source']})")
        print("="*50 + "\n")
    else:
        logger.error(f"Query failed: {result['error']}")
    
if __name__ == "__main__":
    main() 