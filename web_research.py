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
import pandas as pd
import plotly.express as px
from chat_codegpt import chat_with_codegpt
import requests
import json
from dotenv import load_dotenv
import os
import time
import math  # Add this import
from review_articles import evaluate_article_with_ai, display_evaluation
from publish_utils import generate_and_encode_images, publish_article
import logging
import http.client as http_client
import urllib3

load_dotenv()
API_KEY = os.environ.get("NEWSCATCHER_API_KEY")

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
    
    # Add this line to clear the article rejection state
    if hasattr(st.session_state, 'article_rejected'):
        del st.session_state.article_rejected

def get_news_data(search_type, query="", when="24h"):
    """Fetch news data from NewsCatcher API"""
    # Convert time range to API format only when sending to API
    time_mapping = {
        "1h": "1h",
        "3h": "3h",
        "4h": "4h",
        "6h": "6h",
        "12h": "12h",
        "24h": "1d",
        "2d": "2d",
        "3d": "3d",
        "5d": "5d",
        "7d": "7d"
    }
    api_time = time_mapping.get(when, "1d")  # Default to 1 day if unknown format
    
    if search_type == "Headlines":
        url = "https://v3-api.newscatcherapi.com/api/latest_headlines"
        params = {
            "when": api_time,
            "countries": "US, CA, MX, GB",
            "predefined_sources": "top 80 US,top 50 CA,top 20 MX,top 20 GB",
            "lang": "en",
            "ranked_only": "true",
            "clustering_enabled": "true",
            "clustering_threshold": "0.8",
            "page_size": "800"
        }
    else:
        url = "https://v3-api.newscatcherapi.com/api/search"
        params = {
            "q": query,
            "from_": api_time,
            "countries": "US, CA, MX, GB",
            "lang": "en",
            "ranked_only": "true",
            "clustering_enabled": "true",
            "page_size": "100"
        }

    headers = {"x-api-token": API_KEY}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
        return None

def analyze_cluster(cluster):
    """Analyze a single cluster using CodeGPT"""
    titles = [article['title'] for article in cluster.get('articles', [])]
    sources = [article.get('name_source', 'Unknown') for article in cluster.get('articles', [])]
    
    prompt = f"""Analyze these news headlines and their sources:
    Headlines: {json.dumps(titles, indent=2)}
    Sources: {json.dumps(sources, indent=2)}
    
    Determine the common topic, categorize it, identify the main subject, and assess the overall political bias.
    Return a JSON object with the structure: {{"category": "Category name", "subject": "Main subject or focus", "bias": number}}
    The bias should be a number between -1 and 1, where -1 is extremely left-leaning and 1 is extremely right-leaning."""
    
    analysis = chat_with_codegpt(prompt)
    try:
        result = json.loads(analysis)
        # Ensure bias is a float
        result['bias'] = float(result.get('bias', 0))
        return result
    except:
        return {"category": "Unknown", "subject": "Unknown", "bias": 0.0}

def create_article(cluster):
    """Generate article from cluster using CodeGPT"""
    articles_data = []
    for article in cluster['articles'][:8]:  # Limit to 8 articles
        articles_data.append({
            "title": article.get('title', ''),
            "content": article.get('content', ''),
            "name_source": article.get('name_source', ''),
            "link": article.get('link', '')
        })

    prompt = f"""Create an article based on these sources. Include a headline, haiku, full story, and a one-paragraph summary.
    The story should be in HTML format.
    
    Sources: {json.dumps(articles_data, indent=2)}"""

    article_json = chat_with_codegpt(prompt)
    try:
        return json.loads(article_json)
    except:
        st.error("Failed to generate article")
        return None

def review_article(article_data):
    """Review article using AI evaluation"""
    if not article_data:
        st.error("No article data available for review")
        return None
    
    # Format citations from source articles
    if st.session_state.selected_cluster:
        sources = []
        for i, article in enumerate(st.session_state.selected_cluster['articles'][:8], 1):
            sources.append([i, article['link']])
        cited = json.dumps(sources)
    else:
        cited = "[]"
        
    article = {
        'ID': 'DRAFT',
        'AIHeadline': article_data.get('headline', ''),
        'AIStory': article_data.get('story', ''),
        'cat': article_data.get('cat', ''),
        'topic': article_data.get('topic', ''),
        'bs': article_data.get('bs', ''),
        'Cited': cited  # Add citations
    }
    
    try:
        evaluation = evaluate_article_with_ai(article)
        if not evaluation:
            st.error("AI evaluation returned no results")
            return None
            
        # Ensure required fields exist
        evaluation = {
            'quality_score': evaluation.get('quality_score', 0),
            'cat': evaluation.get('cat', 'Unknown'),
            'bs_p': evaluation.get('bs_p', 'Neutral'),
            'reasoning': evaluation.get('reasoning', 'No analysis provided'),
            'topic': evaluation.get('topic', 'Unknown'),
            'trend': evaluation.get('trend', 0.0)  # Add trend score to preserved fields
        }
        return evaluation
        
    except Exception as e:
        st.error(f"AI Evaluation failed: {str(e)}")
        return None

def generate_haiku_images(haiku, headline, date=''):
    """Generate and encode haiku images"""
    try:
        image_data, image_haiku = generate_and_encode_images(haiku, headline, date)
        return image_data, image_haiku
    except Exception as e:
        st.error(f"Image generation failed: {str(e)}")
        return None, None

