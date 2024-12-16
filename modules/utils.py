"""Utility functions"""
import streamlit as st

def get_context_title():
    """Generate a dynamic context-aware title"""
    base_title = "AI News Brew Research"
    
    # Get search context
    if 'topic' in st.session_state and st.session_state.topic:
        search_context = f"Topic: {st.session_state.topic}"
    else:
        search_context = "Headlines"
    
    # Get time range context with bullet separator
    if 'time_range' in st.session_state:
        time_context = f" {st.session_state.time_range}"
    else:
        time_context = ""
    
    # Get cluster context
    if hasattr(st.session_state, 'selected_cluster') and st.session_state.selected_cluster:
        cluster_context = f"• {st.session_state.selected_cluster['subject']}"
    else:
        cluster_context = ""
    
    # Get step context
    if hasattr(st.session_state, 'selected_cluster') and hasattr(st.session_state, 'current_step'):
        steps = ["Generate", "Review", "Visualize", "Publish"]
        step_context = f"• Step {st.session_state.current_step}/4: {steps[st.session_state.current_step-1]}"
    else:
        step_context = ""
    
    # Combine contexts
    contexts = [search_context, time_context, cluster_context, step_context]
    subtitle = " ".join(filter(None, contexts))
    
    return base_title, subtitle

def get_category_counts(headlines):
    """Count categories and sort by frequency"""
    category_counts = {}
    for article in headlines:
        category = article.get('cat', 'Unknown').title()
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # Sort by count (descending) and then alphabetically
    sorted_categories = sorted(
        category_counts.items(),
        key=lambda x: (-x[1], x[0])
    )
    
    return sorted_categories

def reset_article_state():
    """Reset the article-related session state variables"""
    if 'article_data' in st.session_state:
        del st.session_state.article_data
    if 'selected_cluster' in st.session_state:
        del st.session_state.selected_cluster
    if 'evaluation' in st.session_state:
        del st.session_state.evaluation
    if 'publish_data' in st.session_state:
        del st.session_state.publish_data
    if 'haiku_image_path' in st.session_state:
        del st.session_state.haiku_image_path
    if 'publication_success' in st.session_state:
        del st.session_state.publication_success
    if 'published_article_id' in st.session_state:
        del st.session_state.published_article_id
    if 'published_article_url' in st.session_state:
        del st.session_state.published_article_url
    if 'article_rejected' in st.session_state:
        del st.session_state.article_rejected
    if 'feedback_mode' in st.session_state:
        del st.session_state.feedback_mode
    st.session_state.feedback_mode = False
    st.session_state.current_step = 0
    # Reset the article state variables
    st.session_state.article_title = ""
    st.session_state.article_text = ""
    st.session_state.article_url = ""
    st.session_state.article_image_url = ""
    st.session_state.article_published_date = ""
    st.session_state.article_source = ""
    st.session_state.article_authors = []
    st.session_state.article_keywords = []
    st.session_state.article_summary = ""
    st.session_state.article_language = ""
    st.session_state.article_categories = []
    # Add more article state variables as needed