#!/usr/bin/env python3
"""
Utility functions for the AMO Events knowledge base.
Handles document mapping, metadata management, and knowledge base initialization.
"""

import os
import json
import logging
from typing import Dict, List, Set, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("knowledge_utils")

# Constants
DEFAULT_MAPPING_PATH = "data/document_mapping.json"

def load_document_mapping(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the document mapping from a JSON file.
    
    Args:
        file_path: Path to the document mapping file.
        
    Returns:
        A dictionary with document mapping data.
    """
    # Use default path if not specified
    if not file_path:
        file_path = DEFAULT_MAPPING_PATH
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            logger.warning(f"Document mapping file not found at {file_path}. Using empty mapping.")
            return {}
        
        # Load the document mapping
        with open(file_path, 'r') as f:
            mapping = json.load(f)
            
        logger.info(f"Loaded document mapping with {len(mapping)} entries.")
        return mapping
        
    except Exception as e:
        logger.error(f"Error loading document mapping: {e}")
        return {}

def save_document_mapping(mapping: Dict[str, Any], file_path: Optional[str] = None) -> bool:
    """
    Save the document mapping to a JSON file.
    
    Args:
        mapping: The document mapping to save.
        file_path: Path to the document mapping file.
        
    Returns:
        True if successful, False otherwise.
    """
    # Use default path if not specified
    if not file_path:
        file_path = DEFAULT_MAPPING_PATH
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save the document mapping
        with open(file_path, 'w') as f:
            json.dump(mapping, f, indent=2)
            
        logger.info(f"Saved document mapping with {len(mapping)} entries to {file_path}.")
        return True
        
    except Exception as e:
        logger.error(f"Error saving document mapping: {e}")
        return False

def extract_topics_from_mapping(mapping: Dict[str, Any]) -> List[str]:
    """
    Extract unique topics from the document mapping.
    
    Args:
        mapping: The document mapping dictionary.
        
    Returns:
        A sorted list of unique topics.
    """
    topics: Set[str] = set()
    
    try:
        # Iterate through all documents
        for doc_id, doc_info in mapping.items():
            # Add topics if available
            if "topics" in doc_info and isinstance(doc_info["topics"], list):
                topics.update(doc_info["topics"])
                
        logger.info(f"Extracted {len(topics)} unique topics from document mapping.")
        return sorted(list(topics))
        
    except Exception as e:
        logger.error(f"Error extracting topics from mapping: {e}")
        return []

def format_sources_for_display(sources: List[Any]) -> List[Dict[str, Any]]:
    """
    Format source documents for display in the UI.
    
    Args:
        sources: List of source documents (Document objects or dictionaries) with metadata.
        
    Returns:
        A list of formatted source information.
    """
    formatted_sources = []
    
    try:
        logger.info(f"Formatting {len(sources)} sources for display")
        
        for i, source in enumerate(sources):
            logger.info(f"Source {i+1} type: {type(source)}")
            
            # Extract metadata from Document object or dictionary
            if hasattr(source, 'metadata'):
                logger.info(f"Source {i+1} has metadata attribute")
                metadata = source.metadata
            else:
                logger.info(f"Source {i+1} does NOT have metadata attribute")
                metadata = source.get("metadata", {}) if isinstance(source, dict) else {}
            
            logger.info(f"Metadata for source {i+1}: {metadata}")
            
            # Create formatted source
            formatted_source = {
                "title": metadata.get("title", "Untitled Document"),
                "source": metadata.get("source", "Unknown Source"),
                "topics": metadata.get("topics", []),
                "relevance": metadata.get("relevance", metadata.get("score", 0))
            }
            
            formatted_sources.append(formatted_source)
        
        logger.info(f"Returning {len(formatted_sources)} formatted sources")
        return formatted_sources
        
    except Exception as e:
        logger.error(f"Error formatting sources: {e}")
        return []

if __name__ == "__main__":
    # Example usage
    mapping = load_document_mapping()
    topics = extract_topics_from_mapping(mapping)
    print(f"Found {len(topics)} topics: {', '.join(topics[:5])}...") 