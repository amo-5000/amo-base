#!/usr/bin/env python3
"""
Fallback prompts for the AMO Events knowledge base.

This module provides strategies for handling queries when no relevant 
documents are found in the knowledge base.
"""

from typing import Dict, List, Any, Optional

# Topics that the knowledge base should have information about
KNOWN_TOPICS = [
    "Webflow", "Airtable", "Xano", "n8n", "WhatsApp API", 
    "event registration", "event marketing", "attendee management",
    "event analytics", "ticket sales", "check-in process",
    "integration", "automation", "database design", "API connectivity"
]

FALLBACK_SYSTEM_PROMPT = """
You are an AI assistant for AMO Events, an events management platform.
The user's question doesn't match any specific information in our knowledge base.

Respond by:
1. Acknowledging that you don't have specific information about their exact question
2. Suggesting related topics they might be interested in
3. Offering general guidance if possible
4. Being honest about limitations

DO NOT make up specific information about AMO Events, Webflow, Airtable, Xano, n8n, or WhatsApp integrations.
"""

def generate_fallback_response(query: str) -> Dict[str, Any]:
    """
    Generate a fallback response when no relevant documents are found.
    
    Args:
        query: The user's question
    
    Returns:
        Dict with response text and suggested topics
    """
    # Extract potential keywords from the query
    query_words = set(query.lower().split())
    
    # Find related topics based on keyword matching
    related_topics = []
    for topic in KNOWN_TOPICS:
        topic_words = set(topic.lower().split())
        if any(word in query_words for word in topic_words):
            related_topics.append(topic)
    
    # If no direct matches, suggest the most relevant general topics
    if not related_topics:
        if "event" in query.lower() or "attendee" in query.lower() or "registration" in query.lower():
            related_topics = ["event registration", "attendee management"]
        elif "integrat" in query.lower() or "connect" in query.lower():
            related_topics = ["Webflow", "Airtable", "integration"]
        elif "data" in query.lower() or "database" in query.lower():
            related_topics = ["Airtable", "database design"]
        elif "automat" in query.lower() or "workflow" in query.lower():
            related_topics = ["n8n", "automation"]
        elif "message" in query.lower() or "communication" in query.lower() or "notif" in query.lower():
            related_topics = ["WhatsApp API"]
        else:
            # Default suggestions
            related_topics = ["event management", "Airtable", "Webflow"]
    
    # Limit to 3 suggestions
    related_topics = related_topics[:3]
    
    # Create a response structure
    return {
        "has_specific_info": False,
        "suggested_topics": related_topics,
        "fallback_type": "no_relevant_docs",
        "response_prefix": "I don't have specific information about that in my knowledge base."
    }

def format_fallback_message(fallback_data: Dict[str, Any], query: str) -> str:
    """
    Format a fallback response message.
    
    Args:
        fallback_data: Data from generate_fallback_response
        query: The user's original query
    
    Returns:
        Formatted fallback message
    """
    response = [fallback_data["response_prefix"]]
    
    # Add topic suggestions if available
    if fallback_data["suggested_topics"]:
        response.append("\n\nYou might be interested in these related topics instead:")
        for topic in fallback_data["suggested_topics"]:
            response.append(f"- {topic}")
    
    # Add a suggestion to reformulate the question
    response.append("\n\nIf you're looking for something specific, you could try:")
    response.append("- Using different keywords")
    response.append("- Breaking your question into smaller parts")
    response.append("- Asking about a specific tool (Webflow, Airtable, Xano, n8n, or WhatsApp)")
    
    # Add general guidance
    response.append("\n\nI'm here to help with questions about event management using the AMO platform, particularly around integrating Webflow, Airtable, Xano, n8n, and WhatsApp API for event management.")
    
    return "\n".join(response)

def get_fallback_for_query(query: str) -> str:
    """
    Generate a complete fallback response for a query.
    
    Args:
        query: The user's question
    
    Returns:
        Formatted fallback response
    """
    fallback_data = generate_fallback_response(query)
    return format_fallback_message(fallback_data, query)

# Examples of fallback responses for testing
EXAMPLE_QUERIES = [
    "How do I set up a payment gateway?",
    "What's the best way to handle event cancellations?",
    "Can you explain how to use the reporting features?",
    "How do I integrate with Shopify?",
    "What are the security features of AMO Events?"
]

if __name__ == "__main__":
    print("Fallback Response Examples\n")
    
    for query in EXAMPLE_QUERIES:
        print(f"Query: {query}")
        print("-" * 80)
        print(get_fallback_for_query(query))
        print("=" * 80)
        print() 