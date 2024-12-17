"""Display formatting functions"""
import streamlit as st
import pandas as pd
import math
import json
from dateutil import parser
from datetime import datetime
import pytz

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

def format_latest_headlines(headlines, category_filter, page_number, topic_filter=None, items_per_page=5):
    filtered_headlines = [
        headline for headline in headlines
        if (category_filter == "All Categories" or headline.get('cat', '') == category_filter)
        and (topic_filter is None or topic_filter.lower() in headline.get('topic', '').lower())
    ]
    
    total_pages = math.ceil(len(filtered_headlines) / items_per_page)
    start_index = (page_number - 1) * items_per_page
    end_index = start_index + items_per_page
    paginated_headlines = filtered_headlines[start_index:end_index]
    
    headlines_html = ""
    for idx, headline in enumerate(paginated_headlines):
        bias_score = float(headline.get('bs_p', 0))  # Convert to float
        bias_color = get_bias_color(bias_score)
        qas_score = headline.get('qas', 0)  # Get QAS score, default to 0 if not present
        headline_id = f"headline_{start_index + idx}"  # Unique ID for each headline
        article_link = headline.get('link', '')  # Get the article link
        
        # Truncate headline if too long
        headline_text = headline.get('AIHeadline', '')
        if len(headline_text) > 100:
            headline_text = headline_text[:97] + "..."
        
        # Parse the published date string
        published_date = parser.parse(headline.get('Published', ''))
        
        # Assume the server is saving timestamps in UTC
        server_timezone = pytz.timezone('America/Chicago')
        
        # Make published_date timezone-aware (server timezone)
        published_date = published_date.replace(tzinfo=server_timezone)
        
        # Get the user's local timezone
        local_timezone = pytz.timezone('US/Eastern')  # Replace with the appropriate timezone
        
        # Convert the published_date to the user's local timezone
        local_published_date = published_date.astimezone(local_timezone)
        
        # Calculate the relative time difference
        now = datetime.now(local_timezone)
        time_diff = now - local_published_date
        
        # Format original published date/time (server timezone) and converted local date/time
        original_published_datetime_str = published_date.strftime("%Y-%m-%d %H:%M:%S %Z")
        published_datetime_str = local_published_date.strftime("%Y-%m-%d %H:%M:%S")
        
        if time_diff.days == 0:
            if time_diff.seconds < 3600:
                relative_time = "Just now"
            else:
                hours = time_diff.seconds // 3600
                relative_time = f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif time_diff.days < 30:
            relative_time = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
        elif time_diff.days < 365:
            months = time_diff.days // 30
            relative_time = f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = time_diff.days // 365
            relative_time = f"{years} year{'s' if years > 1 else ''} ago"
        
        headlines_html += f"""
            <div style="margin-bottom: 0.75rem; padding: 0.5rem; border: 2px solid {bias_color}; border-radius: 4px;">
                <div style="font-size: 0.9em; color: rgba(255, 255, 255, 0.95); margin-bottom: 0.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    <a href="{article_link}" target="_blank" style="color: rgba(255, 255, 255, 0.95); text-decoration: none;">{headline_text}</a>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-size: 0.8em; color: rgba(255, 255, 255, 0.7);">
                        {relative_time}
                    </div>
                    <div style="display: flex; align-items: center;">
                        <div style="font-size: 0.8em; color: rgba(192, 160, 128, 0.95); margin-right: 0.5rem;">
                            {headline.get('cat', '')}
                        </div>
                        <div style="font-size: 0.8em; color: {bias_color};">
                            {bias_score:.2f}
                        </div>
                    </div>
                </div>
            </div>
            
        """
    
    return headlines_html, total_pages

def create_custom_progress_bar(bias_value, i):
    """Create a custom HTML color block with proper color styling"""
    try:
        bias = float(bias_value)
        bias_color = get_bias_color(bias)
        
        return f"""<div style="flex: 1; height: 10px; background-color: {bias_color}; border-radius: 3px;"></div>"""
    except Exception:
        return ""  # Return empty string on error