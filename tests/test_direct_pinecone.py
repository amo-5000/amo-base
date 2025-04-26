#!/usr/bin/env python3
"""
Test script to directly inspect Pinecone index entries
"""
import os
import sys
from dotenv import load_dotenv
import logging
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
import json

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("direct_pinecone")

# Load environment variables
load_dotenv()

def main():
    """Inspect Pinecone index entries directly"""
    # Get API keys
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not pinecone_api_key or not openai_api_key:
        logger.error("Missing API keys. Please check your .env file.")
        return
    
    # Initialize Pinecone client
    pc = Pinecone(api_key=pinecone_api_key)
    
    # Initialize OpenAI embeddings
    embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
    
    # Get the index
    index_name = "amo-events"
    logger.info(f"Examining index: {index_name}")
    index = pc.Index(index_name)
    
    # Get index stats
    stats = index.describe_index_stats()
    logger.info(f"Total vectors: {stats.total_vector_count}")
    
    # Create a test vector to use for similarity search
    test_query = "Airtable"
    logger.info(f"Generating embedding for query: '{test_query}'")
    query_embedding = embeddings.embed_query(test_query)
    
    # Try to fetch a few records from each namespace to see their structure
    namespaces = list(stats.namespaces.keys()) if hasattr(stats, 'namespaces') else [""]
    
    for namespace in namespaces:
        logger.info(f"\nQuerying namespace: {namespace or 'default'}")
        
        # Use direct fetch from Pinecone index 
        query_results = index.query(
            vector=query_embedding,
            top_k=3,
            include_metadata=True,
            namespace=namespace
        )
        
        logger.info(f"Found {len(query_results.matches)} results")
        
        # Examine the results
        for i, match in enumerate(query_results.matches):
            logger.info(f"\nResult {i+1} (Score: {match.score:.4f}):")
            logger.info(f"ID: {match.id}")
            
            # Check what keys are available in the metadata
            if hasattr(match, 'metadata') and match.metadata:
                metadata_keys = list(match.metadata.keys())
                logger.info(f"Metadata keys: {metadata_keys}")
                
                # Check if _node_content is available and parse it
                if '_node_content' in metadata_keys:
                    try:
                        # Parse the JSON
                        node_content = json.loads(match.metadata['_node_content'])
                        logger.info(f"Node content structure: {list(node_content.keys())}")
                        
                        # Try to find text content
                        if "text" in node_content:
                            logger.info(f"Text content sample: {node_content['text'][:100]}...")
                        elif "page_content" in node_content:
                            logger.info(f"Page content sample: {node_content['page_content'][:100]}...")
                        elif "metadata" in node_content:
                            logger.info(f"Metadata structure: {list(node_content['metadata'].keys())}")
                        
                        # Look for document info
                        if "metadata" in node_content and "file_path" in node_content["metadata"]:
                            logger.info(f"File path: {node_content['metadata']['file_path']}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse node content as JSON: {e}")
                    except Exception as e:
                        logger.error(f"Error processing node content: {e}")
                
                # Look for source information
                if 'source' in metadata_keys:
                    logger.info(f"Source: {match.metadata['source']}")
                
            else:
                logger.info("No metadata found")
    
if __name__ == "__main__":
    main() 