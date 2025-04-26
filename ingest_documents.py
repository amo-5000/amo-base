#!/usr/bin/env python3
"""
Document ingestion script for the AMO events knowledge base.
Processes documents and uploads them to Pinecone.
"""

import os
import argparse
import glob
from typing import List, Dict, Any
import logging
from tqdm import tqdm
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
import pinecone

# Import our knowledge utilities
import knowledge_utils as ku

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("amo_document_ingest")

def setup_pinecone() -> None:
    """Initialize Pinecone client with API key from env vars."""
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_environment = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
    
    if not pinecone_api_key:
        raise ValueError("PINECONE_API_KEY environment variable is required")
    
    pinecone.init(api_key=pinecone_api_key, environment=pinecone_environment)
    logger.info("Pinecone initialized successfully")

def create_pinecone_index_if_not_exists(index_name: str, dimension: int = 1536) -> None:
    """Create Pinecone index if it doesn't already exist."""
    if index_name not in pinecone.list_indexes():
        logger.info(f"Creating new Pinecone index: {index_name}")
        pinecone.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine"
        )
        logger.info(f"Index {index_name} created successfully")
    else:
        logger.info(f"Index {index_name} already exists")

def read_document(file_path: str) -> str:
    """Read document content from file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return ""

def process_document(file_path: str, embeddings, vector_store, 
                     chunk_size: int = 1000, chunk_overlap: int = 200,
                     document_mapping: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Process a single document:
    1. Read content
    2. Extract metadata
    3. Preprocess
    4. Chunk
    5. Generate embeddings
    6. Store in vector database
    
    Args:
        file_path: Path to the document file
        embeddings: LangChain embeddings object
        vector_store: Pinecone vector store
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        document_mapping: Current document mapping dict
    
    Returns:
        Updated document metadata
    """
    # Extract basic file metadata
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    # Read document content
    content = read_document(file_path)
    if not content:
        logger.warning(f"Skipping empty document: {file_path}")
        return None
    
    # Extract topics
    topics = ku.extract_document_topics(content)
    
    # Create metadata
    metadata = {
        "source": file_path,
        "file_name": file_name,
        "file_type": file_ext.replace(".", ""),
        "topics": topics,
        "title": file_name  # Default to filename, can be enhanced
    }
    
    # Preprocess document
    processed = ku.preprocess_document(content, metadata)
    doc_id = processed["metadata"]["doc_id"]
    
    # Update metadata
    metadata = processed["metadata"]
    
    # Check if document already exists and needs updating
    if document_mapping and doc_id in document_mapping:
        # We could implement a change detection mechanism here
        # For simplicity, we're re-processing everything
        logger.info(f"Document {file_name} exists, updating...")
    
    # Chunk document
    chunks = ku.chunk_document(processed["text"], chunk_size, chunk_overlap)
    logger.info(f"Document {file_name} split into {len(chunks)} chunks")
    
    # Prepare documents for vector store
    docs_with_metadata = []
    for i, chunk_text in enumerate(chunks):
        # Create a copy of metadata for each chunk
        chunk_metadata = metadata.copy()
        chunk_metadata["chunk_id"] = i
        chunk_metadata["chunk_total"] = len(chunks)
        
        docs_with_metadata.append({
            "id": f"{doc_id}-chunk-{i}",
            "text": chunk_text,
            "metadata": chunk_metadata
        })
    
    # Add to vector store
    try:
        texts = [doc["text"] for doc in docs_with_metadata]
        metadatas = [doc["metadata"] for doc in docs_with_metadata]
        ids = [doc["id"] for doc in docs_with_metadata]
        
        vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        
        # Update document metadata with embedding info
        metadata["embedding_info"] = {
            "status": "completed",
            "chunks": len(chunks),
            "vector_store": "pinecone",
            "embedded_at": ku.datetime.now().isoformat()
        }
        
        return {doc_id: metadata}
        
    except Exception as e:
        logger.error(f"Error adding document to vector store: {str(e)}")
        return None

def process_documents(document_dir: str, index_name: str, 
                      file_pattern: str = "*.{txt,md,html}",
                      chunk_size: int = 1000, chunk_overlap: int = 200,
                      mapping_file: str = "document_mapping.json") -> None:
    """
    Process all documents in a directory and add them to the vector store.
    
    Args:
        document_dir: Directory containing documents
        index_name: Pinecone index name
        file_pattern: Glob pattern for files to process
        chunk_size: Maximum chunk size
        chunk_overlap: Overlap between chunks
        mapping_file: Path to document mapping file
    """
    # Load existing document mapping
    document_mapping = ku.load_document_mapping(mapping_file)
    
    # Setup embeddings and vector store
    embeddings = OpenAIEmbeddings()
    vector_store = PineconeVectorStore.from_existing_index(
        index_name=index_name,
        embedding=embeddings,
        namespace=""  # Optional namespace if you're using one
    )
    
    # Get all files matching pattern
    patterns = file_pattern.split(",")
    all_files = []
    for pattern in patterns:
        pattern_path = os.path.join(document_dir, pattern.strip())
        all_files.extend(glob.glob(pattern_path))
    
    logger.info(f"Found {len(all_files)} files to process")
    
    # Process each document
    for file_path in tqdm(all_files, desc="Processing documents"):
        result = process_document(
            file_path=file_path,
            embeddings=embeddings,
            vector_store=vector_store,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            document_mapping=document_mapping
        )
        
        if result:
            # Update document mapping
            document_mapping.update(result)
    
    # Save updated document mapping
    ku.save_document_mapping(document_mapping, mapping_file)
    logger.info(f"Document ingestion complete. Processed {len(all_files)} files.")

def main():
    """Main function to run the document ingestion process."""
    parser = argparse.ArgumentParser(description="Ingest documents into the AMO events knowledge base")
    parser.add_argument(
        "--dir", 
        type=str, 
        default="./documents",
        help="Directory containing documents to ingest"
    )
    parser.add_argument(
        "--pattern", 
        type=str, 
        default="*.txt,*.md,*.html",
        help="Comma-separated glob patterns for files to ingest"
    )
    parser.add_argument(
        "--index", 
        type=str, 
        default="amo-events-kb",
        help="Pinecone index name"
    )
    parser.add_argument(
        "--chunk-size", 
        type=int, 
        default=1000,
        help="Maximum chunk size in characters"
    )
    parser.add_argument(
        "--chunk-overlap", 
        type=int, 
        default=200,
        help="Overlap between chunks in characters"
    )
    parser.add_argument(
        "--mapping-file", 
        type=str, 
        default="document_mapping.json",
        help="Path to document mapping file"
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Setup Pinecone
    setup_pinecone()
    
    # Create index if it doesn't exist
    create_pinecone_index_if_not_exists(args.index)
    
    # Process documents
    process_documents(
        document_dir=args.dir,
        index_name=args.index,
        file_pattern=args.pattern,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        mapping_file=args.mapping_file
    )

if __name__ == "__main__":
    main() 