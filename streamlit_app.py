#!/usr/bin/env python3
"""
Streamlit web application for the AMO events knowledge base.
This app provides a user-friendly interface to query the knowledge base.
"""

import os
import streamlit as st
from dotenv import load_dotenv
import logging
import json
import base64
from datetime import datetime
import csv
from io import StringIO
from typing import List, Dict, Any

# Import LangChain and Pinecone components
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from pinecone import Pinecone

# Import utility functions
import query_knowledge as qk
from knowledge_utils import extract_topics_from_mapping, load_document_mapping

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("amo_streamlit_app")

# Load environment variables
load_dotenv()

# AMO Brand Colors
AMO_PRIMARY = "#7b38d8"      # Primary purple
AMO_SECONDARY = "#27ae60"    # Secondary green
AMO_ACCENT = "#f39c12"       # Accent orange
AMO_BACKGROUND = "#f8f9fa"   # Light background
AMO_TEXT = "#2c3e50"         # Dark text color

# Custom CSS
CUSTOM_CSS = f"""
<style>
    .stApp {{
        background-color: {AMO_BACKGROUND};
    }}
    .main .block-container {{
        padding-top: 2rem;
    }}
    h1, h2, h3 {{
        color: {AMO_PRIMARY};
    }}
    .stButton>button {{
        background-color: {AMO_PRIMARY};
        color: white;
        border-radius: 8px;
    }}
    .stButton>button:hover {{
        background-color: {AMO_PRIMARY}dd;
    }}
    .chat-message {{
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
    }}
    .chat-message.user {{
        background-color: #e9ecef;
    }}
    .chat-message.assistant {{
        background-color: #f1f8ff;
        border-left: 5px solid {AMO_PRIMARY};
    }}
    .source-section {{
        font-size: 0.85rem;
        color: #6c757d;
        border-top: 1px solid #dee2e6;
        padding-top: 0.5rem;
        margin-top: 0.5rem;
    }}
    /* Focus indicators for accessibility */
    *:focus {{
        outline: 3px solid {AMO_ACCENT} !important;
        outline-offset: 3px;
    }}
    /* High contrast mode */
    @media (prefers-contrast: more) {{
        body {{
            background-color: white;
            color: black;
        }}
        .stButton>button {{
            background-color: black;
            color: white;
            border: 2px solid black;
        }}
        .chat-message.user {{
            background-color: #e0e0e0;
            border: 1px solid black;
        }}
        .chat-message.assistant {{
            background-color: white;
            border: 1px solid black;
        }}
    }}
</style>
"""

# Set page configuration
st.set_page_config(
    page_title="AMO Events Knowledge Base",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "topics" not in st.session_state:
        st.session_state.topics = []
    
    if "selected_topic" not in st.session_state:
        st.session_state.selected_topic = None

    if "feedback_given" not in st.session_state:
        st.session_state.feedback_given = {}

def setup_knowledge_base() -> bool:
    """Set up the knowledge base connection."""
    try:
        # Initialize the knowledge base
        success, vector_store, error = qk.initialize_knowledge_base()
        
        if not success:
            st.error(f"Failed to initialize knowledge base: {error}")
            return False
        
        # Store vector store in session state
        st.session_state.vector_store = vector_store
        
        # Load document mapping and extract topics
        mapping = load_document_mapping()
        topics = extract_topics_from_mapping(mapping)
        st.session_state.topics = sorted(topics)
        
        logger.info("Knowledge base initialized successfully")
        return True
        
    except Exception as e:
        st.error(f"Error setting up knowledge base: {e}")
        logger.error(f"Error setting up knowledge base: {e}")
        return False

def get_csv_download_link(chat_history, filename="amo_events_chat_export.csv"):
    """Generate a CSV download link for the chat history."""
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["Role", "Content", "Timestamp"])
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for message in chat_history:
        writer.writerow([
            message["role"],
            message["content"],
            timestamp
        ])
    
    csv_string = csv_buffer.getvalue()
    b64 = base64.b64encode(csv_string.encode()).decode()
    return f'<a href="data:file/csv;base64,{b64}" download="{filename}" target="_blank">Download Chat History (CSV)</a>'

