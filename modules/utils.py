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