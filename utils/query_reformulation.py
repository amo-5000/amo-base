#!/usr/bin/env python
"""
Query Reformulation Utilities for AMO Events Knowledge Base

This module provides utilities for reformulating user queries to enhance the
retrieval performance of the AMO Events knowledge base. It includes functions for
query expansion using domain-specific synonyms, query decomposition for complex
questions, and context-aware query generation.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Domain-specific synonyms for event management terms
EVENT_SYNONYMS: Dict[str, List[str]] = {
    "registration": ["signup", "enroll", "register", "booking", "RSVP"],
    "attendee": ["guest", "participant", "visitor", "delegate", "invitee"],
    "check-in": ["arrival", "sign-in", "entrance", "admission"],
    "schedule": ["agenda", "timetable", "program", "itinerary"],
    "venue": ["location", "place", "site", "facility"],
    "speaker": ["presenter", "host", "panelist", "lecturer"],
    "session": ["talk", "presentation", "workshop", "seminar", "breakout"],
    "badge": ["name tag", "ID", "credential", "pass"],
    "ticket": ["pass", "admission", "entry", "registration"],
    "organizer": ["planner", "coordinator", "manager", "host"],
    "feedback": ["survey", "evaluation", "review", "assessment"]
}

# Patterns for identifying complex questions
COMPLEX_QUERY_PATTERNS = [
    r"(how|what).+?and.+?\?",  # Questions with "and"
    r"(how|what).+?or.+?\?",   # Questions with "or"
    r"(how|what|why).+?if.+?\?", # Questions with conditionals
    r"compare.+?and.+?\?",     # Comparison questions
    r"what are the steps to.+?\?", # Process questions
    r"^(.*\?){2,}$"            # Multiple questions in one
]

def expand_query(query: str) -> str:
    """
    Expand the query with domain-specific synonyms.
    
    Args:
        query: The original user query
        
    Returns:
        An expanded query with relevant synonyms
    """
    expanded_terms = []
    
    # Check for each term in our synonym dictionary
    for term, synonyms in EVENT_SYNONYMS.items():
        # If the term is in the query, add its synonyms
        if term.lower() in query.lower():
            # Only add the term once to avoid duplication
            if term not in expanded_terms:
                expanded_terms.append(term)
            
            # Add synonyms that aren't already in the query
            for synonym in synonyms:
                if synonym.lower() not in query.lower() and synonym not in expanded_terms:
                    expanded_terms.append(synonym)
    
    # Add expanded terms to the original query if any were found
    if expanded_terms:
        expanded_query = f"{query} {' '.join(expanded_terms)}"
        logger.info(f"Expanded query: '{query}' -> '{expanded_query}'")
        return expanded_query
    
    return query

def decompose_query(query: str) -> List[str]:
    """
    Decompose a complex query into simpler sub-queries.
    
    Args:
        query: The complex user query
        
    Returns:
        A list of simpler sub-queries
    """
    # Check if the query matches any complex patterns
    is_complex = any(re.search(pattern, query, re.IGNORECASE) for pattern in COMPLEX_QUERY_PATTERNS)
    
    if not is_complex:
        return [query]
    
    sub_queries = []
    
    # Check for multiple questions (split by question mark)
    if "?" in query and not query.endswith("?"):
        questions = [q.strip() + "?" for q in query.split("?") if q.strip()]
        sub_queries.extend(questions)
    
    # Handle "and" questions
    if " and " in query.lower() and not sub_queries:
        # This is a simple heuristic and might need refinement for complex cases
        parts = query.split(" and ")
        if len(parts) == 2:
            # Simple case: "How do I X and Y?"
            if parts[0].lower().startswith("how") or parts[0].lower().startswith("what"):
                prefix = re.match(r"(how|what|why|when|where|who|which).*?do\s+I\s+", parts[0], re.IGNORECASE)
                if prefix:
                    sub_queries.append(parts[0])
                    sub_queries.append(f"{prefix.group(0)}{parts[1]}")
    
    # If decomposition failed or not applicable, return original query
    if not sub_queries:
        return [query]
    
    logger.info(f"Decomposed query: '{query}' -> {sub_queries}")
    return sub_queries

def generate_context_aware_query(
    query: str, 
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Generate a context-aware query based on conversation history.
    
    Args:
        query: The current user query
        conversation_history: Previous messages in the conversation
        
    Returns:
        A reformulated query that incorporates conversation context
    """
    if not conversation_history or len(conversation_history) < 2:
        return query
    
    # Extract recent messages (limiting to last 3 exchanges to keep context relevant)
    recent_messages = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
    
    # Create context string from recent messages
    context_string = " ".join([msg.get("content", "") for msg in recent_messages if msg.get("content")])
    
    # Check if the query contains pronouns or references that might need context
    has_pronouns = re.search(r'\b(it|they|them|those|these|this|that)\b', query, re.IGNORECASE)
    has_references = "the same" in query.lower() or "as mentioned" in query.lower()
    
    if has_pronouns or has_references:
        # Create a more specific query including recent context
        context_aware_query = f"{query} in the context of {context_string}"
        logger.info(f"Generated context-aware query: '{query}' -> '{context_aware_query}'")
        return context_aware_query
    
    return query

def reformulate_query(
    query: str, 
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Tuple[str, List[str]]:
    """
    Reformulate a user query to improve retrieval performance.
    
    This function combines query expansion, decomposition, and context-awareness
    to produce an enhanced query for the knowledge base.
    
    Args:
        query: The original user query
        conversation_history: Previous messages in the conversation
        
    Returns:
        A tuple containing:
            - The reformulated primary query
            - A list of alternative queries (from decomposition)
    """
    # First, make the query context-aware if conversation history exists
    context_aware_query = generate_context_aware_query(query, conversation_history)
    
    # Then expand the query with domain-specific synonyms
    expanded_query = expand_query(context_aware_query)
    
    # Finally, decompose the query if it's complex
    decomposed_queries = decompose_query(expanded_query)
    
    # The primary query is the expanded version
    primary_query = expanded_query
    
    # Alternative queries are from decomposition (excluding the main expanded query)
    alternative_queries = [q for q in decomposed_queries if q != expanded_query]
    
    logger.info(f"Reformulated query: '{query}' -> primary: '{primary_query}', alternatives: {alternative_queries}")
    
    return primary_query, alternative_queries

def get_query_keywords(query: str) -> List[str]:
    """
    Extract important keywords from a query for improved retrieval.
    
    Args:
        query: User query
    
    Returns:
        List of important keywords
    """
    # Remove common stop words
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "about", "is", "are"}
    
    # Extract words, convert to lowercase, filter out stop words and short words
    words = query.lower().split()
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    return keywords

if __name__ == "__main__":
    # Example usage
    test_queries = [
        "How do I set up registration in Webflow?",
        "How do I create an event form and send it to guests?",
        "What's the best way to check in attendees and how do I track attendance?",
        "How do I set up Webflow and Airtable for my event?"
    ]
    
    for query in test_queries:
        print(f"\nOriginal: {query}")
        expanded = expand_query(query)
        print(f"Expanded: {expanded}")
        
        sub_queries = decompose_query(query)
        if len(sub_queries) > 1:
            print(f"Decomposed into: {sub_queries}")
        
        # Test full reformulation
        result = reformulate_query(query)
        if isinstance(result, tuple):
            primary_query, alternative_queries = result
            print(f"Reformulated into primary: {primary_query}")
            if len(alternative_queries) > 0:
                print(f"Alternatives: {alternative_queries}")
        else:
            print(f"Reformulated: {result}")
        
        print(f"Keywords: {get_query_keywords(query)}") 