def get_json_download_link(chat_history, filename="amo_events_chat_export.json"):
    """Generate a JSON download link for the chat history."""
    # Add timestamp to each message
    export_data = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for message in chat_history:
        export_message = message.copy()
        export_message["timestamp"] = timestamp
        export_data.append(export_message)
    
    json_string = json.dumps(export_data, indent=2)
    b64 = base64.b64encode(json_string.encode()).decode()
    return f'<a href="data:file/json;base64,{b64}" download="{filename}" target="_blank">Download Chat History (JSON)</a>'

def give_feedback(message_idx, feedback_type):
    """Record user feedback for a specific message."""
    feedback_key = f"{message_idx}_{feedback_type}"
    st.session_state.feedback_given[feedback_key] = True
    
    # Here you would typically log this feedback to your analytics system
    logger.info(f"Feedback received: {feedback_type} for message {message_idx}")
    
    # Show a thank you message
    st.success("Thank you for your feedback!")

def display_chat_history():
    """Display the chat history with enhanced styling and feedback options."""
    for i, message in enumerate(st.session_state.chat_history):
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
                
                # Display sources if available
                if "sources" in message and message["sources"]:
                    with st.expander("Sources", expanded=False):
                        for source in message["sources"]:
                            st.markdown(f"**{source['title']}** - {source['source']}")
                
                # Add feedback buttons for assistant messages
                col1, col2, col3 = st.columns([1, 1, 6])
                thumbs_up_key = f"{i}_thumbs_up"
                thumbs_down_key = f"{i}_thumbs_down"
                
                # Check if feedback was already given for this message
                feedback_disabled = (f"{i}_thumbs_up" in st.session_state.feedback_given or 
                                     f"{i}_thumbs_down" in st.session_state.feedback_given)
                
                # Display feedback buttons
                if col1.button("👍", key=f"thumbs_up_{i}", disabled=feedback_disabled):
                    give_feedback(i, "thumbs_up")
                
                if col2.button("👎", key=f"thumbs_down_{i}", disabled=feedback_disabled):
                    give_feedback(i, "thumbs_down")

def process_user_query(user_query: str):
    """Process a user query and update the chat history."""
    if not st.session_state.vector_store:
        st.error("Knowledge base not initialized. Please refresh the page.")
        return
    
    # Add user query to chat history
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_query
    })
    
    # Create filter criteria if a topic is selected
    filter_criteria = None
    if st.session_state.selected_topic:
        filter_criteria = {"topics": {"$in": [st.session_state.selected_topic]}}
    
    # Format chat history for the model
    formatted_history = []
    for msg in st.session_state.chat_history[:-1]:  # Exclude current query
        if msg["role"] == "user":
            formatted_history.append({"human": msg["content"]})
        else:
            formatted_history.append({"ai": msg["content"]})
    
    # Get model from sidebar
    model = st.session_state.get("selected_model", "gpt-3.5-turbo")
    
    # Get answer
    with st.spinner("Searching knowledge base..."):
        result = qk.process_query(
            query=user_query,
            vector_store=st.session_state.vector_store,
            model_name=model,
            filter_criteria=filter_criteria,
            chat_history=formatted_history
        )
    
    # Add answer to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"],
        "used_query": result.get("used_query", user_query)
    })

