#!/usr/bin/env python3
"""
AMO Knowledge Base Ingestion Script

This script processes documents and adds them to the Pinecone vector database for
the AMO events knowledge base. It supports processing individual files, directories,
and URLs, and includes chunking, embedding, and metadata extraction.
"""

import os
import argparse
import logging
import glob
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import time
from dotenv import load_dotenv
from tqdm import tqdm
import signal
import sys

# LangChain imports
from langchain.document_loaders import (
    TextLoader,
    UnstructuredMarkdownLoader,
    PyPDFLoader,
    Docx2txtLoader,
    CSVLoader,
    UnstructuredHTMLLoader,
    SeleniumURLLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.document_transformers import Html2TextTransformer
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

# Import utility functions
from knowledge_utils import (
    generate_document_id,
    extract_metadata_from_file,
    detect_document_type,
    load_document_mapping,
    save_document_mapping,
    extract_topics_from_text,
    get_document_stats
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("amo_ingest")

# Load environment variables
load_dotenv()

# Initialize embeddings model
def get_embeddings_model() -> OpenAIEmbeddings:
    """
    Initialize and return the embeddings model.
    
    Returns:
        OpenAIEmbeddings instance
    """
    try:
        return OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=os.environ.get("OPENAI_API_KEY")
        )
    except Exception as e:
        logger.error(f"Failed to initialize embeddings model: {str(e)}")
        raise

# Initialize Pinecone
def setup_pinecone() -> Pinecone:
    """
    Initialize and return Pinecone client.
    
    Returns:
        Pinecone client instance
    """
    try:
        api_key = os.environ.get("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        
        # Initialize with new class-based approach
        return Pinecone(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {str(e)}")
        raise

# Create or get Pinecone index
def get_pinecone_index(client: Pinecone, index_name: str) -> Any:
    """
    Get or create a Pinecone index.
    
    Args:
        client: Pinecone client
        index_name: Name of the index
        
    Returns:
        Pinecone index
    """
    try:
        # Check if index exists
        existing_indexes = [index.name for index in client.list_indexes()]
        if index_name not in existing_indexes:
            # Create index if it doesn't exist
            logger.info(f"Creating new Pinecone index: {index_name}")
            client.create_index(
                name=index_name,
                dimension=1536,  # OpenAI ada-002 embeddings are 1536 dimensions
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-west-2"
                )
            )
            # Wait for index to initialize
            time.sleep(1)
        
        # Return the index
        return client.Index(index_name)
    except Exception as e:
        logger.error(f"Failed to get or create Pinecone index: {str(e)}")
        raise

# Document loading functions
def load_document(file_path: str) -> List[Any]:
    """
    Load a document from a file path using the appropriate loader.
    
    Args:
        file_path: Path to the document
        
    Returns:
        List of document objects
    """
    doc_type = detect_document_type(file_path)
    
    try:
        if doc_type == "text":
            return TextLoader(file_path, encoding="utf-8").load()
        elif doc_type == "markdown":
            return UnstructuredMarkdownLoader(file_path).load()
        elif doc_type == "pdf":
            return PyPDFLoader(file_path).load()
        elif doc_type == "word":
            return Docx2txtLoader(file_path).load()
        elif doc_type == "csv":
            return CSVLoader(file_path).load()
        elif doc_type in ["html", "htm"]:
            return UnstructuredHTMLLoader(file_path).load()
        else:
            # Default to text loader for unknown types
            logger.warning(f"Unknown document type for {file_path}. Using text loader.")
            return TextLoader(file_path, encoding="utf-8").load()
    except Exception as e:
        logger.error(f"Failed to load document {file_path}: {str(e)}")
        return []

def load_url(url: str) -> List[Any]:
    """
    Load content from a URL.
    
    Args:
        url: The URL to load
        
    Returns:
        List of document objects
    """
    try:
        loader = SeleniumURLLoader(urls=[url])
        documents = loader.load()
        
        # Convert HTML to text if needed
        if any("<html" in doc.page_content.lower() for doc in documents):
            html2text = Html2TextTransformer()
            documents = html2text.transform_documents(documents)
        
        # Set metadata for the document
        for doc in documents:
            if "source" not in doc.metadata:
                doc.metadata["source"] = url
            if "title" not in doc.metadata:
                # Extract title from URL
                title = url.split("/")[-1].replace("-", " ").replace("_", " ")
                if not title or title.endswith((".html", ".htm")):
                    title = "Web Page: " + url.split("//")[-1].split("/")[0]
                doc.metadata["title"] = title
        
        return documents
    except Exception as e:
        logger.error(f"Failed to load URL {url}: {str(e)}")
        return []

# Document preprocessing
def split_documents(documents: List[Any], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Any]:
    """
    Split documents into chunks for embedding.
    
    Args:
        documents: List of document objects
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of document chunks
    """
    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        return splitter.split_documents(documents)
    except Exception as e:
        logger.error(f"Failed to split documents: {str(e)}")
        return []

def enhance_chunk_metadata(chunks: List[Any], base_metadata: Dict[str, Any] = None) -> List[Any]:
    """
    Enhance metadata for each chunk with additional information.
    
    Args:
        chunks: List of document chunks
        base_metadata: Base metadata to apply to all chunks
        
    Returns:
        List of chunks with enhanced metadata
    """
    if base_metadata is None:
        base_metadata = {}
    
    for i, chunk in enumerate(chunks):
        # Add chunk number
        chunk.metadata["chunk_number"] = i + 1
        chunk.metadata["chunk_id"] = f"{base_metadata.get('doc_id', 'unknown')}_{i+1}"
        
        # Add any base metadata that doesn't already exist
        for key, value in base_metadata.items():
            if key not in chunk.metadata:
                chunk.metadata[key] = value
    
    return chunks

# Ingest document
def ingest_document(
    file_path: str,
    vector_store: PineconeVectorStore,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    mapping: Dict[str, Any] = None,
    namespace: str = ""
) -> Union[str, None]:
    """
    Process and ingest a document into the vector store.
    
    Args:
        file_path: Path to the document
        vector_store: Pinecone vector store instance
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        mapping: Document mapping dictionary
        namespace: Pinecone namespace to use
        
    Returns:
        Document ID if successful, None otherwise
    """
    try:
        # Extract basic metadata
        metadata = extract_metadata_from_file(file_path)
        doc_id = generate_document_id(file_path)
        metadata["doc_id"] = doc_id
        
        # Check if document already exists in mapping
        if mapping and doc_id in mapping:
            logger.info(f"Document {doc_id} already exists in mapping")
            # Compare modification times to see if it needs updating
            existing_modified = mapping[doc_id].get("modified_at", "")
            current_modified = metadata.get("modified_at", "")
            
            if existing_modified == current_modified:
                logger.info(f"Document {doc_id} is up to date. Skipping.")
                return doc_id
            
            logger.info(f"Document {doc_id} has been modified. Updating.")
        
        # Load the document
        documents = load_document(file_path)
        if not documents:
            logger.warning(f"No content loaded from {file_path}")
            return None
        
        # Extract content for topic detection
        full_text = " ".join([doc.page_content for doc in documents])
        
        # Extract topics if not already present
        if "topics" not in metadata or not metadata["topics"]:
            # Get all existing topics from mapping for context
            all_topics = set()
            if mapping:
                for doc_info in mapping.values():
                    all_topics.update(doc_info.get("topics", []))
            
            # Extract topics from text
            metadata["topics"] = extract_topics_from_text(full_text, all_topics)
        
        # Split into chunks
        chunks = split_documents(documents, chunk_size, chunk_overlap)
        if not chunks:
            logger.warning(f"No chunks created for {file_path}")
            return None
        
        # Enhance chunk metadata
        chunks = enhance_chunk_metadata(chunks, metadata)
        
        # Add to vector store
        ids = vector_store.add_documents(
            documents=chunks,
            namespace=namespace
        )
        
        # Update mapping with chunk IDs
        chunk_info = []
        for i, chunk_id in enumerate(ids):
            chunk_info.append({
                "chunk_id": chunk_id,
                "chunk_number": i + 1,
                "vector_id": chunk_id
            })
        
        # Update mapping
        metadata["chunks"] = chunk_info
        metadata["total_chunks"] = len(chunks)
        metadata["ingested_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Update mapping dictionary
        if mapping is not None:
            mapping[doc_id] = metadata
        
        logger.info(f"Successfully ingested document {doc_id} with {len(chunks)} chunks")
        return doc_id
    
    except Exception as e:
        logger.error(f"Failed to ingest document {file_path}: {str(e)}")
        return None

def ingest_url(
    url: str,
    vector_store: PineconeVectorStore,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    mapping: Dict[str, Any] = None,
    namespace: str = ""
) -> Union[str, None]:
    """
    Process and ingest content from a URL into the vector store.
    
    Args:
        url: URL to process
        vector_store: Pinecone vector store instance
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        mapping: Document mapping dictionary
        namespace: Pinecone namespace to use
        
    Returns:
        Document ID if successful, None otherwise
    """
    try:
        # Generate a unique ID for the URL
        doc_id = generate_document_id(url, url)
        
        # Check if URL already exists in mapping
        if mapping and doc_id in mapping:
            logger.info(f"URL {doc_id} already exists in mapping")
            # URLs don't have modified dates, so we check for freshness less frequently
            # or using last_updated field that might be set
            last_update = mapping[doc_id].get("last_updated", "")
            current_time = time.strftime("%Y-%m-%d")
            
            # Only update if it's been more than 7 days
            if last_update and (time.time() - time.mktime(time.strptime(last_update, "%Y-%m-%d"))) < 7 * 24 * 60 * 60:
                logger.info(f"URL {doc_id} was updated recently. Skipping.")
                return doc_id
            
            logger.info(f"URL {doc_id} needs to be refreshed.")
        
        # Load the URL content
        documents = load_url(url)
        if not documents:
            logger.warning(f"No content loaded from {url}")
            return None
        
        # Setup basic metadata
        metadata = {
            "source": url,
            "title": documents[0].metadata.get("title", url),
            "doc_id": doc_id,
            "file_type": "url",
            "url": url
        }
        
        # Extract content for topic detection
        full_text = " ".join([doc.page_content for doc in documents])
        
        # Extract topics
        all_topics = set()
        if mapping:
            for doc_info in mapping.values():
                all_topics.update(doc_info.get("topics", []))
        
        metadata["topics"] = extract_topics_from_text(full_text, all_topics)
        
        # Split into chunks
        chunks = split_documents(documents, chunk_size, chunk_overlap)
        if not chunks:
            logger.warning(f"No chunks created for {url}")
            return None
        
        # Enhance chunk metadata
        chunks = enhance_chunk_metadata(chunks, metadata)
        
        # Add to vector store
        ids = vector_store.add_documents(
            documents=chunks,
            namespace=namespace
        )
        
        # Update mapping with chunk IDs
        chunk_info = []
        for i, chunk_id in enumerate(ids):
            chunk_info.append({
                "chunk_id": chunk_id,
                "chunk_number": i + 1,
                "vector_id": chunk_id
            })
        
        # Update mapping
        metadata["chunks"] = chunk_info
        metadata["total_chunks"] = len(chunks)
        metadata["ingested_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        metadata["last_updated"] = time.strftime("%Y-%m-%d")
        
        # Update mapping dictionary
        if mapping is not None:
            mapping[doc_id] = metadata
        
        logger.info(f"Successfully ingested URL {doc_id} with {len(chunks)} chunks")
        return doc_id
    
    except Exception as e:
        logger.error(f"Failed to ingest URL {url}: {str(e)}")
        return None

def ingest_directory(
    dir_path: str,
    vector_store: PineconeVectorStore,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    mapping: Dict[str, Any] = None,
    patterns: List[str] = None,
    exclude_patterns: List[str] = None,
    namespace: str = ""
) -> Dict[str, Any]:
    """
    Process and ingest all documents in a directory into the vector store.
    
    Args:
        dir_path: Path to the directory
        vector_store: Pinecone vector store instance
        chunk_size: Size of each chunk
        chunk_overlap: Overlap between chunks
        mapping: Document mapping dictionary
        patterns: List of file patterns to include
        exclude_patterns: List of file patterns to exclude
        namespace: Pinecone namespace to use
        
    Returns:
        Dictionary of document IDs and success status
    """
    # Set default patterns if none provided
    if patterns is None:
        patterns = ["*.txt", "*.md", "*.pdf", "*.docx", "*.doc", "*.html", "*.htm"]
    
    # Set default exclude patterns if none provided
    if exclude_patterns is None:
        exclude_patterns = ["*/.git/*", "*/node_modules/*", "*/venv/*", "*/__pycache__/*"]
    
    # Expand directory path
    dir_path = os.path.expanduser(dir_path)
    
    if not os.path.isdir(dir_path):
        logger.error(f"{dir_path} is not a valid directory")
        return {}
    
    # Get all files matching patterns
    all_files = []
    for pattern in patterns:
        glob_pattern = os.path.join(dir_path, "**", pattern)
        all_files.extend(glob.glob(glob_pattern, recursive=True))
    
    # Filter out excluded patterns
    filtered_files = []
    for file_path in all_files:
        exclude = False
        for exclude_pattern in exclude_patterns:
            if glob.fnmatch.fnmatch(file_path, exclude_pattern):
                exclude = True
                break
        if not exclude:
            filtered_files.append(file_path)
    
    # Process all files
    results = {}
    for file_path in tqdm(filtered_files, desc="Processing files"):
        doc_id = ingest_document(
            file_path=file_path,
            vector_store=vector_store,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            mapping=mapping,
            namespace=namespace
        )
        results[file_path] = doc_id is not None
    
    return results

def signal_handler(sig, frame):
    """Handle interruption signals gracefully."""
    print("\nInterrupted. Cleaning up...")
    sys.exit(0)

def main():
    """Main function to execute the script."""
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Ingest documents into the AMO events knowledge base")
    
    # Add arguments
    parser.add_argument("--file", type=str, help="Path to a single file to ingest")
    parser.add_argument("--dir", type=str, help="Path to a directory to ingest")
    parser.add_argument("--url", type=str, help="URL to ingest")
    parser.add_argument("--urls-file", type=str, help="Path to a file containing URLs to ingest, one per line")
    parser.add_argument("--index", type=str, default="amo-events", help="Name of the Pinecone index")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Size of each chunk")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Overlap between chunks")
    parser.add_argument("--namespace", type=str, default="", help="Pinecone namespace")
    parser.add_argument("--mapping-file", type=str, default="document_mapping.json", help="Path to the document mapping file")
    parser.add_argument("--patterns", type=str, nargs="+", help="File patterns to include")
    parser.add_argument("--exclude", type=str, nargs="+", help="File patterns to exclude")
    
    args = parser.parse_args()
    
    # Check if at least one input is provided
    if not any([args.file, args.dir, args.url, args.urls_file]):
        parser.error("At least one of --file, --dir, --url, or --urls-file is required")
    
    try:
        # Initialize Pinecone client and index
        pinecone_client = setup_pinecone()
        index = get_pinecone_index(pinecone_client, args.index)
        
        # Get embedding model
        embeddings = get_embeddings_model()
        
        # Initialize vector store using the new PineconeVectorStore class
        vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            text_key="text"
        )
        
        # Load document mapping
        mapping = load_document_mapping(args.mapping_file)
        
        # Process input
        if args.file:
            logger.info(f"Processing file: {args.file}")
            doc_id = ingest_document(
                file_path=args.file,
                vector_store=vector_store,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                mapping=mapping,
                namespace=args.namespace
            )
            if doc_id:
                logger.info(f"Successfully ingested file with ID: {doc_id}")
            else:
                logger.error(f"Failed to ingest file: {args.file}")
        
        if args.dir:
            logger.info(f"Processing directory: {args.dir}")
            results = ingest_directory(
                dir_path=args.dir,
                vector_store=vector_store,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                mapping=mapping,
                patterns=args.patterns,
                exclude_patterns=args.exclude,
                namespace=args.namespace
            )
            total = len(results)
            success = sum(1 for v in results.values() if v)
            logger.info(f"Successfully ingested {success}/{total} files from directory")
        
        if args.url:
            logger.info(f"Processing URL: {args.url}")
            doc_id = ingest_url(
                url=args.url,
                vector_store=vector_store,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                mapping=mapping,
                namespace=args.namespace
            )
            if doc_id:
                logger.info(f"Successfully ingested URL with ID: {doc_id}")
            else:
                logger.error(f"Failed to ingest URL: {args.url}")
        
        if args.urls_file:
            logger.info(f"Processing URLs from file: {args.urls_file}")
            with open(args.urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            success_count = 0
            for url in tqdm(urls, desc="Processing URLs"):
                doc_id = ingest_url(
                    url=url,
                    vector_store=vector_store,
                    chunk_size=args.chunk_size,
                    chunk_overlap=args.chunk_overlap,
                    mapping=mapping,
                    namespace=args.namespace
                )
                if doc_id:
                    success_count += 1
            
            logger.info(f"Successfully ingested {success_count}/{len(urls)} URLs from file")
        
        # Save updated mapping
        save_document_mapping(mapping, args.mapping_file)
        
        # Print stats
        stats = get_document_stats(mapping)
        logger.info(f"Knowledge base stats: {stats}")
        
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 