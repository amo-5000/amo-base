#!/usr/bin/env python3
"""
Script to list statistics about the Pinecone index
"""
import os
from dotenv import load_dotenv
import logging
from pinecone import Pinecone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pinecone_stats")

# Load environment variables
load_dotenv()

def main():
    """Get statistics about the Pinecone index"""
    # Get API key
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        logger.error("PINECONE_API_KEY not found in environment variables")
        return
    
    # Initialize Pinecone client
    pc = Pinecone(api_key=api_key)
    
    # List all indexes
    indexes = pc.list_indexes()
    logger.info(f"Found {len(indexes)} Pinecone indexes")
    
    for idx in indexes:
        logger.info(f"Index: {idx.name}")
        logger.info(f"  - Host: {idx.host}")
        logger.info(f"  - Dimension: {idx.dimension}")
        logger.info(f"  - Metric: {idx.metric}")
        
        try:
            # Get the index
            index = pc.Index(idx.name)
            
            # Get index stats
            stats = index.describe_index_stats()
            logger.info(f"  - Total vector count: {stats.total_vector_count}")
            
            # Print namespace information if available
            if hasattr(stats, 'namespaces') and stats.namespaces:
                logger.info(f"  - Namespaces:")
                for ns_name, ns_data in stats.namespaces.items():
                    logger.info(f"    - {ns_name}: {ns_data.vector_count} vectors")
            else:
                logger.info(f"  - No namespace information available")
                
        except Exception as e:
            logger.error(f"Error getting stats for index {idx.name}: {e}")
    
if __name__ == "__main__":
    main() 