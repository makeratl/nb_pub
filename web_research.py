import streamlit as st
import pandas as pd
import plotly.express as px
from chat_codegpt import chat_with_codegpt
import requests
import json
from dotenv import load_dotenv
import os
import time
from review_articles import evaluate_article_with_ai, display_evaluation
from publish_utils import generate_and_encode_images, publish_article

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
        # Add CSS for centered metrics
        st.markdown("""
            <style>
                div[data-testid="metric-container"] {
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    padding: 1rem;
                    text-align: center !important;
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
            </style>
        """, unsafe_allow_html=True)
        
        # Center the metrics container
        st.markdown('<div style="max-width: 800px; margin: 0 auto;">', unsafe_allow_html=True)
        
        # First row - Category and Quality
        col1, col2 = st.columns(2)
        
        with col1:
            category = eval_data.get('cat', 'Unknown')
            st.metric("Category", category)
        
        with col2:
            quality_score = eval_data.get('quality_score', 0)
            try:
                quality_score = float(quality_score)
            except (ValueError, TypeError):
                quality_score = 0.0
            st.metric("Quality Score", f"{quality_score:.1f}/10")
        
        # Add some spacing
        st.markdown("<div style='margin-top: 1em;'></div>", unsafe_allow_html=True)
        
        # Second row - Bias and Viral
        col1, col2 = st.columns(2)
        
        with col1:
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
                
                # Get color for bias value
                bias_color = get_bias_color(numeric_bias)
                
                # Add custom styling for this metric
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
            
        with col2:
            trend_score = eval_data.get('trend')
            try:
                trend_score = float(trend_score)
            except (ValueError, TypeError):
                trend_score = 0.0
            st.metric("Viral Potential", f"{trend_score:.1f}/10")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Display reasoning in an expander (closed by default)
        with st.expander("AI Analysis", expanded=False):
            reasoning = eval_data.get('reasoning', 'No analysis provided')
            st.markdown(reasoning)
    
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
    
    st.markdown("<div style='margin: 0.75rem 0;'><hr style='margin: 0;'></div>", unsafe_allow_html=True)  # Tighter divider
    
    # Main content
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Summary")
        st.markdown(st.session_state.article_data['summary'])
        
        with st.expander("Full Story", expanded=False):
            st.markdown(st.session_state.article_data['story'], unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Haiku")
        # Add style for paragraph margins and display haiku
        st.markdown("""
            <style>
                .element-container div.stMarkdown p {
                    margin: 0.5em 0;
                }
            </style>
        """, unsafe_allow_html=True)
        haiku_lines = st.session_state.article_data['haiku'].split('\n')
        for i, line in enumerate(haiku_lines):
            st.markdown(line.strip(), unsafe_allow_html=True)
            if i < len(haiku_lines) - 1:
                st.markdown("<br>", unsafe_allow_html=True)
        
        with st.expander("Source Articles", expanded=False):
            for article in st.session_state.selected_cluster['articles']:
                st.markdown(f"- [{article['title']}]({article['link']}) - {article['name_source']}")

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
            
            # Start haiku image generation before moving to next step
            with st.spinner("Preparing article and generating haiku image..."):
                # Generate haiku image
                image_data, image_haiku = generate_haiku_images(
                    st.session_state.article_data['haiku'],
                    st.session_state.article_data['headline']
                )
                
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
                    "Cited": json.dumps(sources)  # Add citations
                }
                
                # Add image data if generation was successful
                if image_data and image_haiku:
                    st.session_state.haiku_image = image_haiku
                    st.session_state.publish_data.update({
                        'image_data': image_data,
                        'image_haiku': image_haiku
                    })
                
                with open('publish.json', 'w') as f:
                    json.dump(st.session_state.publish_data, f, indent=2)
                
                st.session_state.current_step = 3
                st.rerun()
    with col2:
        if st.button("Reject Article", key="review_reject_step"):
            reset_article_state()
            st.rerun()
    
    st.markdown("---")  # Divider
    
    # Main content
    review_tab, article_tab = st.tabs(["AI Review", "Article Content"])
    
    with review_tab:
        #st.subheader("AI Review Results")
        display_evaluation_results()
    
    with article_tab:
        st.subheader(st.session_state.article_data['headline'])
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### Summary")
            st.markdown(st.session_state.article_data['summary'])
            
            with st.expander("Full Story", expanded=True):
                st.markdown(st.session_state.article_data['story'], unsafe_allow_html=True)
        
        with col2:
            st.markdown("### Haiku")
            # Add style for paragraph margins and display haiku
            st.markdown("""
                <style>
                    .element-container div.stMarkdown p {
                        margin: 0.5em 0;
                    }
                </style>
            """, unsafe_allow_html=True)
            haiku_lines = st.session_state.article_data['haiku'].split('\n')
            for i, line in enumerate(haiku_lines):
                st.markdown(line.strip(), unsafe_allow_html=True)
                if i < len(haiku_lines) - 1:
                    st.markdown("<br>", unsafe_allow_html=True)
            
            with st.expander("Source Articles", expanded=False):
                for article in st.session_state.selected_cluster['articles']:
                    st.markdown(f"- [{article['title']}]({article['link']}) - {article['name_source']}")

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
                    st.session_state.haiku_image = image_haiku
                    st.session_state.publish_data.update({
                        'image_data': image_data,
                        'image_haiku': image_haiku
                    })
                    st.rerun()
    with col2:
        if st.button("Continue to Final Review", key="image_continue_review"):
            st.session_state.current_step = 4
            st.rerun()
    
    st.markdown("---")  # Divider
    
    # Main content
    st.markdown("### Haiku Visualization")
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
        st.image(st.session_state.haiku_image, caption="Generated Haiku Image")

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
        if st.button("Publish Article", key="final_review_publish"):
            with st.spinner("Publishing article..."):
                article_id = publish_article(
                    st.session_state.publish_data,
                    os.environ.get("PUBLISH_API_KEY")
                )
                if article_id:
                    article_url = f"https://ainewsbrew.com/article/{article_id}"
                    st.success(f"""Article published successfully! 
                        \nID: {article_id}
                        \nView at: [{article_url}]({article_url})""")
    try:
        st.subheader("Final Review")
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("### Article Content")
            st.markdown(f"**Headline:** {st.session_state.publish_data.get('AIHeadline', 'No headline')}")
            st.markdown(f"**Category:** {st.session_state.publish_data.get('cat', 'No category')}")
            st.markdown(f"**Topic:** {st.session_state.publish_data.get('topic', 'No topic')}")
            st.markdown("**Haiku:**")
            st.markdown(st.session_state.publish_data.get('AIHaiku', 'No haiku'))
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
            
            if st.session_state.haiku_image is not None:
                st.image(st.session_state.haiku_image, caption="Final Haiku Image")
            else:
                st.warning("No haiku image available")
    
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
        time_context = f"• {st.session_state.time_range}"  # Changed to bullet point
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
    """Generate color for bias value from -1 (blue) to 1 (red)"""
    try:
        # Ensure bias_value is a float and clamped between -1 and 1
        bias = float(bias_value)
        bias = max(-1.0, min(1.0, bias))
        
        # Define colors as RGB tuples
        left_color = (41, 98, 255)    # Bright Blue
        center_color = (128, 0, 128)   # Purple
        right_color = (255, 36, 0)     # Bright Red
        
        # Convert bias from -1:1 to 0:1 scale
        normalized = (bias + 1) / 2
        
        if normalized <= 0.5:
            # Blend between blue and purple
            ratio = normalized * 2
            r = left_color[0] + (center_color[0] - left_color[0]) * ratio
            g = left_color[1] + (center_color[1] - left_color[1]) * ratio
            b = left_color[2] + (center_color[2] - left_color[2]) * ratio
        else:
            # Blend between purple and red
            ratio = (normalized - 0.5) * 2
            r = center_color[0] + (right_color[0] - center_color[0]) * ratio
            g = center_color[1] + (right_color[1] - center_color[1]) * ratio
            b = center_color[2] + (right_color[2] - center_color[2]) * ratio
        
        return f"rgb({int(r)}, {int(g)}, {int(b)})"
        
    except Exception:
        return "rgb(128, 128, 128)"  # Default to gray on error

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
            
            /* Progress bar base styles */
            div[data-testid="stProgress"] > div > div {
                background-color: var(--accent-blue);
            }
            
            /* Progress bar container styles */
            .bias-progress-container {
                background: white;
                padding: 0.5rem;
                border-radius: 4px;
                margin: 0.5rem 0;
            }
            
            /* Custom progress bar colors - with higher specificity */
            .bias-left div[data-testid="stProgress"] > div > div:first-child {
                background: rgb(41, 98, 255) !important;
            }
            
            .bias-center div[data-testid="stProgress"] > div > div:first-child {
                background: rgb(128, 0, 128) !important;
            }
            
            .bias-right div[data-testid="stProgress"] > div > div:first-child {
                background: rgb(255, 36, 0) !important;
            }
            
            /* Override any Streamlit defaults */
            .stProgress > div > div {
                background-color: inherit !important;
            }
            
            /* Debug outline */
            .bias-progress-container {
                outline: 1px solid rgba(0,0,0,0.1);
            }
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
                padding-top: 0.5rem !important;
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
        st.header("Search Controls")
        search_type = st.radio("Search Type", ["Headlines", "Topic"])
        
        # Create a form to handle the Enter key
        with st.form(key='search_form'):
            if search_type == "Topic":
                topic = st.text_input("Enter Topic")
                # Store topic in session state for title display
                if topic:
                    st.session_state.topic = topic
            else:
                # Clear topic from session state if using Headlines
                st.session_state.topic = None
            
            time_range = st.select_slider(
                "Time Range",
                options=["1h", "3h", "4h", "6h", "12h", "24h", "2d", "3d", "5d", "7d"],
                value="24h",
                help="Select time range from 1 hour to 7 days"
            )
            # Store time range in session state for title display
            st.session_state.time_range = time_range
            
            submit_button = st.form_submit_button("Search News")
            
            if submit_button:
                # Clear all session state except search parameters
                for key in list(st.session_state.keys()):
                    if key != 'topic' and key != 'time_range':
                        del st.session_state[key]
                
                # Clear both columns by forcing a rerun before loading state
                col1, col2 = st.columns([2, 3])
                with col1:
                    st.empty()
                with col2:
                    st.empty()
                
                # Now set loading state and trigger another rerun
                st.session_state.is_loading_clusters = True
                st.rerun()

    # Main content area
    col1, col2 = st.columns([2, 3])
    
    # Clear columns if we're starting a new search
    if hasattr(st.session_state, 'is_loading_clusters') and st.session_state.is_loading_clusters:
        with col1:
            st.empty()
        with col2:
            st.empty()
            
        query = st.session_state.topic if search_type == "Topic" else ""
        news_data = get_news_data(search_type, query, time_range)
        
        if news_data:
            # Calculate total clusters before displaying
            total_clusters = len([c for c in news_data.get('clusters', []) if c.get('cluster_size', 0) >= 3])
            clusters = []
            processed_clusters = 0
            
            with col1:
                st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.1); border-radius: 8px; padding: 2rem; text-align: center;">
                        <div class="loading-spinner" style="margin: 0 auto;">
                            <style>
                                .loading-spinner {{
                                    width: 50px;
                                    height: 50px;
                                    border: 5px solid #f3f3f3;
                                    border-top: 5px solid var(--accent-blue);
                                    border-radius: 50%;
                                    animation: spin 1s linear infinite;
                                }}
                                @keyframes spin {{
                                    0% {{ transform: rotate(0deg); }}
                                    100% {{ transform: rotate(360deg); }}
                                }}
                            </style>
                        </div>
                        <div style="margin-top: 1.5rem; color: var(--text-secondary);">
                            <div style="color: var(--accent-blue); font-weight: 500; margin-bottom: 0.5rem;">
                                Processing News Data
                            </div>
                            <div style="font-size: 0.9em; margin: 0.3rem 0;">Found {total_clusters} news clusters to analyze</div>
                            <div style="width: 100%; background: rgba(255,255,255,0.2); border-radius: 4px; margin: 1rem 0; height: 8px; overflow: hidden;">
                                <div id="progress-bar" style="width: 0%; height: 100%; background: var(--accent-blue); transition: width 0.3s ease;"></div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            for i, cluster in enumerate(news_data.get('clusters', [])):
                if cluster.get('cluster_size', 0) >= 3:
                    processed_clusters += 1
                    progress = (processed_clusters / total_clusters) * 100
                    
                    # Update progress bar
                    with col1:
                        st.markdown(f"""
                            <style>
                                #progress-bar {{
                                    width: {progress}% !important;
                                }}
                            </style>
                            <div style="text-align: center; color: var(--text-secondary); font-size: 0.9em; margin-top: 10px; display: none;">
                                Processing cluster {processed_clusters} of {total_clusters}
                            </div>
                        """, unsafe_allow_html=True)
                    
                    analysis = analyze_cluster(cluster)
                    clusters.append({
                        **cluster,
                        **analysis
                    })
            
            st.session_state.clusters = clusters
            st.session_state.is_loading_clusters = False
            st.rerun()

    with col1:
        if 'is_loading_clusters' not in st.session_state:
            st.session_state.is_loading_clusters = False
            
        if st.session_state.is_loading_clusters:
            st.markdown("""
                <div style="background: rgba(255,255,255,0.1); border-radius: 8px; padding: 2rem; text-align: center;">
                    <div class="loading-spinner" style="margin: 0 auto;">
                        <style>
                            .loading-spinner {
                                width: 50px;
                                height: 50px;
                                border: 5px solid #f3f3f3;
                                border-top: 5px solid var(--accent-blue);
                                border-radius: 50%;
                                animation: spin 1s linear infinite;
                            }
                            @keyframes spin {
                                0% { transform: rotate(0deg); }
                                100% { transform: rotate(360deg); }
                            }
                        </style>
                    </div>
                    <div style="margin-top: 1.5rem; color: var(--text-secondary);">
                        <div style="color: var(--accent-blue); font-weight: 500; margin-bottom: 0.5rem;">
                            Processing News Data
                        </div>
                        <div style="font-size: 0.9em; margin: 0.3rem 0;">1. Fetching latest news</div>
                        <div style="font-size: 0.9em; margin: 0.3rem 0;">2. Processing clusters</div>
                        <div style="font-size: 0.9em; margin: 0.3rem 0;">3. Analyzing content & bias</div>
                        <div style="margin-top: 1rem; font-size: 0.8em; opacity: 0.8;">
                            Please wait while AI evaluates the news clusters
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        elif st.session_state.clusters:
            # Now display the clusters
            for i, cluster in enumerate(st.session_state.clusters):
                # Determine if this cluster is being evaluated
                is_evaluating = hasattr(st.session_state, 'evaluating_cluster') and st.session_state.evaluating_cluster == i
                opacity = "1" if is_evaluating else "0.4" if hasattr(st.session_state, 'evaluating_cluster') else "1"
                transition = "opacity 0.3s ease"
                
                with st.expander(f"{cluster['subject']} ({cluster['category']})", expanded=True):
                    st.markdown(
                        f"""
                        <div style="opacity: {opacity}; transition: {transition};">
                            <div style="display: flex; align-items: center; width: 100%; padding: 4px 0;">
                                <div style="flex: 0 0 auto; padding-right: 15px;">Articles: {cluster['cluster_size']}</div>
                                <div style="flex: 1;">{create_custom_progress_bar(cluster.get('bias', 0), i)}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    if st.button("Evaluate Sources", key=f"cluster_{i}"):
                        st.session_state.evaluating_cluster = i
                        with st.spinner("Generating article..."):
                            article_data = create_article(cluster)
                            if article_data:
                                st.session_state.selected_cluster = cluster
                                st.session_state.article_data = article_data
                                st.session_state.current_step = 1
                                st.session_state.clusters.pop(i)
                                st.session_state.evaluating_cluster = None  # Clear evaluation state
                                st.rerun()
                            else:
                                st.error("Failed to generate article")
                                st.session_state.evaluating_cluster = None
        
        # Show evaluation spinner in the same container
        if hasattr(st.session_state, 'evaluating_cluster') and st.session_state.evaluating_cluster is not None:
            cluster = st.session_state.clusters[st.session_state.evaluating_cluster]
            st.markdown(f"""
                <div style="background: rgba(255,255,255,0.1); border-radius: 8px; padding: 2rem; text-align: center;">
                    <div class="evaluation-spinner" style="margin: 0 auto;">
                        <style>
                            .evaluation-spinner {{
                                width: 60px;
                                height: 60px;
                                border: 5px solid #f3f3f3;
                                border-top: 5px solid var(--accent-gold);
                                border-radius: 50%;
                                animation: spin 1.2s linear infinite;
                            }}
                            @keyframes spin {{
                                0% {{ transform: rotate(0deg); }}
                                100% {{ transform: rotate(360deg); }}
                            }}
                        </style>
                    </div>
                    <div style="margin-top: 1rem; color: var(--text-secondary);">
                        <div style="color: var(--text-primary); font-weight: 500; font-size: 1.1em; margin-bottom: 0.5rem;">
                            {cluster['subject']}
                        </div>
                        <div style="color: var(--accent-gold); font-weight: 500;">Evaluating Sources</div>
                        <div style="font-size: 0.9em; margin-top: 0.5rem;">Analyzing content and generating article...</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    with col2:
        if st.session_state.selected_cluster and st.session_state.article_data:
            # Add custom CSS for wizard layout
            st.markdown("""
                <style>
                    /* Reduce spacing between wizard elements */
                    .block-container > div > div > div:has(h2) {
                        margin-bottom: 0.5rem !important;
                    }
                    .block-container > div > div > div:has(button) {
                        margin-top: 0.25rem !important;
                        margin-bottom: 0.25rem !important;
                    }
                    /* Remove extra padding from progress bar */
                    div[data-testid="stProgress"] {
                        padding-top: 0.25rem !important;
                        padding-bottom: 0.25rem !important;
                    }
                    /* Tighten caption spacing */
                    .caption {
                        margin-top: 0 !important;
                        margin-bottom: 0.25rem !important;
                    }
                    /* Reduce button margins */
                    .stButton > button {
                        margin: 0.25rem 0 !important;
                    }
                    /* Reduce divider spacing */
                    hr {
                        margin: 0.5rem 0 !important;
                    }
                    /* Tighten spacing around content sections */
                    .element-container {
                        margin: 0.25rem 0 !important;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # Rest of your existing display logic for steps
            # Add a progress indicator
            progress = st.progress(st.session_state.current_step / 4)
            steps = ["Generate", "Review", "Visualize", "Publish"]
            st.caption(f"Step {st.session_state.current_step}/4: {steps[st.session_state.current_step-1]}")
            
            # Step 1: Article Generation
            if st.session_state.current_step == 1:
                display_article_step()
                if st.button("Continue to Review"):
                    with st.spinner("Running AI review..."):
                        evaluation = review_article(st.session_state.article_data)
                        if evaluation:
                            st.session_state.evaluation = evaluation
                            st.session_state.current_step = 2
                            st.rerun()
            
            # Step 2: AI Review
            elif st.session_state.current_step == 2:
                display_review_step()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Accept and Continue", key="main_review_accept"):
                        # Format citations
                        sources = []
                        for i, article in enumerate(st.session_state.selected_cluster['articles'][:8], 1):
                            sources.append([i, article['link']])
                            
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
                            "Cited": json.dumps(sources)  # Add citations
                        }
                        with open('publish.json', 'w') as f:
                            json.dump(st.session_state.publish_data, f, indent=2)
                        st.session_state.current_step = 3
                        st.rerun()
                with col2:
                    if st.button("Reject Article", key="main_review_reject"):
                        reset_article_state()
                        st.rerun()
            
            # Step 3: Image Generation
            elif st.session_state.current_step == 3:
                display_image_step()
                if st.session_state.haiku_image is not None:
                    if st.button("Continue to Final Review", key="main_continue_review"):
                        st.session_state.current_step = 4
                        st.rerun()
            
            # Step 4: Final Review and Publication
            else:
                display_final_review()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Publish Article", key="main_publish"):
                        with st.spinner("Publishing article..."):
                            article_id = publish_article(
                                st.session_state.publish_data,
                                os.environ.get("PUBLISH_API_KEY")
                            )
                            if article_id:
                                article_url = f"https://ainewsbrew.com/article/{article_id}"
                                st.session_state.publication_success = True
                                st.session_state.published_article_id = article_id
                                st.session_state.published_article_url = article_url
                                st.rerun()
                with col2:
                    if st.button("Cancel Publication", key="main_cancel"):
                        reset_article_state()
                        st.rerun()
    
    # Show success view if publication was successful
    if hasattr(st.session_state, 'publication_success') and st.session_state.publication_success:
        display_publication_success(
            st.session_state.published_article_id,
            st.session_state.published_article_url
        )

if __name__ == "__main__":
    main() 