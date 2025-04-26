#!/usr/bin/env python3
"""
AMO Events Knowledge Base Content Updater

This script automates the process of adding new content to the knowledge base.
It can process new documents, update embeddings, and refresh the Pinecone index.
"""

import os
import sys
import argparse
import logging
import yaml
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

# Add parent directory to path to import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core modules
from dotenv import load_dotenv
import ingest_knowledge as ingester

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/content_updater.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("content_updater")

# Ensure log directory exists
os.makedirs("logs", exist_ok=True)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AMO Events Knowledge Base Content Updater")
    
    # Command options
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # add command
    add_parser = subparsers.add_parser("add", help="Add new content to the knowledge base")
    add_parser.add_argument("--path", required=True, help="Path to document or directory to add")
    add_parser.add_argument("--namespace", default="", help="Namespace for the content")
    add_parser.add_argument("--topics", nargs="+", help="Topics to associate with the content")
    add_parser.add_argument("--dry-run", action="store_true", help="Process documents but don't upload to Pinecone")
    
    # update command
    update_parser = subparsers.add_parser("update", help="Update existing content in the knowledge base")
    update_parser.add_argument("--path", required=True, help="Path to document or directory to update")
    update_parser.add_argument("--namespace", default="", help="Namespace for the content")
    update_parser.add_argument("--dry-run", action="store_true", help="Process documents but don't upload to Pinecone")
    
    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete content from the knowledge base")
    delete_parser.add_argument("--path", help="Path to document to delete")
    delete_parser.add_argument("--filter", help="JSON filter criteria to delete matching documents")
    delete_parser.add_argument("--namespace", default="", help="Namespace for the content")
    delete_parser.add_argument("--dry-run", action="store_true", help="Don't actually delete, just show what would be deleted")
    
    # list command
    list_parser = subparsers.add_parser("list", help="List content in the knowledge base")
    list_parser.add_argument("--namespace", default="", help="Namespace to list")
    list_parser.add_argument("--filter", help="JSON filter criteria to list matching documents")
    list_parser.add_argument("--format", choices=["text", "json", "yaml"], default="text", help="Output format")
    
    # backup command
    backup_parser = subparsers.add_parser("backup", help="Backup the knowledge base")
    backup_parser.add_argument("--output", required=True, help="Output directory for backup")
    
    # restore command
    restore_parser = subparsers.add_parser("restore", help="Restore the knowledge base from backup")
    restore_parser.add_argument("--input", required=True, help="Input directory containing backup")
    restore_parser.add_argument("--dry-run", action="store_true", help="Don't actually restore, just verify backup")
    
    return parser.parse_args()

