#!/usr/bin/env python3
"""
Test script for querying the AMO Events knowledge base with namespace filters
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
logger = logging.getLogger("namespace_test")

# Load environment variables
load_dotenv()

# Import from query_knowledge.py
from query_knowledge import initialize_knowledge_base

def main():
    """Run test queries with namespace filters"""
    # Initialize knowledge base
    logger.info("Initializing knowledge base...")
    success, vector_store, error = initialize_knowledge_base()
    
    if not success:
        logger.error(f"Failed to initialize knowledge base: {error}")
        return
    
    # Create a test query
    test_query = "What is Airtable?"
    
    # Try both namespaces
    namespaces = ["amo-events", "airtable", ""]
    
    for namespace in namespaces:
        logger.info(f"Querying with namespace: '{namespace or 'default'}'")
        
        try:
            # Run similarity search with the namespace
            docs = vector_store.similarity_search(
                query=test_query,
                k=3,
                namespace=namespace
            )
            
            # Print results
            print(f"\n=== Results for namespace: {namespace or 'default'} ===")
            print(f"Found {len(docs)} documents")
            
            for i, doc in enumerate(docs):
                print(f"\nDocument {i+1}:")
                print(f"Source: {doc.metadata.get('source', 'Unknown')}")
                print(f"Title: {doc.metadata.get('title', 'Untitled')}")
                if 'topics' in doc.metadata:
                    print(f"Topics: {', '.join(doc.metadata['topics'])}")
                print(f"\nContent sample: {doc.page_content[:300]}...")
                print("-" * 70)
                
        except Exception as e:
            logger.error(f"Error querying namespace '{namespace}': {e}")
    
if __name__ == "__main__":
    main() 