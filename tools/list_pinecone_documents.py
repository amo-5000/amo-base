#!/usr/bin/env python3
"""
Script to list all documents stored in the Pinecone index
"""
import os
import sys
import json
from dotenv import load_dotenv
import logging
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings

# Add parent directory to path to import project modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from knowledge_utils import load_document_mapping

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("list_pinecone_docs")

# Load environment variables
load_dotenv()

def main():
    """List documents in the Pinecone index with metadata"""
    # Get API key and index name
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX", "amo-events")
    
    if not api_key:
        logger.error("PINECONE_API_KEY not found in environment variables")
        return
    
    # Initialize Pinecone client
    pc = Pinecone(api_key=api_key)
    
    # Get the index
    index = pc.Index(index_name)
    
    # Get index stats
    stats = index.describe_index_stats()
    logger.info(f"Found index: {index_name} with {stats.total_vector_count} total vectors")
    
    # Initialize OpenAI embeddings for query
    embeddings = OpenAIEmbeddings()
    
    # Get document mapping
    mapping_file = os.getenv("DOCUMENT_MAPPING_FILE", "document_mapping.json")
    document_mapping = load_document_mapping(mapping_file)
    
    if document_mapping:
        logger.info(f"Loaded {len(document_mapping)} documents from mapping file")
        print("\n=== DOCUMENTS FROM MAPPING FILE ===")
        for doc_id, doc_info in document_mapping.items():
            print(f"\nDocument ID: {doc_id}")
            print(f"Title: {doc_info.get('title', 'Unknown')}")
            print(f"Source: {doc_info.get('source', 'Unknown')}")
            print(f"Topics: {', '.join(doc_info.get('topics', []))}")
            print(f"Chunks: {doc_info.get('total_chunks', 0)}")
            print("-" * 50)
    else:
        logger.info("No document mapping file found or empty")
    
    # Query each namespace to get actual document content
    namespaces = list(stats.namespaces.keys()) if hasattr(stats, 'namespaces') else [""]
    
    for namespace in namespaces:
        logger.info(f"Querying namespace: {namespace or 'default'}")
        print(f"\n=== DOCUMENTS IN NAMESPACE: {namespace or 'default'} ===")
        
        # Create a general query to get sample vectors
        sample_query = "about"  # Generic term likely to match many documents
        query_embedding = embeddings.embed_query(sample_query)
        
        # Get a sample of documents from this namespace
        try:
            results = index.query(
                vector=query_embedding,
                top_k=10,  # Limit to 10 samples
                include_metadata=True,
                namespace=namespace
            )
            
            doc_count = 0
            unique_sources = set()
            unique_topics = set()
            
            for match in results.matches:
                if hasattr(match, 'metadata') and '_node_content' in match.metadata:
                    try:
                        # Parse the JSON in _node_content
                        node_content = json.loads(match.metadata['_node_content'])
                        metadata = node_content.get('metadata', {})
                        
                        # Get document info
                        source = metadata.get('source', match.metadata.get('file_path', 'Unknown'))
                        title = metadata.get('title', match.metadata.get('file_name', 'Unknown'))
                        topics = metadata.get('topics', [])
                        
                        print(f"\nDocument {doc_count + 1}:")
                        print(f"ID: {match.id}")
                        print(f"Title: {title}")
                        print(f"Source: {source}")
                        print(f"Topics: {', '.join(topics) if topics else 'None'}")
                        print(f"Score: {match.score:.4f}")
                        print("-" * 50)
                        
                        doc_count += 1
                        unique_sources.add(source)
                        unique_topics.update(topics)
                        
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse _node_content as JSON for match {match.id}")
                    except Exception as e:
                        logger.error(f"Error processing match {match.id}: {e}")
            
            print(f"\nSummary for namespace '{namespace or 'default'}':")
            print(f"Sampled {doc_count} documents")
            print(f"Unique sources: {len(unique_sources)}")
            print(f"Unique topics: {len(unique_topics)}")
            if unique_topics:
                print(f"Topics: {', '.join(unique_topics)}")
            print("=" * 50)
            
        except Exception as e:
            logger.error(f"Error querying namespace '{namespace}': {e}")
    
if __name__ == "__main__":
    main() 