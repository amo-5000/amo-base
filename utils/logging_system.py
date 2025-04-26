#!/usr/bin/env python3
"""
Comprehensive logging system for the AMO Events knowledge base.

This module provides structured logging for queries, responses, and performance metrics
to enable analysis and continuous improvement of the knowledge base.
"""

import os
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("amo_kb_logger")

# Constants
LOG_DIR = "logs"
QUERY_LOG_FILE = os.path.join(LOG_DIR, "query_log.jsonl")
PERFORMANCE_LOG_FILE = os.path.join(LOG_DIR, "performance_metrics.jsonl")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error_log.jsonl")

# Create logs directory and files if they don't exist
os.makedirs(LOG_DIR, exist_ok=True)
for file_path in [QUERY_LOG_FILE, PERFORMANCE_LOG_FILE, ERROR_LOG_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            pass

def generate_query_id() -> str:
    """Generate a unique ID for each query."""
    return str(uuid.uuid4())

def log_query(
    query: str,
    query_type: str = "general",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log a user query to the query log file.
    
    Args:
        query: The user's question
        query_type: Type of query (general, how-to, comparison, etc.)
        user_id: Optional identifier for the user
        session_id: Optional identifier for the session
        context: Additional context information
        
    Returns:
        The generated query ID
    """
    query_id = generate_query_id()
    timestamp = datetime.now().isoformat()
    
    log_entry = {
        "query_id": query_id,
        "timestamp": timestamp,
        "query": query,
        "query_type": query_type,
        "user_id": user_id,
        "session_id": session_id,
        "context": context or {}
    }
    
    try:
        with open(QUERY_LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log query: {e}")
    
    return query_id

def log_response(
    query_id: str,
    response: str,
    sources: List[Dict[str, Any]],
    retrieval_time: float,
    processing_time: float,
    doc_count: int,
    confidence_score: Optional[float] = None,
    is_fallback: bool = False
) -> None:
    """
    Log a system response to a query.
    
    Args:
        query_id: The query ID returned by log_query
        response: The system's response text
        sources: The sources used for the response
        retrieval_time: Time taken to retrieve documents (seconds)
        processing_time: Time taken to process the full response (seconds)
        doc_count: Number of documents retrieved
        confidence_score: Optional confidence score (0-1)
        is_fallback: Whether this was a fallback response
    """
    timestamp = datetime.now().isoformat()
    
    response_entry = {
        "query_id": query_id,
        "timestamp": timestamp,
        "response_length": len(response),
        "doc_count": doc_count,
        "retrieval_time_ms": int(retrieval_time * 1000),
        "processing_time_ms": int(processing_time * 1000),
        "confidence_score": confidence_score,
        "is_fallback": is_fallback,
        "source_count": len(sources)
    }
    
    # Add source info (but not full content)
    if sources:
        response_entry["sources"] = [{
            "title": s.get("title", "Unknown"),
            "source": s.get("source", "Unknown"),
            "relevance": s.get("relevance", 0)
        } for s in sources]
    
    try:
        with open(PERFORMANCE_LOG_FILE, 'a') as f:
            f.write(json.dumps(response_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log response: {e}")

def log_error(
    query_id: str,
    error_type: str,
    error_message: str,
    stack_trace: Optional[str] = None
) -> None:
    """
    Log an error that occurred during query processing.
    
    Args:
        query_id: The query ID returned by log_query
        error_type: Type of error (retrieval, processing, etc.)
        error_message: Error message
        stack_trace: Optional stack trace
    """
    timestamp = datetime.now().isoformat()
    
    error_entry = {
        "query_id": query_id,
        "timestamp": timestamp,
        "error_type": error_type,
        "error_message": error_message
    }
    
    if stack_trace:
        error_entry["stack_trace"] = stack_trace
    
    try:
        with open(ERROR_LOG_FILE, 'a') as f:
            f.write(json.dumps(error_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log error: {e}")

def log_feedback(
    query_id: str,
    feedback_type: str,
    rating: Optional[int] = None,
    comments: Optional[str] = None
) -> None:
    """
    Log user feedback on a response.
    
    Args:
        query_id: The query ID returned by log_query
        feedback_type: Type of feedback (thumbs_up, thumbs_down, rating, comment)
        rating: Optional numerical rating (e.g., 1-5)
        comments: Optional user comments
    """
    timestamp = datetime.now().isoformat()
    
    feedback_entry = {
        "query_id": query_id,
        "timestamp": timestamp,
        "feedback_type": feedback_type
    }
    
    if rating is not None:
        feedback_entry["rating"] = rating
    
    if comments:
        feedback_entry["comments"] = comments
    
    try:
        # Append to the end of the query log entry with matching ID
        # This is a simple implementation; in production, you might use a database
        updated_entries = []
        found = False
        
        with open(QUERY_LOG_FILE, 'r') as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry["query_id"] == query_id:
                    if "feedback" not in entry:
                        entry["feedback"] = []
                    entry["feedback"].append(feedback_entry)
                    found = True
                updated_entries.append(entry)
        
        if found:
            with open(QUERY_LOG_FILE, 'w') as f:
                for entry in updated_entries:
                    f.write(json.dumps(entry) + "\n")
        else:
            logger.warning(f"No query found with ID {query_id} for feedback")
            
    except Exception as e:
        logger.error(f"Failed to log feedback: {e}")

class QueryLogger:
    """Query logger class for timing and tracking a complete query lifecycle."""
    
    def __init__(self, query: str, query_type: str = "general", user_id: Optional[str] = None, session_id: Optional[str] = None):
        """Initialize the query logger with query info."""
        self.start_time = time.time()
        self.retrieval_start_time = None
        self.retrieval_end_time = None
        self.query = query
        self.query_type = query_type
        self.user_id = user_id
        self.session_id = session_id
        self.query_id = log_query(query, query_type, user_id, session_id)
        self.doc_count = 0
        self.is_fallback = False
        self.sources = []
        
    def start_retrieval(self) -> None:
        """Mark the start of document retrieval."""
        self.retrieval_start_time = time.time()
    
    def end_retrieval(self, doc_count: int, sources: List[Dict[str, Any]]) -> None:
        """
        Mark the end of document retrieval.
        
        Args:
            doc_count: Number of documents retrieved
            sources: Sources metadata
        """
        self.retrieval_end_time = time.time()
        self.doc_count = doc_count
        self.sources = sources
    
    def log_error(self, error_type: str, error_message: str, stack_trace: Optional[str] = None) -> None:
        """Log an error during query processing."""
        log_error(self.query_id, error_type, error_message, stack_trace)
    
    def log_response(self, response: str, confidence_score: Optional[float] = None, is_fallback: bool = False) -> None:
        """
        Log the final response to the query.
        
        Args:
            response: The response text
            confidence_score: Optional confidence score
            is_fallback: Whether this was a fallback response
        """
        end_time = time.time()
        
        # Calculate times
        total_time = end_time - self.start_time
        
        # If retrieval was timed, calculate it; otherwise set to 0
        if self.retrieval_start_time and self.retrieval_end_time:
            retrieval_time = self.retrieval_end_time - self.retrieval_start_time
        else:
            retrieval_time = 0
        
        # Log the complete response
        log_response(
            self.query_id,
            response,
            self.sources,
            retrieval_time,
            total_time,
            self.doc_count,
            confidence_score,
            is_fallback
        )

def get_recent_queries(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the most recent queries from the log.
    
    Args:
        limit: Maximum number of queries to return
        
    Returns:
        List of recent query entries
    """
    queries = []
    
    try:
        with open(QUERY_LOG_FILE, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    queries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.error(f"Error reading query log: {e}")
    
    # Sort by timestamp (newest first) and limit
    queries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return queries[:limit]

def get_performance_metrics(days: int = 7) -> Dict[str, Any]:
    """
    Calculate performance metrics for the specified number of days.
    
    Args:
        days: Number of days to include in metrics
        
    Returns:
        Dictionary of performance metrics
    """
    metrics = {
        "total_queries": 0,
        "avg_retrieval_time_ms": 0,
        "avg_processing_time_ms": 0,
        "fallback_percentage": 0,
        "avg_doc_count": 0,
        "error_count": 0
    }
    
    # Calculate cutoff time
    now = datetime.now()
    cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = cutoff.timestamp() - (days * 24 * 60 * 60)
    
    performance_data = []
    error_count = 0
    
    # Read performance data
    try:
        with open(PERFORMANCE_LOG_FILE, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    timestamp = datetime.fromisoformat(entry.get("timestamp", "")).timestamp()
                    if timestamp >= cutoff:
                        performance_data.append(entry)
                except (json.JSONDecodeError, ValueError):
                    continue
    except Exception as e:
        logger.error(f"Error reading performance log: {e}")
    
    # Count errors
    try:
        with open(ERROR_LOG_FILE, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    timestamp = datetime.fromisoformat(entry.get("timestamp", "")).timestamp()
                    if timestamp >= cutoff:
                        error_count += 1
                except (json.JSONDecodeError, ValueError):
                    continue
    except Exception as e:
        logger.error(f"Error reading error log: {e}")
    
    # Calculate metrics
    if performance_data:
        metrics["total_queries"] = len(performance_data)
        metrics["avg_retrieval_time_ms"] = sum(entry.get("retrieval_time_ms", 0) for entry in performance_data) / len(performance_data)
        metrics["avg_processing_time_ms"] = sum(entry.get("processing_time_ms", 0) for entry in performance_data) / len(performance_data)
        metrics["fallback_percentage"] = sum(1 for entry in performance_data if entry.get("is_fallback", False)) / len(performance_data) * 100
        metrics["avg_doc_count"] = sum(entry.get("doc_count", 0) for entry in performance_data) / len(performance_data)
        metrics["error_count"] = error_count
    
    return metrics

if __name__ == "__main__":
    # Example usage
    print("Testing Query Logger")
    
    # Log a test query
    query = "How do I integrate Webflow with Airtable for event registration?"
    logger = QueryLogger(query, query_type="how-to")
    
    # Simulate processing
    logger.start_retrieval()
    time.sleep(0.5)  # Simulate retrieval time
    
    # Log retrieval completion
    sources = [
        {"title": "Webflow Integration Guide", "source": "docs/webflow.md", "relevance": 0.92},
        {"title": "Airtable Setup for Events", "source": "docs/airtable.md", "relevance": 0.87},
    ]
    logger.end_retrieval(doc_count=2, sources=sources)
    
    # Generate a response
    time.sleep(0.5)  # Simulate processing time
    response = "To integrate Webflow with Airtable for event registration, you need to..."
    
    # Log the response
    logger.log_response(response, confidence_score=0.85)
    
    # Log some feedback
    log_feedback(logger.query_id, "thumbs_up", rating=5)
    
    print("Query logged successfully with ID:", logger.query_id)
    
    # Example of retrieving metrics
    metrics = get_performance_metrics(days=7)
    print("\nPerformance Metrics (7 days):")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}") 