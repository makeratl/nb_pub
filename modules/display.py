"""Display formatting functions"""
import streamlit as st
import pandas as pd
import math
import json

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
            
        # Return rgba colors with higher opacity and more vibrant colors
        if bias < -0.6:
            return 'rgba(41, 98, 255, 0.95)'     # Far Left - Brighter Blue
        elif bias < -0.3:
            return 'rgba(33, 150, 243, 0.95)'    # Left - Vivid Blue
        elif bias < -0.1:
            return 'rgba(3, 169, 244, 0.95)'     # Center Left - Light Blue
        elif bias <= 0.1:
            return 'rgba(74, 111, 165, 0.95)'    # Neutral - Theme Blue
        elif bias <= 0.3:
            return 'rgba(255, 152, 0, 0.95)'     # Center Right - Orange
        elif bias <= 0.6:
            return 'rgba(245, 124, 0, 0.95)'     # Right - Dark Orange
        else:
            return 'rgba(230, 81, 0, 0.95)'      # Far Right - Deep Orange
            
    except (ValueError, TypeError):
        return 'rgba(28, 28, 28, 0.95)'  # Default dark background for any errors

def format_latest_headlines(headlines, category_filter, page, topic_filter=None, items_per_page=5):
    filtered_headlines = [
        headline for headline in headlines
        if (category_filter == "All Categories" or headline.get('cat', '') == category_filter)
        and (topic_filter is None or topic_filter.lower() in headline.get('topic', '').lower())
    ]
    
    total_pages = math.ceil(len(filtered_headlines) / items_per_page)
    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    paginated_headlines = filtered_headlines[start_index:end_index]
    
    headlines_html = ""
    for idx, headline in enumerate(paginated_headlines):
        bias_score = float(headline.get('bs_p', 0))  # Convert to float
        bias_color = get_bias_color(bias_score)
        headline_id = f"headline_{start_index + idx}"  # Unique ID for each headline
        article_link = headline.get('link', '')  # Get the article link
        
        # Truncate headline if too long
        headline_text = headline.get('AIHeadline', '')
        if len(headline_text) > 100:
            headline_text = headline_text[:97] + "..."
        
        headlines_html += f"""
            <div style="margin-bottom: 0.75rem; padding: 0.5rem; border: 2px solid {bias_color}; border-radius: 4px;">
                <div style="font-size: 0.9em; color: rgba(255, 255, 255, 0.95); margin-bottom: 0.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    <a href="{article_link}" target="_blank" style="color: rgba(255, 255, 255, 0.95); text-decoration: none;">{headline_text}</a>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 0.8em; color: rgba(255, 255, 255, 0.7);">
                        {headline.get('Published', '')}
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="font-size: 0.8em; color: {bias_color}; margin-right: 0.5rem;">
                            {bias_score:.2f}
                        </div>
                        <div style="font-size: 0.8em; color: rgba(192, 160, 128, 0.95);">
                            {headline.get('cat', '')}
                        </div>
                    </div>
                </div>
            </div>
        """
    
    return headlines_html, total_pages

def create_custom_progress_bar(bias_value, i):
    """Create a custom HTML progress bar with proper color styling"""
    try:
        bias = float(bias_value)
        normalized = (bias + 1) / 2  # Convert -1:1 to 0:1 scale
        percentage = normalized * 100
        bias_color = get_bias_color(bias)
        
        return f"""<div style="flex: 1; background-color: rgba(250, 252, 255, 0.9); border-radius: 3px; padding: 1px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.15); border: 1px solid rgba(64, 82, 100, 0.25);"><div style="width: {percentage}%; height: 10px; background-color: {bias_color}; border-radius: 2px; transition: width 0.3s ease; box-shadow: 0 1px 1px rgba(0,0,0,0.08);"></div></div>"""
    except Exception:
        return ""  # Return empty string on error