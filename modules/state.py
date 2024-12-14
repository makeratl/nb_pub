"""Session state management functions"""
import streamlit as st

def init_session_state():
    """Initialize session state variables"""
    if 'clusters' not in st.session_state:
        st.session_state.clusters = []
    if 'selected_cluster' not in st.session_state:
        st.session_state.selected_cluster = None
    if 'article_data' not in st.session_state:
        st.session_state.article_data = None
    if 'evaluation' not in st.session_state:
        st.session_state.evaluation = None
    if 'haiku_image' not in st.session_state:
        st.session_state.haiku_image = None
    if 'publish_data' not in st.session_state:
        st.session_state.publish_data = None

def reset_article_state():
    """Reset article-related session state"""
    # Clear all article-related state
    st.session_state.article_data = None
    st.session_state.evaluation = None
    st.session_state.haiku_image = None
    st.session_state.publish_data = None
    st.session_state.selected_cluster = None
    st.session_state.evaluating_cluster = None
    st.session_state.current_step = None
    
    # Clear publication-related state
    if hasattr(st.session_state, 'publication_success'):
        del st.session_state.publication_success
    if hasattr(st.session_state, 'published_article_id'):
        del st.session_state.published_article_id
    if hasattr(st.session_state, 'published_article_url'):
        del st.session_state.published_article_url
    
    # Ensure clusters are selectable
    for key in list(st.session_state.keys()):
        if key.startswith('cluster_') and key != 'clusters':
            del st.session_state[key]
    
    # Clear article rejection state
    if hasattr(st.session_state, 'article_rejected'):
        del st.session_state.article_rejected 
    
    # Always clear the review step initialization flag to ensure category updates
    if hasattr(st.session_state, 'review_step_initialized'):
        del st.session_state.review_step_initialized
    if hasattr(st.session_state, 'last_reviewed_article'):
        del st.session_state.last_reviewed_article