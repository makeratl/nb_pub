"""
AI News Brew Research Web Interface

Key Data Format Notes:
1. Bias Values (bs_p):
   - Numeric values ranging from -1.0 to 1.0
   - Negative values indicate left-leaning bias
   - Positive values indicate right-leaning bias
   - Color mapping:
     * Far Left   (-1.0 to -0.6): Deep Blue (#2962FF)
     * Left       (-0.6 to -0.3): Blue (#2196F3)
     * Center Left(-0.3 to -0.1): Light Blue (#03A9F4)
     * Neutral    (-0.1 to 0.1):  Theme Blue (#4A6FA5)
     * Center Right(0.1 to 0.3):  Orange (#FF9800)
     * Right      (0.3 to 0.6):   Dark Orange (#F57C00)
     * Far Right  (0.6 to 1.0):   Deep Orange (#E65100)

2. Categories (cat):
   - Text values, displayed in title case
   - Shown in gold color (rgba(192, 160, 128, 0.95))

3. Topics (topic):
   - Text values, displayed in title case
   - Shown in theme blue color (#4A6FA5)

4. API Response Format:
   - Latest headlines endpoint returns:
     * ID: Article identifier
     * AIHeadline: Generated headline text
     * Published: Timestamp (formatted as 'MMM DD, YYYY')
     * bs_p: Bias score (-1 to 1)
     * topic: Article topic
     * cat: Article category

5. Theme Colors:
   - Primary Blue: #4A6FA5
   - Gold Accent: rgba(192, 160, 128, 0.95)
   - Text White: rgba(255, 255, 255, 0.95)
   - Text Dim: rgba(255, 255, 255, 0.5)
"""

import streamlit as st
from modules.state import init_session_state, reset_article_state
from modules.api_client import get_news_data, fetch_latest_headlines
from modules.display import format_latest_headlines, get_bias_color, create_custom_progress_bar
from modules.article_wizard import (
    display_article_step, 
    display_review_step,
    display_image_step,
    display_final_review
)
from modules.utils import get_context_title, get_category_counts
from chat_codegpt import chat_with_codegpt
from modules.cluster_analysis import analyze_cluster, create_article
import time

