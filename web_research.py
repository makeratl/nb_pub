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
    st.session_state.article_data = None
    st.session_state.evaluation = None
    st.session_state.haiku_image = None
    st.session_state.publish_data = None
    st.session_state.selected_cluster = None

def get_news_data(search_type, query="", when="1d"):
    """Fetch news data from NewsCatcher API"""
    if search_type == "Headlines":
        url = "https://v3-api.newscatcherapi.com/api/latest_headlines"
        params = {
            "when": when,
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
            "from_": when,
            "countries": "US, CA, MX, GB",
            "lang": "en",
            "ranked_only": "true",
            "clustering_enabled": "true",
            "page_size": "100"
        }

    headers = {"x-api-token": API_KEY}
    
    with st.spinner('Fetching news data...'):
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

    with st.spinner('Generating article...'):
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
            'topic': evaluation.get('topic', 'Unknown')
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
        # Create three columns for key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            quality_score = eval_data.get('quality_score', 0)
            try:
                # Try to convert quality_score to float, use 0 if fails
                quality_score = float(quality_score)
            except (ValueError, TypeError):
                quality_score = 0.0
            st.metric("Quality Score", f"{quality_score:.1f}/10")
        
        with col2:
            category = eval_data.get('cat', 'Unknown')
            st.metric("Category", category)
        
        with col3:
            bias_score = eval_data.get('bs_p', 'Neutral')
            st.metric("Bias Score", bias_score)
        
        # Display reasoning in an expander
        with st.expander("AI Analysis", expanded=True):
            reasoning = eval_data.get('reasoning', 'No analysis provided')
            st.markdown(reasoning)
    
    except Exception as e:
        st.error(f"Error displaying evaluation results: {str(e)}")

def display_article_step():
    """Display the generated article content"""
    st.subheader(st.session_state.article_data['headline'])
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Summary")
        st.markdown(st.session_state.article_data['summary'])
        
        with st.expander("Full Story", expanded=False):
            st.markdown(st.session_state.article_data['story'], unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Haiku")
        st.markdown(st.session_state.article_data['haiku'])
        
        with st.expander("Source Articles", expanded=False):
            for article in st.session_state.selected_cluster['articles']:
                st.markdown(f"- [{article['title']}]({article['link']}) - {article['name_source']}")

def display_review_step():
    """Display the AI review results and article content"""
    review_tab, article_tab = st.tabs(["AI Review", "Article Content"])
    
    with review_tab:
        st.subheader("AI Review Results")
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
            st.markdown(st.session_state.article_data['haiku'])
            
            with st.expander("Source Articles", expanded=False):
                for article in st.session_state.selected_cluster['articles']:
                    st.markdown(f"- [{article['title']}]({article['link']}) - {article['name_source']}")

def display_image_step():
    """Display the haiku image generation step"""
    if not st.session_state.publish_data:
        st.error("No publication data available for image generation")
        reset_article_state()
        return
        
    st.subheader("Haiku Visualization")
    
    if st.session_state.haiku_image is None:
        with st.spinner("Generating haiku image..."):
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
                return
    
    st.image(st.session_state.haiku_image, caption="Generated Haiku Image")
    
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

def display_final_review():
    """Display final review before publication"""
    if not st.session_state.publish_data:
        st.error("No publication data available")
        reset_article_state()
        return
    
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

def main():
    st.set_page_config(layout="wide", page_title="News Research Dashboard")
    init_session_state()

    st.title("News Research Dashboard")

    # Sidebar controls
    with st.sidebar:
        st.header("Search Controls")
        search_type = st.radio("Search Type", ["Headlines", "Topic"])
        
        if search_type == "Topic":
            topic = st.text_input("Enter Topic")
        
        time_range = st.select_slider(
            "Time Range",
            options=["1h", "12h", "1d", "7d", "30d"],
            value="1d"
        )
        
        if st.button("Search News"):
            query = topic if search_type == "Topic" else ""
            news_data = get_news_data(search_type, query, time_range)
            
            if news_data:
                with st.spinner('Analyzing clusters...'):
                    clusters = []
                    for cluster in news_data.get('clusters', []):
                        if cluster.get('cluster_size', 0) >= 3:
                            analysis = analyze_cluster(cluster)
                            clusters.append({
                                **cluster,
                                **analysis
                            })
                    st.session_state.clusters = clusters
                    st.success(f"Found {len(clusters)} relevant clusters")

    # Main content area
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("News Clusters")
        if st.session_state.clusters:
            for i, cluster in enumerate(st.session_state.clusters):
                with st.expander(f"{cluster['subject']} ({cluster['category']})"):
                    st.write(f"Articles: {cluster['cluster_size']}")
                    try:
                        bias = float(cluster.get('bias', 0))
                    except (ValueError, TypeError):
                        bias = 0.0
                    st.progress(
                        (bias + 1) / 2,
                        f"Bias: {bias:0.2f}"
                    )
                    if st.button("Select Cluster", key=f"cluster_{i}"):
                        with st.spinner("Generating article..."):
                            article_data = create_article(cluster)
                            if article_data:
                                st.session_state.selected_cluster = cluster
                                st.session_state.article_data = article_data
                                st.session_state.current_step = 1
                                # Remove selected cluster from the list
                                st.session_state.clusters.pop(i)
                                st.rerun()
                            else:
                                st.error("Failed to generate article")

    with col2:
        if st.session_state.selected_cluster and st.session_state.article_data:
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
                    if st.button("Accept and Continue"):
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
                    if st.button("Reject Article"):
                        reset_article_state()
                        st.rerun()
            
            # Step 3: Image Generation
            elif st.session_state.current_step == 3:
                display_image_step()
                if st.session_state.haiku_image is not None:
                    if st.button("Continue to Final Review"):
                        st.session_state.current_step = 4
                        st.rerun()
            
            # Step 4: Final Review and Publication
            else:
                display_final_review()
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Publish Article"):
                        with st.spinner("Publishing article..."):
                            article_id = publish_article(
                                st.session_state.publish_data,
                                os.environ.get("PUBLISH_API_KEY")
                            )
                            if article_id:
                                st.success(f"Article published successfully! ID: {article_id}")
                                reset_article_state()
                                st.rerun()
                with col2:
                    if st.button("Cancel Publication"):
                        reset_article_state()
                        st.rerun()

if __name__ == "__main__":
    main() 