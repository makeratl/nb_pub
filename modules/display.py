"""Display formatting functions"""
import streamlit as st
import pandas as pd
import math

def get_bias_color(bias_value):
    """Generate color for bias value from -1 to 1"""
    try:
        # Handle string numeric values
        if isinstance(bias_value, str):
            try:
                bias = float(bias_value)
            except ValueError:
                return 'rgba(28, 28, 28, 0.95)'  # Default dark background for non-numeric strings
        else:
            bias = float(bias_value)
        
        # Clamp value between -1 and 1
        bias = max(-1.0, min(1.0, bias))
            
        # Return rgba colors with opacity
        if bias < -0.6: return 'rgba(41, 98, 255, 0.15)'     # Far Left
        elif bias < -0.3: return 'rgba(33, 150, 243, 0.15)'   # Left
        elif bias < -0.1: return 'rgba(3, 169, 244, 0.15)'    # Center Left
        elif bias <= 0.1: return 'rgba(28, 28, 28, 0.95)'     # Neutral
        elif bias <= 0.3: return 'rgba(255, 107, 107, 0.15)'  # Center Right
        elif bias <= 0.6: return 'rgba(229, 57, 53, 0.15)'    # Right
        else: return 'rgba(183, 28, 28, 0.15)'               # Far Right
            
    except (ValueError, TypeError):
        return 'rgba(28, 28, 28, 0.95)'  # Default dark background for any errors

def format_latest_headlines(headlines, selected_category=None, page=1, per_page=5, topic_filter=None):
    """Format headlines with metadata for sidebar display with pagination"""
    # Ensure page is valid
    page = max(1, page)  # Ensure page is at least 1
    
    # First filter by category if selected
    if selected_category and selected_category != "All Categories":
        filtered_headlines = [h for h in headlines if h.get('cat', '').title() == selected_category]
    else:
        filtered_headlines = headlines
    
    # Apply topic keyword filtering if provided and not empty
    if topic_filter and topic_filter.strip():
        # Split the topic filter into terms
        terms = []
        current_term = []
        in_quotes = False
        
        # Parse the topic filter string
        for char in topic_filter:
            if char == '"':
                in_quotes = not in_quotes
                if not in_quotes and current_term:
                    terms.append(''.join(current_term))
                    current_term = []
            elif char == ' ' and not in_quotes:
                if current_term:
                    terms.append(''.join(current_term))
                    current_term = []
            else:
                current_term.append(char)
        
        if current_term:
            terms.append(''.join(current_term))
        
        # Filter headlines based on terms
        for term in terms:
            if term.startswith('"') and term.endswith('"'):
                # Exact phrase match
                phrase = term[1:-1].lower()
                filtered_headlines = [
                    h for h in filtered_headlines 
                    if phrase in h.get('topic', '').lower() or phrase in h.get('AIHeadline', '').lower()
                ]
            else:
                # Individual word match
                filtered_headlines = [
                    h for h in filtered_headlines 
                    if term.lower() in h.get('topic', '').lower() or term.lower() in h.get('AIHeadline', '').lower()
                ]
    
    # Paginate filtered headlines
    total_pages = math.ceil(len(filtered_headlines) / per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_headlines = filtered_headlines[start_idx:end_idx]
    
    # Add styling
    st.markdown("""
        <style>
            .headline-item {
                padding: 0.4rem 0.5rem;
                margin-bottom: 0.25rem;
                border-radius: 3px;
                transition: all 0.2s ease;
                border: 1px solid rgba(255, 255, 255, 0.1);
                position: relative;
            }
            .headline-text {
                color: rgba(255, 255, 255, 0.95);
                font-size: 0.8em;
                line-height: 1.2;
                margin-bottom: 0.25rem;
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .headline-metadata {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-size: 0.65em;
                color: rgba(255, 255, 255, 0.6);
                line-height: 1;
                min-width: 0;
            }
        </style>
    """, unsafe_allow_html=True)
    
    headlines_html = '<div class="headline-list">'
    
    for article in page_headlines:
        try:
            published_date = pd.to_datetime(article['Published']).strftime('%b %d')
        except:
            published_date = "Recent"
            
        bias = article.get('bs_p', 'Neutral')
        bias_color = get_bias_color(bias)
        category = article.get('cat', '').title()
        topic = article.get('topic', '').title()
        
        headlines_html += f"""
            <div class="headline-item" style="background-color: {bias_color}">
                <div class="headline-text">{article['AIHeadline']}</div>
                <div class="headline-metadata">
                    <span class="headline-category">{category}</span>
                    <span class="headline-topic">{topic}</span>
                    <span class="headline-date">{published_date}</span>
                </div>
            </div>"""
    
    headlines_html += '</div>'
    return headlines_html, total_pages

def create_custom_progress_bar(bias_value, i):
    """Create a custom HTML progress bar with proper color styling"""
    try:
        bias = float(bias_value)
        normalized = (bias + 1) / 2  # Convert -1:1 to 0:1 scale
        percentage = normalized * 100
        bias_color = get_bias_color(bias)
        
        return f"""<div style="flex: 1; background-color: rgba(240, 242, 246, 0.8); border-radius: 3px; padding: 1px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.2); border: 1px solid rgba(44, 62, 80, 0.3);"><div style="width: {percentage}%; height: 10px; background-color: {bias_color}; border-radius: 2px; transition: width 0.3s ease; box-shadow: 0 1px 1px rgba(0,0,0,0.1);"></div></div>"""
    except Exception:
        return ""  # Return empty string on error