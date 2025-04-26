#!/usr/bin/env python3
"""
Script to search for specific keywords or topics in the Pinecone database
"""
import os
import sys
import argparse
from dotenv import load_dotenv
import logging
import importlib.util

# Add parent directory to path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.vector_store import initialize_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("search_pinecone")

# Load environment variables
load_dotenv()

def main():
    """Search for documents in Pinecone based on keywords or topics"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Search Pinecone for documents matching keywords or topics")
    parser.add_argument("query", help="The search query")
    parser.add_argument("--namespace", "-n", default=None, help="Namespace to search in (leave empty for all)")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Maximum number of results to return")
    parser.add_argument("--show-content", "-c", action="store_true", help="Show document content")
    args = parser.parse_args()
    
    # Initialize vector store
    logger.info("Initializing vector store...")
    try:
        vector_store = initialize_vector_store()
        logger.info("Vector store initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {str(e)}")
        return
    
    # Create search filter if namespace specified
    search_filter = None
    if args.namespace:
        search_filter = {"namespace": args.namespace}
        logger.info(f"Filtering search to namespace: {args.namespace}")
    
    # Search for documents
    logger.info(f"Searching for: '{args.query}'")
    try:
        results = vector_store.similarity_search_with_score(
            query=args.query,
            k=args.limit,
            filter=search_filter
        )
        logger.info(f"Found {len(results)} results")
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        return
    
    # Display results
    print(f"\n=== SEARCH RESULTS FOR: '{args.query}' ===")
    print(f"Found {len(results)} results\n")
    
    # Group results by namespace
    results_by_namespace = {}
    for doc, score in results:
        namespace = doc.metadata.get("namespace", "default")
        if namespace not in results_by_namespace:
            results_by_namespace[namespace] = []
        results_by_namespace[namespace].append((doc, score))
    
    # Display results by namespace
    for namespace, namespace_docs in results_by_namespace.items():
        print(f"\nNAMESPACE: {namespace}")
        print("-" * 60)
        
        for i, (doc, score) in enumerate(namespace_docs):
            print(f"\nResult {i+1}:")
            print(f"Title: {doc.metadata.get('title', 'Unknown')}")
            print(f"Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"Score: {1.0 - score:.4f}")  # Convert distance to similarity score
            
            # Show topics if available
            topics = doc.metadata.get("topics", [])
            if topics and isinstance(topics, list):
                print(f"Topics: {', '.join(topics)}")
            
            # Show content if requested
            if args.show_content:
                print("\nContent Preview:")
                # Limit to first 500 characters
                content_preview = doc.page_content[:500]
                if len(doc.page_content) > 500:
                    content_preview += "..."
                print(content_preview)
            
            print("-" * 60)
    
    print("\nSearch complete!")

if __name__ == "__main__":
    main() 