def create_sidebar():
    """Create the sidebar with settings and filters."""
    # Add AMO logo if available
    try:
        # If logo file exists, display it
        if os.path.exists("assets/amo_logo.png"):
            st.sidebar.image("assets/amo_logo.png", width=200)
    except Exception:
        pass  # If logo doesn't exist, skip it
    
    st.sidebar.title("Settings")
    
    # Model selection
    st.sidebar.subheader("Model")
    selected_model = st.sidebar.selectbox(
        "Select AI model",
        options=["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o"],
        index=0,
        help="Choose the AI model to use. More advanced models may provide better answers but are slower."
    )
    st.session_state.selected_model = selected_model
    
    # Topic filter
    st.sidebar.subheader("Filter by Topic")
    
    # Add "All topics" option
    topic_options = ["All topics"] + st.session_state.topics
    
    selected_topic = st.sidebar.selectbox(
        "Select a topic",
        options=topic_options,
        index=0,
        help="Filter responses to focus on a specific topic area."
    )
    
    # Set selected topic (None if "All topics" is selected)
    if selected_topic == "All topics":
        st.session_state.selected_topic = None
    else:
        st.session_state.selected_topic = selected_topic
    
    # Export options
    if st.session_state.chat_history:
        st.sidebar.subheader("Export Conversation")
        export_col1, export_col2 = st.sidebar.columns(2)
        
        with export_col1:
            if st.button("Export as CSV", help="Download the conversation as a CSV file"):
                st.markdown(get_csv_download_link(st.session_state.chat_history), unsafe_allow_html=True)
        
        with export_col2:
            if st.button("Export as JSON", help="Download the conversation as a JSON file"):
                st.markdown(get_json_download_link(st.session_state.chat_history), unsafe_allow_html=True)
    
    # Clear chat button
    if st.sidebar.button("Clear Chat", help="Start a new conversation"):
        st.session_state.chat_history = []
        st.session_state.feedback_given = {}
        st.experimental_rerun()
    
    # Accessibility options
    with st.sidebar.expander("Accessibility Options", expanded=False):
        st.checkbox("High Contrast Mode", key="high_contrast", 
                   help="Enable high contrast mode for better visibility")
        st.checkbox("Large Text", key="large_text",
                   help="Increase text size throughout the application")
        st.slider("Text Size", min_value=100, max_value=200, value=100, step=10, 
                 key="text_size_percent", 
                 help="Adjust the text size (percentage of normal size)")
    
    # Apply accessibility settings
    if st.session_state.get("large_text", False):
        st.markdown("""
        <style>
        .stTextInput, .stSelectbox, p, div {
            font-size: 1.2rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
    
    if st.session_state.get("text_size_percent", 100) > 100:
        size = st.session_state.get("text_size_percent", 100)
        st.markdown(f"""
        <style>
        .stTextInput, .stSelectbox, p, div {{
            font-size: {size}% !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    
    # About section
    st.sidebar.subheader("About")
    st.sidebar.info(
        "This knowledge base provides information about event management "
        "using the AMO Events platform, which integrates Webflow, Airtable, "
        "Xano, n8n, and WhatsApp API."
    )

def main():
    """Main function to run the Streamlit app."""
    # Initialize session state
    initialize_session_state()
    
    # Apply custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Set up knowledge base if not already initialized
    if not st.session_state.vector_store:
        with st.spinner("Initializing knowledge base..."):
            if not setup_knowledge_base():
                st.error("Failed to initialize knowledge base. Please check your API keys and Pinecone index.")
                st.stop()
    
    # Create sidebar
    create_sidebar()
    
    # Main content
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("AMO Events Knowledge Assistant")
    with col2:
        # Add a help button
        if st.button("Help", help="Get help using this assistant"):
            st.session_state.chat_history.append({
                "role": "user",
                "content": "How do I use this knowledge assistant?"
            })
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": (
                    "Welcome to the AMO Events Knowledge Assistant! Here's how to use it:\n\n"
                    "1. **Ask questions** about event management using Webflow, Airtable, Xano, n8n, or WhatsApp API\n"
                    "2. **Filter by topic** using the sidebar if you want focused information\n"
                    "3. **View sources** by clicking the 'Sources' expander under any answer\n"
                    "4. **Give feedback** using the thumbs up/down buttons\n"
                    "5. **Export your conversation** using the export buttons in the sidebar\n"
                    "6. **Adjust accessibility settings** in the sidebar for better readability\n\n"
                    "Try asking specific questions like 'How do I connect Webflow forms to Airtable?' or 'What's the best way to send WhatsApp notifications for event reminders?'"
                ),
                "sources": []
            })
            st.experimental_rerun()
    
    st.subheader("Ask questions about event management with Webflow, Airtable, Xano, n8n, and WhatsApp API")
    
    # Display chat messages
    display_chat_history()
    
    # Chat input
    user_query = st.chat_input(
        "Ask a question about AMO Events...",
        help="Type your question here and press Enter to get an answer"
    )
    if user_query:
        process_user_query(user_query)
        st.experimental_rerun()
    
    # Topic quick buttons
    if st.session_state.topics and not st.session_state.chat_history:
        st.write("### Quick Topics")
        st.write("Click on a topic to see related information:")
        
        # Create columns for topic buttons
        cols = st.columns(3)
        
        # Display popular topics as buttons
        popular_topics = st.session_state.topics[:6]  # Limit to 6 topics
        for i, topic in enumerate(popular_topics):
            col_index = i % 3
            if cols[col_index].button(topic, key=f"topic_{i}", help=f"Get information about {topic}"):
                process_user_query(f"Tell me about {topic}")
                st.experimental_rerun()

    # Create a directory for static assets if it doesn't exist
    os.makedirs("assets", exist_ok=True)

if __name__ == "__main__":
    main() 