def create_document_metadata(path: str, topics: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Create metadata for a document.
    
    Args:
        path: Path to the document
        topics: List of topics to associate with the document
        
    Returns:
        Dictionary with metadata
    """
    file_name = os.path.basename(path)
    file_path = os.path.abspath(path)
    
    metadata = {
        "file_name": file_name,
        "file_path": file_path,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    if topics:
        metadata["topics"] = topics
    
    return metadata

def process_documents(path: str, namespace: str, topics: Optional[List[str]] = None, update: bool = False) -> List[Dict[str, Any]]:
    """
    Process documents for addition to the knowledge base.
    
    Args:
        path: Path to document or directory
        namespace: Namespace for the content
        topics: List of topics to associate with the content
        update: Whether this is an update operation
        
    Returns:
        List of processed document dictionaries
    """
    # Check if path exists
    if not os.path.exists(path):
        logger.error(f"Path does not exist: {path}")
        return []
    
    # Initialize document list
    documents = []
    
    # Process directory or file
    if os.path.isdir(path):
        logger.info(f"Processing directory: {path}")
        
        # Get list of files in directory
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip hidden files and directories
                if file.startswith(".") or "/." in file_path:
                    continue
                
                # Process file
                try:
                    metadata = create_document_metadata(file_path, topics)
                    doc_chunks = ingester.process_document(file_path, metadata)
                    if doc_chunks:
                        documents.extend(doc_chunks)
                        logger.info(f"Processed {len(doc_chunks)} chunks from {file_path}")
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
    
    else:
        # Process single file
        logger.info(f"Processing file: {path}")
        try:
            metadata = create_document_metadata(path, topics)
            doc_chunks = ingester.process_document(path, metadata)
            if doc_chunks:
                documents.extend(doc_chunks)
                logger.info(f"Processed {len(doc_chunks)} chunks from {path}")
        except Exception as e:
            logger.error(f"Error processing {path}: {str(e)}")
    
    return documents

def add_content(args):
    """Add new content to the knowledge base."""
    logger.info(f"Adding content from {args.path} to namespace '{args.namespace}'")
    
    # Process documents
    documents = process_documents(args.path, args.namespace, args.topics)
    
    if not documents:
        logger.error("No documents processed. Aborting.")
        return False
    
    logger.info(f"Processed {len(documents)} document chunks")
    
    # If dry run, don't upload to Pinecone
    if args.dry_run:
        logger.info("Dry run - not uploading to Pinecone")
        return True
    
    # Upload to Pinecone
    try:
        load_dotenv()
        success, error = ingester.upload_to_pinecone(documents, args.namespace)
        
        if success:
            logger.info(f"Successfully uploaded {len(documents)} document chunks to Pinecone")
            return True
        else:
            logger.error(f"Error uploading to Pinecone: {error}")
            return False
            
    except Exception as e:
        logger.error(f"Error during upload: {str(e)}")
        return False

def update_content(args):
    """Update existing content in the knowledge base."""
    logger.info(f"Updating content from {args.path} in namespace '{args.namespace}'")
    
    # Get filter criteria based on file path
    if os.path.isfile(args.path):
        file_path = os.path.abspath(args.path)
        filter_criteria = {"file_path": file_path}
    else:
        directory_path = os.path.abspath(args.path)
        filter_criteria = {"file_path": {"$startswith": directory_path}}
    
    # If dry run, don't delete or upload to Pinecone
    if args.dry_run:
        logger.info("Dry run - not modifying Pinecone")
        return True
    
    # Delete existing content with matching filter
    try:
        load_dotenv()
        delete_success = ingester.delete_from_pinecone(filter_criteria, args.namespace)
        
        if not delete_success:
            logger.error("Error deleting existing content. Aborting update.")
            return False
            
    except Exception as e:
        logger.error(f"Error during delete: {str(e)}")
        return False
    
    # Process and add updated content
    documents = process_documents(args.path, args.namespace, update=True)
    
    if not documents:
        logger.error("No documents processed. Aborting.")
        return False
    
    logger.info(f"Processed {len(documents)} document chunks")
    
    # Upload to Pinecone
    try:
        success, error = ingester.upload_to_pinecone(documents, args.namespace)
        
        if success:
            logger.info(f"Successfully updated {len(documents)} document chunks in Pinecone")
            return True
        else:
            logger.error(f"Error uploading to Pinecone: {error}")
            return False
            
    except Exception as e:
        logger.error(f"Error during upload: {str(e)}")
        return False

def delete_content(args):
    """Delete content from the knowledge base."""
    # Parse filter if provided
    filter_criteria = None
    
    if args.filter:
        try:
            filter_criteria = json.loads(args.filter)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON filter: {args.filter}")
            return False
    
    # If path is provided, create filter based on path
    elif args.path:
        if os.path.isfile(args.path):
            file_path = os.path.abspath(args.path)
            filter_criteria = {"file_path": file_path}
        else:
            directory_path = os.path.abspath(args.path)
            filter_criteria = {"file_path": {"$startswith": directory_path}}
    
    if not filter_criteria:
        logger.error("Either --path or --filter must be provided")
        return False
    
    logger.info(f"Deleting content with filter {filter_criteria} from namespace '{args.namespace}'")
    
    # If dry run, don't delete from Pinecone
    if args.dry_run:
        logger.info("Dry run - not deleting from Pinecone")
        return True
    
    # Delete from Pinecone
    try:
        load_dotenv()
        success = ingester.delete_from_pinecone(filter_criteria, args.namespace)
        
        if success:
            logger.info("Successfully deleted content from Pinecone")
            return True
        else:
            logger.error("Error deleting from Pinecone")
            return False
            
    except Exception as e:
        logger.error(f"Error during delete: {str(e)}")
        return False

def list_content(args):
    """List content in the knowledge base."""
    # Parse filter if provided
    filter_criteria = None
    
    if args.filter:
        try:
            filter_criteria = json.loads(args.filter)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON filter: {args.filter}")
            return False
    
    logger.info(f"Listing content in namespace '{args.namespace}'")
    
    # Get content from Pinecone
    try:
        load_dotenv()
        success, data = ingester.list_pinecone_content(args.namespace, filter_criteria)
        
        if success:
            # Format output
            if args.format == "json":
                print(json.dumps(data, indent=2))
            elif args.format == "yaml":
                print(yaml.dump(data, default_flow_style=False))
            else:
                # Text format
                print(f"Found {len(data)} documents in namespace '{args.namespace}'")
                for i, doc in enumerate(data, 1):
                    print(f"\n--- Document {i} ---")
                    print(f"ID: {doc.get('id', 'Unknown')}")
                    print(f"File: {doc.get('metadata', {}).get('file_name', 'Unknown')}")
                    print(f"Path: {doc.get('metadata', {}).get('file_path', 'Unknown')}")
                    print(f"Topics: {doc.get('metadata', {}).get('topics', [])}")
            
            return True
        else:
            logger.error("Error listing content from Pinecone")
            return False
            
    except Exception as e:
        logger.error(f"Error during list: {str(e)}")
        return False

def backup_knowledge_base(args):
    """Backup the knowledge base."""
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Backing up knowledge base to {output_dir}")
    
    try:
        load_dotenv()
        
        # Get index statistics to find namespaces
        namespaces = ingester.get_pinecone_namespaces()
        
        for namespace in namespaces:
            namespace_dir = os.path.join(output_dir, namespace) if namespace else os.path.join(output_dir, "default")
            os.makedirs(namespace_dir, exist_ok=True)
            
            # Get content for namespace
            success, data = ingester.list_pinecone_content(namespace)
            
            if success:
                # Write data to file
                backup_file = os.path.join(namespace_dir, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(backup_file, "w") as f:
                    json.dump(data, f, indent=2)
                    
                logger.info(f"Backed up {len(data)} documents from namespace '{namespace}' to {backup_file}")
            else:
                logger.error(f"Error backing up namespace '{namespace}'")
        
        # Write metadata
        metadata_file = os.path.join(output_dir, "backup_metadata.json")
        with open(metadata_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "namespaces": namespaces,
                "version": "1.0"
            }, f, indent=2)
        
        logger.info(f"Backup completed successfully to {output_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Error during backup: {str(e)}")
        return False

def restore_knowledge_base(args):
    """Restore the knowledge base from backup."""
    input_dir = args.input
    
    if not os.path.exists(input_dir):
        logger.error(f"Backup directory does not exist: {input_dir}")
        return False
    
    # Check for metadata file
    metadata_file = os.path.join(input_dir, "backup_metadata.json")
    if not os.path.exists(metadata_file):
        logger.error(f"Metadata file not found: {metadata_file}")
        return False
    
    # Read metadata
    with open(metadata_file, "r") as f:
        metadata = json.load(f)
    
    logger.info(f"Restoring knowledge base from {input_dir} (created {metadata.get('timestamp', 'unknown')})")
    
    # If dry run, just verify backup
    if args.dry_run:
        logger.info("Dry run - verifying backup only")
        
        for namespace in metadata.get("namespaces", []):
            namespace_dir = os.path.join(input_dir, namespace) if namespace else os.path.join(input_dir, "default")
            
            if not os.path.exists(namespace_dir):
                logger.warning(f"Namespace directory not found: {namespace_dir}")
                continue
                
            # Find backup files
            backup_files = [f for f in os.listdir(namespace_dir) if f.startswith("backup_") and f.endswith(".json")]
            
            if not backup_files:
                logger.warning(f"No backup files found in {namespace_dir}")
                continue
                
            # Get latest backup file
            latest_backup = sorted(backup_files)[-1]
            backup_path = os.path.join(namespace_dir, latest_backup)
            
            # Read backup file
            with open(backup_path, "r") as f:
                data = json.load(f)
                
            logger.info(f"Verified {len(data)} documents in namespace '{namespace}' backup")
        
        logger.info("Backup verification completed successfully")
        return True
    
    # Actual restore
    try:
        load_dotenv()
        
        for namespace in metadata.get("namespaces", []):
            namespace_dir = os.path.join(input_dir, namespace) if namespace else os.path.join(input_dir, "default")
            
            if not os.path.exists(namespace_dir):
                logger.warning(f"Namespace directory not found: {namespace_dir}")
                continue
                
            # Find backup files
            backup_files = [f for f in os.listdir(namespace_dir) if f.startswith("backup_") and f.endswith(".json")]
            
            if not backup_files:
                logger.warning(f"No backup files found in {namespace_dir}")
                continue
                
            # Get latest backup file
            latest_backup = sorted(backup_files)[-1]
            backup_path = os.path.join(namespace_dir, latest_backup)
            
            # Read backup file
            with open(backup_path, "r") as f:
                data = json.load(f)
            
            # Clear existing namespace
            ingester.delete_from_pinecone(None, namespace)
            
            # Upload backup data
            success, error = ingester.upload_to_pinecone(data, namespace)
            
            if success:
                logger.info(f"Restored {len(data)} documents to namespace '{namespace}'")
            else:
                logger.error(f"Error restoring namespace '{namespace}': {error}")
        
        logger.info("Restore completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during restore: {str(e)}")
        return False

def main():
    """Main function."""
    args = parse_arguments()
    
    if args.command == "add":
        success = add_content(args)
    elif args.command == "update":
        success = update_content(args)
    elif args.command == "delete":
        success = delete_content(args)
    elif args.command == "list":
        success = list_content(args)
    elif args.command == "backup":
        success = backup_knowledge_base(args)
    elif args.command == "restore":
        success = restore_knowledge_base(args)
    else:
        # No command specified
        logger.error("No command specified. Use --help for usage information.")
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 