def main():
    st.set_page_config(layout="wide", page_title="AI News Brew Research")
    
    # Initialize session state
    if 'article_rejected' not in st.session_state:
        st.session_state.article_rejected = False
    
    init_session_state()
    
    # Add global styles
    st.markdown("""
        <style>
            /* Color palette */
            :root {
                --primary-bg: #f8faff;
                --secondary-bg: #edf2ff;
                --accent-blue: #4a6fa5;
                --accent-gold: #c0a080;
                --text-primary: #2c3e50;
                --text-secondary: #5a6c7e;
                --border-color: #e0e7ff;
                --metric-bg: #ffffff;
            }
            
            /* Source tags styling - moved to global scope */
            .source-tags {
                display: flex !important;
                flex-wrap: wrap !important;
                gap: 8px !important;
                margin-bottom: 1rem !important;
            }
            .source-tag {
                background-color: rgba(74, 111, 165, 0.1) !important;
                border: 1px solid rgba(74, 111, 165, 0.3) !important;
                border-radius: 16px !important;
                padding: 4px 12px !important;
                font-size: 0.9em !important;
                color: #4a6fa5 !important;
                display: inline-flex !important;
                align-items: center !important;
                gap: 6px !important;
            }
            .source-count {
                background-color: rgba(74, 111, 165, 0.2) !important;
                border-radius: 50% !important;
                width: 20px !important;
                height: 20px !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                font-size: 0.8em !important;
                font-weight: 500 !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Dynamic title
    title, subtitle = get_context_title()
    st.title(title)
    st.markdown(f'<p class="subtitle">{subtitle}</p>', unsafe_allow_html=True)

    # Sidebar controls
    with st.sidebar:
        st.header("Research")
        
        # Use columns for search type and time range outside the form
        col1, col2 = st.columns([3, 2])
        with col1:
            search_type = st.selectbox(
                "Type",
                ["Headlines", "Topic"],
                label_visibility="collapsed"
            )
        with col2:
            time_range = st.selectbox(
                "Time",
                ["1h", "3h", "4h", "6h", "12h", "24h", "2d", "3d", "5d", "7d","14d","30d","60d","90d","180d","1y","2y","3yr"],
                index=5,
                label_visibility="collapsed"
            )
            st.session_state.time_range = time_range
        
        # Show topic input field immediately if Topic is selected
        topic = None
        if search_type == "Topic":
            if 'last_topic' not in st.session_state:
                st.session_state.last_topic = ''
            
            topic = st.text_input(
                "Topic",
                placeholder="Enter topic...",
                key="topic_input"
            )
            
            if topic and topic != st.session_state.last_topic:
                st.session_state.last_topic = topic
                st.session_state.topic = topic
                
                # Clear session state and fetch news
                for key in list(st.session_state.keys()):
                    if key not in ['topic', 'time_range', 'last_topic']:
                        del st.session_state[key]
                
                with st.spinner("Fetching news..."):
                    news_data = get_news_data("Topic", query=topic, when=time_range)
                    if news_data and 'clusters' in news_data:
                        st.session_state.news_data = news_data
                        st.session_state.is_loading_clusters = True
                        st.session_state.clusters = []
                        st.rerun()
        else:
            st.session_state.topic = None
        
        # Search form
        with st.form(key='search_form', clear_on_submit=False):
            submit_button = st.form_submit_button(
                "Search",
                use_container_width=True,
                disabled=(search_type == "Topic" and not topic)
            )
            
            if submit_button:
                # Clear session state and fetch news
                for key in list(st.session_state.keys()):
                    if key not in ['topic', 'time_range', 'last_topic']:
                        del st.session_state[key]
                
                with st.spinner("Fetching news..."):
                    if search_type == "Headlines":
                        news_data = get_news_data("Headlines", when=time_range)
                    else:
                        news_data = get_news_data("Topic", query=topic, when=time_range)
                    
                    if news_data and 'clusters' in news_data:
                        st.session_state.news_data = news_data
                        st.session_state.is_loading_clusters = True
                        st.session_state.clusters = []
                        st.rerun()

        # Latest Headlines section
        st.markdown("""
            <div class="latest-headlines">
                Published Headlines
            </div>
        """, unsafe_allow_html=True)
        
        # Fetch and display headlines
        headlines = fetch_latest_headlines()
        if headlines:
            category_counts = get_category_counts(headlines)
            category_options = ["All Categories"] + [cat for cat, _ in category_counts]
            
            # Get the current category from session state
            current_category = st.session_state.get('selected_category', 'All Categories')
            
            # Ensure the category exists in options, fallback to "All Categories" if not
            if current_category not in category_options:
                current_category = "All Categories"
                st.session_state.selected_category = current_category
            
            # Find the index of the current category
            category_index = category_options.index(current_category)
            
            selected_category = st.selectbox(
                "Filter by Category",
                category_options,
                index=category_index,
                format_func=lambda x: f"{x} ({dict(category_counts).get(x, len(headlines)) if x != 'All Categories' else len(headlines)})",
                label_visibility="collapsed"
            )
            
            # Get topic filter from session state
            topic_filter = st.session_state.get('topic')
            if topic_filter and topic_filter.strip():  # Only apply filter if topic has content
                topic_filter = topic_filter.strip()
            else:
                topic_filter = None  # Default to None for no filtering
            
            # Display headlines with both category and topic filtering
            headlines_html, total_pages = format_latest_headlines(
                headlines, 
                selected_category, 
                st.session_state.headline_page,
                topic_filter=topic_filter
            )
            
            # Update session state when category changes manually
            if selected_category != st.session_state.get('selected_category'):
                st.session_state.selected_category = selected_category
                st.session_state.headline_page = 1
                st.rerun()
            
            # Initialize page number
            if 'headline_page' not in st.session_state:
                st.session_state.headline_page = 1
            
            # Display headlines
            st.markdown(headlines_html, unsafe_allow_html=True)
            
            # Pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])

            col1.write("")
            if col1.button("←", use_container_width=True, disabled=st.session_state.headline_page <= 1):
                st.session_state.headline_page -= 1
                st.rerun()

            # Create a container for the page number
            with col2.container():
                st.write("")
                st.markdown(
                    f'<div style="text-align: center; color: rgba(255,255,255,0.8);">'
                    f'Page {st.session_state.headline_page} of {total_pages}'
                    f'</div>',
                    unsafe_allow_html=True
                )

            col3.write("")
            if col3.button("→", use_container_width=True, disabled=st.session_state.headline_page >= total_pages):
                st.session_state.headline_page += 1
                st.rerun()

    # Main content area
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if 'is_loading_clusters' not in st.session_state:
            st.session_state.is_loading_clusters = False
            
        if st.session_state.is_loading_clusters:
            with st.spinner("Processing news clusters..."):
                if 'news_data' in st.session_state:
                    clusters = []
                    valid_clusters = [c for c in st.session_state.news_data.get('clusters', []) 
                                    if len(c.get('articles', [])) >= 3]
                    total_clusters = len(valid_clusters)
                    
                    if total_clusters > 0:
                        st.write(f"Found {total_clusters} clusters to analyze")
                        progress_bar = st.progress(0)
                        
                        for idx, cluster in enumerate(valid_clusters):
                            progress = (idx) / total_clusters
                            progress_bar.progress(progress)
                            
                            analysis = analyze_cluster(cluster)
                            if analysis:
                                clusters.append({
                                    'category': analysis.get('category', 'Unknown'),
                                    'subject': analysis.get('subject', 'Unknown'),
                                    'bias': analysis.get('bias', 0.0),
                                    'cluster_size': len(cluster.get('articles', [])),
                                    'articles': cluster.get('articles', [])
                                })
                        
                        progress_bar.progress(1.0)
                        st.write(f"Analysis complete! Found {len(clusters)} valid clusters")
                    else:
                        st.warning("No clusters with 3 or more articles found")
                    
                    st.session_state.clusters = clusters
                    st.session_state.is_loading_clusters = False
                    del st.session_state.news_data
                    st.rerun()
        
        elif st.session_state.clusters:
            # Get unique categories from the clusters
            categories = list(set(cluster['category'] for cluster in st.session_state.clusters))
            categories.insert(0, "All Categories")

            # Add category filter dropdown
            selected_category = st.selectbox(
                "Filter by Category",
                categories,
                key="category_filter",
                index=0
            )

            # Display clusters
            filtered_clusters = [
                cluster for cluster in st.session_state.clusters
                if selected_category == "All Categories" or cluster['category'] == selected_category
            ]

            for i, cluster in enumerate(filtered_clusters):
                is_evaluating = (hasattr(st.session_state, 'evaluating_cluster') and 
                                st.session_state.evaluating_cluster == i and 
                                not hasattr(st.session_state, 'article_rejected'))
                opacity = "1" if is_evaluating or not hasattr(st.session_state, 'evaluating_cluster') else "1"
                
                st.markdown(
                    f"""
                    <div style="opacity: {opacity}; padding: 1rem; border: 1px solid rgba(74, 111, 165, 0.1); border-radius: 8px; margin-bottom: 0.75rem; background-color: #1C1C1C;">
                        <div style="font-weight: 500; font-size: 1em; margin-bottom: 0.5rem; color: rgba(255, 255, 255, 0.95);">
                            {cluster['subject']}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <div style="color: rgba(192, 160, 128, 0.95); font-size: 0.85em;">
                                {cluster['category']}
                            </div>
                            <div style="color: rgba(255, 255, 255, 0.8); font-size: 0.9em;">
                                Articles: {cluster['cluster_size']}
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; width: 100%; padding: 4px 0;">
                            <div style="flex: 1;">{create_custom_progress_bar(cluster.get('bias', 0), i)}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                if st.button("Evaluate Sources", key=f"eval_cluster_{i}"):
                    st.session_state.evaluating_cluster = i
                    
                    # Create a placeholder for the loading animation
                    with col2:
                        loading_placeholder = st.empty()
                        with loading_placeholder.container():
                            st.markdown("""
                                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; background: rgba(74, 111, 165, 0.05); border-radius: 8px; padding: 2rem;">
                                    <div style="color: #4A6FA5; font-size: 1.2rem; margin-bottom: 1rem;">
                                        Analyzing Sources & Generating Article
                                    </div>
                                    <div class="stProgress">
                                        <div style="width: 100%; height: 4px; background: #f0f2f6; border-radius: 2px; overflow: hidden;">
                                            <div style="width: 30%; height: 100%; background: #4A6FA5; border-radius: 2px; animation: loading 1.5s infinite ease-in-out;">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <style>
                                    @keyframes loading {
                                        0% { transform: translateX(-100%); }
                                        100% { transform: translateX(200%); }
                                    }
                                    .stProgress {
                                        width: 200px;
                                    }
                                </style>
                            """, unsafe_allow_html=True)
                            
                            # Add source information
                            st.markdown(f"""
                                <div style="margin-top: 1rem; text-align: center; color: rgba(74, 111, 165, 0.7);">
                                    Processing {len(cluster.get('articles', []))} source articles
                                </div>
                            """, unsafe_allow_html=True)
                    
                    # Generate the article
                    with st.spinner():
                        try:
                            article_data = create_article(cluster)
                            if article_data:
                                st.session_state.selected_cluster = cluster
                                st.session_state.article_data = article_data
                                st.session_state.current_step = 1
                                st.session_state.clusters.pop(i)
                                st.session_state.evaluating_cluster = None
                                
                                # Clear the loading animation
                                loading_placeholder.empty()
                                
                                st.rerun()
                            else:
                                raise ValueError("Empty article data returned from create_article")
                        except Exception as e:
                            # Show error in the loading placeholder
                            with loading_placeholder.container():
                                st.error(f"Failed to generate article. Error: {str(e)}")
                                time.sleep(60)  # Show error for 1 minute
                                st.session_state.evaluating_cluster = None
                                st.rerun()

    with col2:
        if st.session_state.selected_cluster and st.session_state.article_data:
            if st.session_state.current_step == 1:
                display_article_step()
            elif st.session_state.current_step == 2:
                display_review_step()
            elif st.session_state.current_step == 3:
                display_image_step()
            else:
                display_final_review()

if __name__ == "__main__":
    main() 