def display_evaluation_results():
    """Display AI evaluation results in a clean format"""
    eval_data = st.session_state.evaluation
    
    if not eval_data:
        st.error("No evaluation data available")
        return
    
    try:
        # Add CSS for centered metrics and layout
        st.markdown("""
            <style>
                div[data-testid="metric-container"] {
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 1rem;
                    text-align: center !important;
                    margin-bottom: 0.5rem;
                }
                
                div[data-testid="metric-container"] > div {
                    width: 100%;
                }
                
                div[data-testid="metric-container"] label {
                    display: block;
                    text-align: center;
                    color: #444;
                    font-weight: 500;
                }
                
                div[data-testid="metric-container"] div[data-testid="metric-value"] {
                    text-align: center;
                    font-size: 1.2rem !important;
                }
                
                .metrics-stack {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }

                /* Custom tab styling */
                .stTabs [data-baseweb="tab-list"] {
                    gap: 8px;
                    margin-bottom: 0.5rem;
                }

                .stTabs [data-baseweb="tab"] {
                    padding: 0.5rem 1rem;
                    background-color: #f8f9fa;
                    border-radius: 4px;
                }

                .stTabs [data-baseweb="tab-highlight"] {
                    background-color: var(--primary-color);
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Category row
        category = eval_data.get('cat', 'Unknown')
        st.metric("Category", category)
        
        # Create two columns for Analysis and Metrics
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # AI Analysis expander (expanded by default)
            st.markdown("""
                <style>
                    /* Hide the collapse arrow for this specific expander */
                    [data-testid="stExpander"] div[role="button"] svg {
                        display: none;
                    }
                    /* Remove hover effect and cursor pointer */
                    [data-testid="stExpander"] div[role="button"] {
                        pointer-events: none;
                    }
                    /* Maintain consistent background */
                    [data-testid="stExpander"] div[role="button"]:hover {
                        background-color: transparent;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # Create tabs for different analysis aspects
            quality_tab, bias_tab, prop_tab = st.tabs([
                 "Quality", "Bias", "Propagation"
            ])
            
            with quality_tab:
                quality_score = eval_data.get('quality_score', 0)
                try:
                    quality_score = float(quality_score)
                except (ValueError, TypeError):
                    quality_score = 0.0
                
                st.markdown(f"""
                    ### Quality Assessment Score: {quality_score:.1f}/10
                    
                    The quality score evaluates the article based on:
                    - Writing clarity and coherence
                    - Source diversity and reliability
                    - Factual accuracy and completeness
                    - Balanced presentation
                """)
            
            with bias_tab:
                bias_score = eval_data.get('bs_p', 'Neutral')
                bias_mapping = {
                    'Far Left': -1.0,
                    'Left': -0.6,
                    'Center Left': -0.3,
                    'Neutral': 0.0,
                    'Center Right': 0.3,
                    'Right': 0.6,
                    'Far Right': 1.0
                }
                numeric_bias = bias_mapping.get(bias_score, 0.0)
                bias_color = get_bias_color(numeric_bias)
                
                st.markdown(f"""
                    ### Bias Assessment: {bias_score}
                    
                    The bias score indicates the article's political leaning:
                    - Far Left (-1.0) to Far Right (1.0)
                    - Current score indicates {bias_score} bias
                    - Based on source analysis and content evaluation
                """)
            
            with prop_tab:
                trend_score = eval_data.get('trend', 0.0)
                if isinstance(trend_score, str):
                    try:
                        trend_score = float(trend_score)
                    except (ValueError, TypeError):
                        trend_score = 0.0
                
                st.markdown(f"""
                    ### Propagation Index: {trend_score:.1f}/10
                    
                    The propagation index measures:
                    - Topic relevance and timeliness
                    - Public interest potential
                    - Information spread patterns
                    - Content accessibility
                """)
        
        with col2:
            # Metrics stack
            quality_score = eval_data.get('quality_score', 0)
            try:
                quality_score = float(quality_score)
            except (ValueError, TypeError):
                quality_score = 0.0
            st.metric("Quality Score", f"{quality_score:.1f}/10")
            
            bias_score = eval_data.get('bs_p', 'Neutral')
            try:
                # Convert text bias to numeric value
                bias_mapping = {
                    'Far Left': -1.0,
                    'Left': -0.6,
                    'Center Left': -0.3,
                    'Neutral': 0.0,
                    'Center Right': 0.3,
                    'Right': 0.6,
                    'Far Right': 1.0
                }
                numeric_bias = bias_mapping.get(bias_score, 0.0)
                bias_color = get_bias_color(numeric_bias)
                
                # Add custom styling for bias metric
                st.markdown(f"""
                    <style>
                        [data-testid="metric-container"]:nth-of-type(3) {{
                            background: linear-gradient(to right, {bias_color}22, {bias_color}44) !important;
                            border-color: {bias_color} !important;
                        }}
                        [data-testid="metric-container"]:nth-of-type(3) [data-testid="metric-value"] {{
                            color: {bias_color} !important;
                        }}
                    </style>
                """, unsafe_allow_html=True)
                
                st.metric("Bias Score", bias_score)
            except Exception as e:
                st.metric("Bias Score", bias_score)
            
            trend_score = eval_data.get('trend')
            try:
                trend_score = float(trend_score)
            except (ValueError, TypeError):
                trend_score = 0.0
            st.metric("Propagation Index", f"{trend_score:.1f}/10")
    
    except Exception as e:
        st.error(f"Error displaying evaluation results: {str(e)}")

def display_article_step():
    """Display the generated article content"""
    # Header section with reduced spacing
    st.markdown(f"""
        <div style="margin-bottom: 0.5rem;">
            <h2 style="margin: 0;">{st.session_state.article_data['headline']}</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Navigation controls
    if st.button("Continue to Review", key="continue_review"):
        with st.spinner("Running AI review..."):
            evaluation = review_article(st.session_state.article_data)
            if evaluation:
                st.session_state.evaluation = evaluation
                st.session_state.current_step = 2
                st.rerun()
    
    # Group sources by domain/publisher
    source_groups = {}
    for article in st.session_state.selected_cluster['articles']:
        source = article['name_source']
        if source in source_groups:
            source_groups[source] += 1
        else:
            source_groups[source] = 1
    
    # Sort sources by frequency
    sorted_sources = sorted(source_groups.items(), key=lambda x: x[1], reverse=True)
    
    # Display source tags without redefining styles
    st.markdown('<div class="source-tags">', unsafe_allow_html=True)
    
    # Generate tag HTML
    tags_html = ""
    for source, count in sorted_sources:
        tags_html += f"""
        <div class="source-tag">
            {source}
            <span class="source-count">{count}</span>
        </div>
        """
    st.markdown(tags_html + "</div>", unsafe_allow_html=True)
    
    # Main content - swapped columns with adjusted ratio and styling
    col1, col2 = st.columns([1.2, 2.6])  # Adjusted ratio to give haiku more width
    
    with col1:
        haiku_lines = st.session_state.article_data['haiku'].split('\n')
        st.markdown("""
            <style>
                .haiku-container {
                    background-color: #f8f9fa;
                    border: 1px solid rgba(74, 111, 165, 0.1);
                    border-radius: 8px;
                    padding: 1rem;
                    margin-top: 0.5rem;
                    width: 100%;
                    box-sizing: border-box;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }
                .haiku-title {
                    font-size: 1rem;
                    color: #4a6fa5;
                    margin-bottom: 0.75rem;
                    font-weight: 500;
                }
                .haiku-text {
                    font-size: 0.95rem;
                    font-style: italic;
                    color: #2c3e50;
                    line-height: 1.5;
                    text-align: center;
                    white-space: nowrap;
                    overflow-x: auto;
                    max-width: 100%;
                    scrollbar-width: none;
                    -ms-overflow-style: none;
                }
                .haiku-text::-webkit-scrollbar {
                    display: none;
                }
                .haiku-line {
                    white-space: nowrap;
                    margin: 0.2rem 0;
                }
                /* Responsive font sizing with more breakpoints */
                @media (max-width: 1400px) {
                    .haiku-text {
                        font-size: 0.9rem;
                    }
                }
                @media (max-width: 1200px) {
                    .haiku-text {
                        font-size: 0.85rem;
                    }
                }
                @media (max-width: 992px) {
                    .haiku-text {
                        font-size: 0.8rem;
                    }
                }
                @media (max-width: 768px) {
                    .haiku-text {
                        font-size: 0.75rem;
                    }
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Then add the content with the haiku
        st.markdown(f"""
            <div class="haiku-container">
                <div class="haiku-title">Haiku</div>
                <div class="haiku-text">
                    <div class="haiku-line">{haiku_lines[0].strip()}</div>
                    <div class="haiku-line">{haiku_lines[1].strip()}</div>
                    <div class="haiku-line">{haiku_lines[2].strip()}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Add container styling to ensure proper spacing
        st.markdown("""
            <style>
                .summary-container {
                    margin-left: 1rem;
                    padding-left: 1rem;
                    border-left: 1px solid rgba(74, 111, 165, 0.1);
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="summary-container">', unsafe_allow_html=True)
        st.markdown("#### Summary")
        st.markdown(st.session_state.article_data['summary'])
        
        with st.expander("Full Story", expanded=False):
            st.markdown(st.session_state.article_data['story'], unsafe_allow_html=True)
            
        with st.expander("Source Articles", expanded=False):
            for article in st.session_state.selected_cluster['articles']:
                st.markdown(f"- [{article['title']}]({article['link']}) - {article['name_source']}")
        st.markdown('</div>', unsafe_allow_html=True)

def display_review_step():
    """Display the AI review results and article content"""
    # Header section
    st.subheader(st.session_state.article_data['headline'])
    
    # Navigation controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Accept and Continue", key="review_accept"):
            # Format citations
            sources = []
            for i, article in enumerate(st.session_state.selected_cluster['articles'][:8], 1):
                sources.append([i, article['link']])
            
            # Create publish data first
            st.session_state.publish_data = {
                "AIHeadline": st.session_state.article_data['headline'],
                "AIHaiku": st.session_state.article_data['haiku'],
                "AIStory": st.session_state.article_data['story'],
                "AISummary": st.session_state.article_data['summary'],
                "bs": f"{st.session_state.selected_cluster['category']} | High Confidence | {st.session_state.selected_cluster['subject']}",
                "topic": st.session_state.evaluation.get('topic', st.session_state.selected_cluster['category']),
                "cat": st.session_state.evaluation.get('cat', st.session_state.selected_cluster['subject']),
                "bs_p": st.session_state.evaluation.get('bs_p', ''),
                "qas": st.session_state.evaluation.get('quality_score', ''),
                "Cited": json.dumps(sources)
            }
            
            # Separate spinner just for image generation
            with st.spinner("Generating haiku image..."):
                try:
                    # Generate haiku image with explicit timeout
                    image_data, image_haiku = generate_haiku_images(
                        st.session_state.article_data['haiku'],
                        st.session_state.article_data['headline']
                    )
                    
                    if not image_data or not image_haiku:
                        st.error("Failed to generate image - please try again")
                        return
                    
                    # Store image data in session state
                    st.session_state.haiku_image = image_haiku
                    st.session_state.publish_data.update({
                        'image_data': image_data,
                        'image_haiku': image_haiku
                    })
                    
                    # Save to file
                    with open('publish.json', 'w') as f:
                        json.dump(st.session_state.publish_data, f, indent=2)
                    
                    # Only proceed if image generation was successful
                    st.session_state.current_step = 3
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error generating image: {str(e)}")
                    return
    with col2:
        if st.button("Reject Article", key="review_reject_step"):
            st.session_state.article_rejected = True
            reset_article_state()
            st.rerun()
    
    # Create tabs for different analysis aspects
    quality_score = st.session_state.evaluation.get('quality_score', 0)
    try:
        quality_score = float(quality_score)
    except (ValueError, TypeError):
        quality_score = 0.0
        
    bias_score = st.session_state.evaluation.get('bs_p', 'Neutral')
    
    trend_score = st.session_state.evaluation.get('trend', 0.0)
    if isinstance(trend_score, str):
        try:
            trend_score = float(trend_score)
        except (ValueError, TypeError):
            trend_score = 0.0
    
    quality_tab, bias_tab, prop_tab, content_tab = st.tabs([
        f"Quality ({quality_score:.1f})",
        f"Bias ({bias_score})",
        f"Propagation ({trend_score:.1f})",
        "Article Content"
    ])
    
    with quality_tab:
        quality_score = st.session_state.evaluation.get('quality_score', 0)
        try:
            quality_score = float(quality_score)
        except (ValueError, TypeError):
            quality_score = 0.0
        
        # Parse quality-related content from reasoning
        reasoning = st.session_state.evaluation.get('reasoning', '')
        quality_analysis = ""
        
        # Look for the Quality Analysis section
        if "Quality Analysis:" in reasoning:
            sections = reasoning.split("Quality Analysis:")
            if len(sections) > 1:
                quality_section = sections[1].split("Bias Analysis:")[0].strip()
                quality_analysis = quality_section
        
        if not quality_analysis:
            quality_analysis = """
                The quality score evaluates the article based on:
                - Writing clarity and coherence
                - Source diversity and reliability
                - Factual accuracy and completeness
                - Balanced presentation
            """
        
        st.markdown(f"""
            ### Quality Assessment Score: {quality_score:.1f}/10
            
            {quality_analysis}
        """)
    
    with bias_tab:
        bias_score = st.session_state.evaluation.get('bs_p', 'Neutral')
        
        # Parse bias-related content from reasoning
        bias_analysis = ""
        
        # Look for the Bias Analysis section
        if "Bias Analysis:" in reasoning:
            sections = reasoning.split("Bias Analysis:")
            if len(sections) > 1:
                bias_section = sections[1].split("Viral Potential:")[0].strip()
                bias_analysis = bias_section
        
        if not bias_analysis:
            bias_analysis = f"""
                The bias score indicates {bias_score} political leaning:
                - Based on source analysis and content evaluation
                - Considers perspective balance
                - Evaluates partisan language
            """
        
        st.markdown(f"""
            ### Bias Assessment: {bias_score}
            
            {bias_analysis}
        """)
    
    with prop_tab:
        trend_score = st.session_state.evaluation.get('trend', 0.0)
        if isinstance(trend_score, str):
            try:
                trend_score = float(trend_score)
            except (ValueError, TypeError):
                trend_score = 0.0
        
        # Parse propagation-related content from reasoning
        prop_analysis = ""
        
        # Look for the Viral Potential section
        if "Viral Potential:" in reasoning:
            sections = reasoning.split("Viral Potential:")
            if len(sections) > 1:
                prop_section = sections[1].strip()
                prop_analysis = prop_section
        
        if not prop_analysis:
            prop_analysis = f"""
                The propagation index measures:
                - Topic relevance and timeliness
                - Public interest potential
                - Information spread patterns
                - Content accessibility
            """
        
        st.markdown(f"""
            ### Propagation Index: {trend_score:.1f}/10
            
            {prop_analysis}
        """)
    
    with content_tab:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### Summary")
            st.markdown(st.session_state.article_data['summary'])
            
            with st.expander("Full Story", expanded=False):
                st.markdown(st.session_state.article_data['story'], unsafe_allow_html=True)
        
        with col2:
            # Haiku style
            st.markdown("""
                <style>
                    .haiku-container {
                        background-color: #f8f9fa;
                        border: 1px solid rgba(74, 111, 165, 0.1);
                        border-radius: 8px;
                        padding: 1rem;
                        margin-top: 0.5rem;
                        display: inline-block;
                        width: auto;
                    }
                    .haiku-title {
                        font-size: 1rem;
                        color: #4a6fa5;
                        margin-bottom: 0.75rem;
                        font-weight: 500;
                    }
                    .haiku-text {
                        font-size: 0.9rem;
                        font-style: italic;
                        color: #2c3e50;
                        line-height: 1.5;
                        white-space: nowrap;
                    }
                    
                    /* Source tags styling */
                    .source-tags {
                        display: flex;
                        flex-wrap: wrap;
                        gap: 8px;
                        margin: 1rem 0;
                    }
                    .source-tag {
                        background-color: rgba(74, 111, 165, 0.1);
                        border: 1px solid rgba(74, 111, 165, 0.3);
                        border-radius: 16px;
                        padding: 4px 12px;
                        font-size: 0.9em;
                        color: #4a6fa5;
                        display: inline-flex;
                        align-items: center;
                        gap: 6px;
                    }
                    .source-count {
                        background-color: rgba(74, 111, 165, 0.2);
                        border-radius: 50%;
                        width: 20px;
                        height: 20px;
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 0.8em;
                        font-weight: 500;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # Haiku content
            haiku_lines = st.session_state.article_data['haiku'].split('\n')
            st.markdown(f"""
                <div class="haiku-container">
                    <div class="haiku-title">Haiku</div>
                    <div class="haiku-text">
                        {haiku_lines[0].strip()}<br>
                        {haiku_lines[1].strip()}<br>
                        {haiku_lines[2].strip()}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Group sources by domain/publisher
            source_groups = {}
            for article in st.session_state.selected_cluster['articles']:
                source = article['name_source']
                if source in source_groups:
                    source_groups[source] += 1
                else:
                    source_groups[source] = 1
            
            # Sort sources by frequency
            sorted_sources = sorted(source_groups.items(), key=lambda x: x[1], reverse=True)
            
            # Generate source tags HTML
            tags_html = '<div class="source-tags">'
            for source, count in sorted_sources:
                tags_html += f"""
<div class="source-tag">
    {source}
    <span class="source-count">{count}</span>
</div>
                """
            tags_html += "</div>"
            
            st.markdown(tags_html, unsafe_allow_html=True)
            
            # Source links in expander
            with st.expander("Source Links", expanded=False):
                for article in st.session_state.selected_cluster['articles']:
                    st.markdown(f"- [{article['title']}]({article['link']})")

def display_image_step():
    """Display the haiku image generation step"""
    if not st.session_state.publish_data:
        st.error("No publication data available for image generation")
        reset_article_state()
        return
    
    # Header section
    st.subheader(st.session_state.publish_data.get('AIHeadline', ''))
    
    # Navigation controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Regenerate Image"):
            with st.spinner("Generating new image..."):
                image_data, image_haiku = generate_haiku_images(
                    st.session_state.publish_data.get('AIHaiku', ''),
                    st.session_state.publish_data.get('AIHeadline', '')
                )
                if image_data and image_haiku:
                    # Update both session state and publish data
                    st.session_state.haiku_image = image_haiku
                    st.session_state.publish_data.update({
                        'image_data': image_data,
                        'image_haiku': image_haiku
                    })
                    # Save updated publish data to file
                    with open('publish.json', 'w') as f:
                        json.dump(st.session_state.publish_data, f, indent=2)
                    st.rerun()
                else:
                    st.error("Failed to generate new image")
    with col2:
        if st.button("Continue to Final Review", key="image_continue_review"):
            st.session_state.current_step = 4
            st.rerun()
    
    
    # Main content
    st.markdown("#### Haiku Visualization")
    if st.session_state.haiku_image is None:
        with st.spinner("Generating initial haiku image..."):
            image_data, image_haiku = generate_haiku_images(
                st.session_state.publish_data.get('AIHaiku', ''),
                st.session_state.publish_data.get('AIHeadline', '')
            )
            if image_data and image_haiku:
                st.session_state.haiku_image = image_haiku
                st.session_state.publish_data.update({
                    'image_data': image_data,
                    'image_haiku': image_haiku
                })
                st.rerun()
            else:
                st.error("Failed to generate haiku image")
    else:
        container_style = """
            <style>
                [data-testid="stImage"] {
                    width: 70%;
                    margin: 0 auto;
                    display: block;
                }
                [data-testid="stImage"] img {
                    border-radius: 8px;
                }
            </style>
        """
        st.markdown(container_style, unsafe_allow_html=True)
        st.image(st.session_state.haiku_image, caption="Generated Haiku Image", use_container_width=False)

def display_final_review():
    """Display final review before publication"""
    if not st.session_state.publish_data:
        st.error("No publication data available")
        reset_article_state()
        return
    
    # Header section
    st.subheader(st.session_state.publish_data.get('AIHeadline', ''))
    
    # Navigation controls
    col1, col2 = st.columns(2)
    with col1:
        # Check if article has already been published
        is_published = hasattr(st.session_state, 'publication_success') and st.session_state.publication_success
        
        # Create publish button with disabled state based on publication status
        if st.button("Publish Article", 
                    key="final_review_publish", 
                    disabled=is_published):
            with st.spinner("Publishing article..."):
                article_id = publish_article(
                    st.session_state.publish_data,
                    os.environ.get("PUBLISH_API_KEY")
                )
                if article_id:
                    st.session_state.publication_success = True
                    st.session_state.published_article_id = article_id
                    st.session_state.published_article_url = f"https://ainewsbrew.com/article/{article_id}"
                    st.success(f"""Article published successfully! 
                        \nID: {article_id}
                        \nView at: [{st.session_state.published_article_url}]({st.session_state.published_article_url})""")
                    st.rerun()  # Rerun to update button state
    
    try:
        
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("### Article Content")
            st.markdown(f"**Headline:** {st.session_state.publish_data.get('AIHeadline', 'No headline')}")
            st.markdown(f"**Category:** {st.session_state.publish_data.get('cat', 'No category')}")
            st.markdown(f"**Topic:** {st.session_state.publish_data.get('topic', 'No topic')}")
            
            # Display haiku image with styling
            if st.session_state.haiku_image is not None:
                st.markdown("""
                    <style>
                        [data-testid="stImage"] {
                            width: 100%;
                            margin: 1rem auto;
                            display: block;
                        }
                        [data-testid="stImage"] img {
                            border-radius: 8px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        }
                    </style>
                """, unsafe_allow_html=True)
                st.image(st.session_state.haiku_image, caption="Haiku Visualization")
            else:
                st.warning("No haiku image available")
            
            st.markdown("**Summary:**")
            st.markdown(st.session_state.publish_data.get('AISummary', 'No summary'))
        
        with col2:
            st.markdown("### Publication Details")
            try:
                quality_score = float(st.session_state.publish_data.get('qas', 0))
                st.metric("Quality Score", f"{quality_score:.1f}/10")
            except (ValueError, TypeError):
                st.metric("Quality Score", "N/A")
            
            st.metric("Bias Score", st.session_state.publish_data.get('bs_p', 'N/A'))
    
    except Exception as e:
        st.error(f"Error displaying final review: {str(e)}")
        reset_article_state()

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
        time_context = f" {st.session_state.time_range}"  # Changed to bullet point
    else:
        time_context = ""
    
    # Get cluster context
    if st.session_state.selected_cluster:
        cluster_context = f"• {st.session_state.selected_cluster['subject']}"
    else:
        cluster_context = ""
    
    # Get step context
    if st.session_state.selected_cluster and hasattr(st.session_state, 'current_step'):
        steps = ["Generate", "Review", "Visualize", "Publish"]
        step_context = f"• Step {st.session_state.current_step}/4: {steps[st.session_state.current_step-1]}"
    else:
        step_context = ""
    
    # Combine contexts
    contexts = [search_context, time_context, cluster_context, step_context]
    subtitle = " ".join(filter(None, contexts))
    
    return base_title, subtitle

def display_publication_success(article_id, article_url):
    """Display the success view after publication"""
    # Clear the layout
    st.empty()
    
    # Success header with custom styling
    st.markdown("""
        <style>
            .success-header {
                color: #28a745;
                text-align: center;
                padding: 2rem 0;
                margin-bottom: 2rem;
            }
            .success-content {
                max-width: 800px;
                margin: 0 auto;
                padding: 2rem;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .success-link {
                text-align: center;
                font-size: 1.2rem;
                margin: 2rem 0;
            }
            .success-icon {
                font-size: 3rem;
                text-align: center;
                margin-bottom: 1rem;
            }
        </style>
        <div class="success-header">
            <div class="success-icon">✅</div>
            <h2>Article Published Successfully!</h2>
        </div>
    """, unsafe_allow_html=True)
    
    # Content container
    st.markdown('<div class="success-content">', unsafe_allow_html=True)
    
    # Article details
    st.markdown(f"**Article ID:** {article_id}")
    st.markdown(f"**Published At:** {article_url}")
    
    # Centered link button
    st.markdown(f"""
        <div class="success-link">
            <a href="{article_url}" target="_blank" style="
                background-color: var(--accent-blue);
                color: white;
                padding: 0.75rem 1.5rem;
                border-radius: 4px;
                text-decoration: none;
                display: inline-block;
                transition: all 0.2s;
            ">View Published Article</a>
        </div>
    """, unsafe_allow_html=True)
    
    # Return to dashboard button
    if st.button("Return to Dashboard", key="return_dashboard"):
        st.session_state.clear()
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

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

def format_latest_headlines(headlines, selected_category=None, page=1, per_page=5):
    """Format headlines with metadata for sidebar display with pagination"""
    # Filter headlines if category is selected
    if selected_category and selected_category != "All Categories":
        filtered_headlines = [h for h in headlines if h.get('cat', '').title() == selected_category]
    else:
        filtered_headlines = headlines
    
    # Paginate filtered headlines
    total_pages = math.ceil(len(filtered_headlines) / per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_headlines = filtered_headlines[start_idx:end_idx]
    
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
                min-width: 0; /* Enable flexbox text truncation */
            }
            .headline-category {
                color: rgba(192, 160, 128, 0.95);
                text-transform: uppercase;
                font-weight: 500;
                font-size: 0.9em;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 80px;
            }
            .headline-topic {
                color: rgba(74, 111, 165, 0.95);
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                flex: 1;
                min-width: 0;
            }
            .headline-date {
                margin-left: auto;
                color: rgba(255, 255, 255, 0.5);
                white-space: nowrap;
                flex-shrink: 0;
            }
            .headline-list {
                margin-top: 0.25rem;
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

def display_wizard_content():
    """Display the wizard content with proper container"""
    if st.session_state.selected_cluster and st.session_state.article_data:
        # Add custom CSS for wizard layout
        # st.markdown("""
        #     <style>
        #         /* Container styles */
        #         [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
        #             background-color: #1E1E1E !important;
        #             border: 1px solid rgba(255,255,255,0.1) !important;
        #             border-radius: 8px !important;
        #             padding: 1rem !important;
        #             color: rgba(255,255,255,0.9) !important;
        #             margin-top: 0 !important;
        #         }
                
        #         /* Text colors for dark theme */
        #         [data-testid="stVerticalBlock"] h1,
        #         [data-testid="stVerticalBlock"] h2,
        #         [data-testid="stVerticalBlock"] h3 {
        #             color: rgba(255,255,255,0.9) !important;
        #         }
                
        #         [data-testid="stVerticalBlock"] p {
        #             color: rgba(255,255,255,0.8) !important;
        #         }
                
        #         /* Progress bar styling */
        #         div[data-testid="stProgress"] {
        #             padding: 0.25rem 0 !important;
        #         }
                
        #         div[data-testid="stProgress"] > div > div {
        #             background-color: var(--accent-blue) !important;
        #         }
                
        #         /* Caption styling */
        #         .caption {
        #             color: rgba(255,255,255,0.7) !important;
        #             margin: 0 0 0.5rem 0 !important;
        #         }
                
        #         /* Button styling */
        #         .stButton > button {
        #             background-color: #2E2E2E !important;
        #             color: rgba(255,255,255,0.9) !important;
        #             border: 1px solid rgba(255,255,255,0.1) !important;
        #         }
                
        #         .stButton > button:hover {
        #             background-color: #3E3E3E !important;
        #             border-color: rgba(255,255,255,0.2) !important;
        #         }
        #     </style>
        # """, unsafe_allow_html=True)
        
        # Use container instead of expander
        with st.container():
            # Display step text before progress bar
            steps = ["Generate", "Review", "Visualize", "Publish"]
            st.caption(f"Step {st.session_state.current_step}/4: {steps[st.session_state.current_step-1]}")
            progress = st.progress(st.session_state.current_step / 4)
            
            # Display appropriate step content
            if st.session_state.current_step == 1:
                display_article_step()
            elif st.session_state.current_step == 2:
                display_review_step()
            elif st.session_state.current_step == 3:
                display_image_step()
            else:
                display_final_review()

def fetch_latest_headlines():
    """Fetch all headlines from the API"""
    try:
        api_key = os.environ.get("PUBLISH_API_KEY")
        http = urllib3.PoolManager()
        
        headers = {
            "X-API-KEY": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        timestamp = int(time.time() * 1000)
        url = f"https://fetch.ainewsbrew.com/api/index_v5.php?mode=latest&timestamp={timestamp}"
        
        response = http.request(
            'GET',
            url,
            headers=headers
        )
        
        # Return all headlines instead of limiting to 10
        return json.loads(response.data.decode('utf-8')) if response.status == 200 else []
        
    except Exception as e:
        st.error(f"Error fetching headlines: {str(e)}")
        return []

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

def format_latest_headlines(headlines, selected_category=None, page=1, per_page=5):
    """Format headlines with metadata for sidebar display with pagination"""
    # Filter headlines if category is selected
    if selected_category and selected_category != "All Categories":
        filtered_headlines = [h for h in headlines if h.get('cat', '').title() == selected_category]
    else:
        filtered_headlines = headlines
    
    # Paginate filtered headlines
    total_pages = math.ceil(len(filtered_headlines) / per_page)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_headlines = filtered_headlines[start_idx:end_idx]
    
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
                min-width: 0; /* Enable flexbox text truncation */
            }
            .headline-category {
                color: rgba(192, 160, 128, 0.95);
                text-transform: uppercase;
                font-weight: 500;
                font-size: 0.9em;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 80px;
            }
            .headline-topic {
                color: rgba(74, 111, 165, 0.95);
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                flex: 1;
                min-width: 0;
            }
            .headline-date {
                margin-left: auto;
                color: rgba(255, 255, 255, 0.5);
                white-space: nowrap;
                flex-shrink: 0;
            }
            .headline-list {
                margin-top: 0.25rem;
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

def main():
    st.set_page_config(layout="wide", page_title="AI News Brew Research")
    
    # Add global styles at the start
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
            
            /* Rest of your existing global styles... */
        </style>
    """, unsafe_allow_html=True)
    
    init_session_state()

    # Add custom CSS for more compact layout
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
                --sidebar-bg-start: #2c3e50;
                --sidebar-bg-end: #34495e;
            }
            
            /* Main container and general styling */
            .main .block-container {
                padding-top: 0.0rem !important;
                padding-bottom: 2rem;
                background-color: var(--primary-bg);
            }
            
            /* Headers styling */
            h1 {
                font-size: 1.5rem !important;
                margin: 0 !important;
                padding: 0 !important;
                line-height: 1.2 !important;
                color: var(--accent-blue);
            }
            
            h2, h3 {
                margin-top: 0;
                margin-bottom: 0.5rem !important;
                padding-top: 0 !important;
                color: var(--text-primary);
            }
            
            /* Metric containers styling */
            div[data-testid="metric-container"] {
                background-color: var(--metric-bg);
                border-radius: 8px;
                padding: 1.2rem;
                text-align: center !important;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                border: 1px solid var(--border-color);
            }
            
            div[data-testid="metric-container"] label {
                color: var(--text-secondary);
                font-weight: 500;
                font-size: 0.9rem;
            }
            
            div[data-testid="metric-container"] div[data-testid="metric-value"] {
                color: var(--accent-blue);
                font-size: 1.3rem !important;
                font-weight: 600;
            }
            
            /* Tabs styling */
            .stTabs [data-baseweb="tab"] {
                color: var(--text-secondary);
            }
            
            .stTabs [data-baseweb="tab-highlight"] {
                background-color: var(--accent-blue);
            }
            
            /* Button styling */
            .stButton > button {
                background-color: var(--accent-blue);
                color: white;
                border: none;
                padding: 0.75rem 1rem;
                border-radius: 4px;
                transition: all 0.2s;
                width: 100%;
                margin: 0.5rem 0;
            }
            
            .stButton > button:hover {
                background-color: #5a7fb5;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            /* Expander styling */
            .streamlit-expanderHeader {
                background-color: var(--secondary-bg);
                border-radius: 4px;
                padding: 0.75rem !important;
                color: var(--text-primary);
            }
            
            /* Progress bar styling */
            .stProgress > div > div {
                background-color: var(--accent-blue);
            }
            
            /* Subtitle styling */
            .subtitle {
                color: var(--text-secondary);
                font-size: 1rem !important;
                margin: 0.2rem 0 0.5rem 0 !important;
                padding: 0 !important;
                line-height: 1.2 !important;
            }
            
            /* Sidebar styling */
            [data-testid="stSidebar"] {
                background: linear-gradient(to right, var(--sidebar-bg-start), var(--sidebar-bg-end));
                border-right: 1px solid rgba(255,255,255,0.1);
            }
            
            [data-testid="stSidebar"] [data-testid="stMarkdown"] {
                color: rgba(255,255,255,0.9);
            }
            
            /* Sidebar header */
            [data-testid="stSidebar"] header {
                background: transparent;
            }
            
            [data-testid="stSidebar"] .sidebar-content h1,
            [data-testid="stSidebar"] .sidebar-content h2,
            [data-testid="stSidebar"] .sidebar-content h3 {
                color: white;
                margin-bottom: 1.5rem;
            }
            
            /* Sidebar radio buttons */
            [data-testid="stSidebar"] .stRadio > label {
                color: rgba(255,255,255,0.9);
            }
            
            [data-testid="stSidebar"] .stRadio [data-testid="stMarkdown"] p {
                color: rgba(255,255,255,0.9);
            }
            
            /* Sidebar form fields */
            [data-testid="stSidebar"] .stTextInput label,
            [data-testid="stSidebar"] .stSelectbox label,
            [data-testid="stSidebar"] .stSlider label {
                color: rgba(255,255,255,0.9) !important;
            }
            
            [data-testid="stSidebar"] .stTextInput input,
            [data-testid="stSidebar"] .stSelectbox select {
                background-color: rgba(255,255,255,0.1);
                color: white;
                border: 1px solid rgba(255,255,255,0.2);
            }
            
            /* Sidebar slider */
            [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {
                margin-top: 1rem;
            }
            
            /* Sidebar form submit button */
            [data-testid="stSidebar"] .stButton > button {
                background: var(--accent-blue);
                color: white;
                border: none;
                width: 100%;
                margin-top: 1rem;
            }
            
            [data-testid="stSidebar"] .stButton > button:hover {
                background: var(--accent-gold);
                color: var(--sidebar-bg-start);
            }

            /* Rest of your existing styles... */
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
                ["1h", "3h", "4h", "6h", "12h", "24h", "2d", "3d", "5d", "7d"],
                index=5,
                label_visibility="collapsed"
            )
            st.session_state.time_range = time_range
        
        # Show topic input field immediately if Topic is selected
        topic = None
        if search_type == "Topic":
            # Add a key to track if Enter was pressed
            if 'last_topic' not in st.session_state:
                st.session_state.last_topic = ''
            
            topic = st.text_input(
                "Topic",
                placeholder="Enter topic...",
                key="topic_input"
            )
            
            # Check if Enter was pressed (topic changed)
            if topic and topic != st.session_state.last_topic:
                st.session_state.last_topic = topic
                st.session_state.topic = topic
                
                # Trigger search automatically
                # Clear all session state except search parameters
                for key in list(st.session_state.keys()):
                    if key not in ['topic', 'time_range', 'last_topic']:
                        del st.session_state[key]
                
                # Fetch news data
                with st.spinner("Fetching news..."):
                    news_data = get_news_data("Topic", query=topic, when=time_range)
                    
                    if news_data and 'clusters' in news_data:
                        st.session_state.news_data = news_data
                        st.session_state.is_loading_clusters = True
                        st.session_state.clusters = []
                        st.rerun()
                    else:
                        st.error("No news data found")
                        st.session_state.clusters = []
                        st.session_state.is_loading_clusters = False
                        if 'news_data' in st.session_state:
                            del st.session_state.news_data
                
                st.rerun()
        else:
            st.session_state.topic = None
        
        # Wrap just the search button in a form for manual triggering
        with st.form(key='search_form', clear_on_submit=False):
            submit_button = st.form_submit_button(
                "Search",
                use_container_width=True,
                disabled=(search_type == "Topic" and not topic)
            )
            
            if submit_button:
                # Clear all session state except search parameters
                for key in list(st.session_state.keys()):
                    if key not in ['topic', 'time_range', 'last_topic']:
                        del st.session_state[key]
                
                # Fetch news data based on search type
                with st.spinner("Fetching news..."):
                    if search_type == "Headlines":
                        news_data = get_news_data("Headlines", when=time_range)
                    else:
                        news_data = get_news_data("Topic", query=topic, when=time_range)
                    
                    if news_data and 'clusters' in news_data:
                        # Store news data and set loading state
                        st.session_state.news_data = news_data
                        st.session_state.is_loading_clusters = True
                        st.session_state.clusters = []  # Clear existing clusters
                        st.rerun()  # Trigger rerun to show loading state
                    else:
                        st.error("No news data found")
                        st.session_state.clusters = []
                        st.session_state.is_loading_clusters = False
                        if 'news_data' in st.session_state:
                            del st.session_state.news_data
                
                st.rerun()

        # Add Latest Headlines section after the search form
        st.markdown("""
            <style>
                .latest-headlines {
                    margin-top: 0em;
                    padding: 0;
                }
                .latest-headlines h4 {
                    color: var(--text-color);
                    margin-bottom: 0.25rem;  /* Reduced from 0.5rem */
                    font-size: 1.0em;        /* Slightly smaller header */
                    opacity: 0.8;            /* Slightly dimmed */
                }
                
                /* Remove default Streamlit spacing */
                .latest-headlines + div {
                    margin-top: -0.5rem;
                }
                
                /* Reduce space after selectbox */
                .stSelectbox {
                    margin-bottom: -1rem;
                }
                
                /* Reduce space between category dropdown and first headline */
                div[data-testid="stSelectbox"] + div {
                    margin-top: -0.5rem;
                }
            </style>
            <div class="latest-headlines">
                Published Headlines
            </div>
        """, unsafe_allow_html=True)
        
        # Fetch headlines
        headlines = fetch_latest_headlines()
        if headlines:
            # Get category counts and create filter options
            category_counts = get_category_counts(headlines)
            
            # Add custom CSS to reduce spacing around selectbox and headlines
            st.markdown("""
                <style>
                    /* Reduce space after selectbox */
                    .stSelectbox {
                        margin-bottom: -1rem;
                    }
                    
                    /* Adjust spacing for headlines section */
                    .latest-headlines {
                        margin-top: -0.5rem;
                        padding: 0;
                    }
                    .latest-headlines h4 {
                        margin-bottom: 0.5rem;
                    }
                    /* Reduce space between category dropdown and first headline */
                    div[data-testid="stSelectbox"] + div {
                        margin-top: -0.5rem;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # Create category filter dropdown
            category_options = ["All Categories"] + [cat for cat, _ in category_counts]
            selected_category = st.selectbox(
                "Filter by Category",
                category_options,
                format_func=lambda x: f"{x} ({dict(category_counts).get(x, len(headlines)) if x != 'All Categories' else len(headlines)})",
                label_visibility="collapsed"
            )
            
            # Initialize page number in session state if not exists
            if 'headline_page' not in st.session_state:
                st.session_state.headline_page = 1
            
            # Display filtered headlines with pagination
            headlines_html, total_pages = format_latest_headlines(
                headlines, 
                selected_category, 
                st.session_state.headline_page
            )
            st.markdown(headlines_html, unsafe_allow_html=True)
            
            # Pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if st.button("←", disabled=st.session_state.headline_page <= 1):
                    st.session_state.headline_page -= 1
                    st.rerun()
            
            with col2:
                st.markdown(
                    f'<div style="text-align: center; color: rgba(255,255,255,0.8);">'
                    f'Page {st.session_state.headline_page} of {total_pages}'
                    f'</div>',
                    unsafe_allow_html=True
                )
            
            with col3:
                if st.button("→", disabled=st.session_state.headline_page >= total_pages):
                    st.session_state.headline_page += 1
                    st.rerun()
            
            # Reset page number when category changes
            if selected_category != st.session_state.get('last_category'):
                st.session_state.headline_page = 1
                st.session_state.last_category = selected_category
                st.rerun()
        else:
            st.caption("No recent headlines available")

    # Main content area with adjusted ratio
    col1, col2 = st.columns([0.8, 3])  # Reduced ratio for cluster listings
    
    with col1:
        if 'is_loading_clusters' not in st.session_state:
            st.session_state.is_loading_clusters = False
            
        if st.session_state.is_loading_clusters:
            # Show loading indicator while processing clusters
            with st.spinner("Processing news clusters..."):
                if 'news_data' in st.session_state:
                    # Process clusters
                    clusters = []
                    valid_clusters = [c for c in st.session_state.news_data.get('clusters', []) 
                                    if len(c.get('articles', [])) >= 3]
                    total_clusters = len(valid_clusters)
                    
                    if total_clusters > 0:
                        st.write(f"Found {total_clusters} clusters to analyze")
                        progress_bar = st.progress(0)
                        
                        for idx, cluster in enumerate(valid_clusters):
                            # Update progress bar
                            progress = (idx) / total_clusters
                            progress_bar.progress(progress)
                            # st.write(f"Analyzing cluster {idx + 1}/{total_clusters}: {len(cluster.get('articles', []))} articles")
                            
                            analysis = analyze_cluster(cluster)
                            if analysis:
                                clusters.append({
                                    'category': analysis.get('category', 'Unknown'),
                                    'subject': analysis.get('subject', 'Unknown'),
                                    'bias': analysis.get('bias', 0.0),
                                    'cluster_size': len(cluster.get('articles', [])),
                                    'articles': cluster.get('articles', [])
                                })
                    
                        # Complete the progress bar
                        progress_bar.progress(1.0)
                        st.write(f"Analysis complete! Found {len(clusters)} valid clusters")
                    else:
                        st.warning("No clusters with 3 or more articles found")
                    
                    st.session_state.clusters = clusters
                    st.session_state.is_loading_clusters = False
                    del st.session_state.news_data  # Clean up
                    st.rerun()
                else:
                    st.error("No news data found in session state")
                    st.session_state.is_loading_clusters = False
        elif st.session_state.clusters:
            # Now display the clusters
            for i, cluster in enumerate(st.session_state.clusters):
                # Determine if this cluster is being evaluated
                is_evaluating = (hasattr(st.session_state, 'evaluating_cluster') and 
                                st.session_state.evaluating_cluster == i and 
                                not hasattr(st.session_state, 'article_rejected'))
                opacity = "1" if is_evaluating or not hasattr(st.session_state, 'evaluating_cluster') else "1"
                transition = "opacity .9s ease"
                
                st.markdown(
                    f"""
                    <div style="opacity: {opacity}; transition: {transition}; padding: 1rem; border: 1px solid rgba(74, 111, 165, 0.1); border-radius: 8px; margin-bottom: 0.75rem; background-color: #1C1C1C;">
                        <div style="font-weight: 500; font-size: 1em; margin-bottom: 0.5rem; color: rgba(255, 255, 255, 0.95);">
                            {cluster['subject']}
                        </div>
                        <div style="color: rgba(192, 160, 128, 0.95); font-size: 0.85em; margin-bottom: 0.5rem;">
                            {cluster['category']}
                        </div>
                        <div style="display: flex; align-items: center; width: 100%; padding: 4px 0;">
                            <div style="flex: 0 0 auto; padding-right: 15px; font-size: 0.9em; color: rgba(255, 255, 255, 0.8);">
                                Articles: {cluster['cluster_size']}
                            </div>
                            <div style="flex: 1;">{create_custom_progress_bar(cluster.get('bias', 0), i)}</div>
                        </div>
                        <div class="button-container" id="button_container_{i}">
                        </div>
                    </div>
                    
                    <style>
                        /* Style for the button container */
                        .button-container .stButton > button {{
                            background: #4a6fa5;
                            color: rgba(255, 255, 255, 0.95);
                            border: none;
                            padding: 8px 16px;
                            border-radius: 4px;
                            cursor: pointer;
                            margin-top: 12px;
                            width: 100%;
                            font-size: 14px;
                            font-weight: 500;
                        }}
                        
                        .button-container .stButton > button:hover {{
                            background: #5a7fb5;
                            color: white;
                        }}
                        
                        /* Ensure button container is properly nested */
                        #button_container_{i} {{
                            margin: 0;
                            padding: 0;
                        }}
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                
                # Create a container for the button
                button_container = st.container()
                with button_container:
                    if st.button("Evaluate Sources", key=f"eval_cluster_{i}"):
                        st.session_state.evaluating_cluster = i
                        with st.spinner("Generating article..."):
                            article_data = create_article(cluster)
                            if article_data:
                                st.session_state.selected_cluster = cluster
                                st.session_state.article_data = article_data
                                st.session_state.current_step = 1
                                st.session_state.clusters.pop(i)
                                st.session_state.evaluating_cluster = None
                                st.rerun()
                            else:
                                st.error("Failed to generate article")
                                st.session_state.evaluating_cluster = None
                
                # Add divider after the button (if not the last item)
                if i < len(st.session_state.clusters) - 1:
                    st.markdown("""
                        <div style="height: 1px; 
                                   background: linear-gradient(to right, 
                                       rgba(74, 111, 165, 0.05), 
                                       rgba(74, 111, 165, 0.2), 
                                       rgba(74, 111, 165, 0.05)); 
                                   margin: 1rem 0 1.5rem 0;">
                        </div>
                    """, unsafe_allow_html=True)

    with col2:
        display_wizard_content()

    # Show success view if publication was successful
    if hasattr(st.session_state, 'publication_success') and st.session_state.publication_success:
        display_publication_success(
            st.session_state.published_article_id,
            st.session_state.published_article_url
        )

if __name__ == "__main__":
    main() 