"""Article generation and review wizard"""
import streamlit as st
from .display import get_bias_color
from .article_evaluation import evaluate_article_with_ai
from publish_utils import publish_article, generate_and_encode_images, search_historical_articles
from .utils import reset_article_state
from .unified_haiku_image_generator import generate_haiku_images
from .bluesky_publish import publish_to_bluesky
from .keyword_optimizer import optimize_headline_keywords
from .api_client import get_news_data
from modules.instagram_publish import InstagramPublisher
from chat_codegpt import chat_with_codegpt
import json
import os
import base64
import requests
import urllib.parse
from datetime import datetime

def create_step_header(headline, buttons):
    """Create consistent header with headline and action buttons"""
    # Format the headline string with proper HTML escaping
    formatted_headline = headline.replace('"', '&quot;').replace("'", '&#39;')
    
    st.markdown(f"""
        <style>
            .step-header {{
                margin-bottom: 1rem;
                padding: 0.5rem;
                background: rgba(74, 111, 165, 0.05);
                border-radius: 8px;
                border: 1px solid rgba(74, 111, 165, 0.1);
            }}
            .headline-text {{
                color: rgba(255, 255, 255, 0.95);
                font-size: 1.1em;
                font-weight: 500;
                margin-bottom: 0.5rem;
            }}
            .action-buttons {{
                display: flex;
                gap: 1rem;
            }}
        </style>
        <div class="step-header">
            <div class="headline-text">{formatted_headline}</div>
            <div class="action-buttons">
    """, unsafe_allow_html=True)
    
    # Create columns for buttons
    cols = st.columns(len(buttons))
    for col, (label, key, callback) in zip(cols, buttons):
        with col:
            if st.button(label, key=key):
                callback()
    
    st.markdown("</div></div>", unsafe_allow_html=True)

def display_article_step():
    """Display the generated article content"""
    headline = st.session_state.article_data.get('headline', '')
    category = st.session_state.selected_cluster.get('category', 'Unknown')
    quality_score = 0.0  # Placeholder value
    bias_text = 'Neutral'  # Placeholder value
    trend_score = 0.0  # Placeholder value
    
    # Add citation highlighting styles
    st.markdown("""
        <style>
            q[data-source], span[data-source], span[data-sources] {
                background-color: rgba(74, 111, 165, 0.1);
                border-bottom: 1px dashed rgba(74, 111, 165, 0.5);
                cursor: pointer;
                position: relative;
            }
            
            q[data-source]:hover, span[data-source]:hover, span[data-sources]:hover {
                background-color: rgba(74, 111, 165, 0.2);
            }
            
            .citation-tooltip {
                position: absolute;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%);
                background-color: #1C1C1C;
                border: 1px solid rgba(74, 111, 165, 0.3);
                border-radius: 4px;
                padding: 0.5rem;
                font-size: 0.9em;
                color: rgba(255, 255, 255, 0.9);
                z-index: 1000;
                display: none;
            }
            
            q[data-source]:hover .citation-tooltip,
            span[data-source]:hover .citation-tooltip,
            span[data-sources]:hover .citation-tooltip {
                display: block;
            }
            
            .source-link {
                color: #4A6FA5;
                text-decoration: none;
            }
            
            .source-link:hover {
                text-decoration: underline;
            }

            .ai-attribution {
                margin-top: 2rem;
                padding-top: 1rem;
            }

            .ai-attribution hr {
                border: 0;
                height: 1px;
                background: rgba(74, 111, 165, 0.2);
                margin: 0 0 1rem 0;
            }

            .ai-attribution .footnote {
                color: rgba(255, 255, 255, 0.7);
                font-size: 0.9em;
                font-style: italic;
                line-height: 1.5;
                margin: 0;
                padding: 0 1rem;
            }
        </style>
        
        <script>
            function showSourceTooltip(element) {
                const sourceIds = element.dataset.source || element.dataset.sources;
                const sources = sourceIds.split(',').map(id => {
                    const sourceEl = document.querySelector(`[data-source-id="${id}"]`);
                    return sourceEl ? sourceEl.innerHTML : '';
                });
                
                const tooltip = document.createElement('div');
                tooltip.className = 'citation-tooltip';
                tooltip.innerHTML = sources.join('<br>');
                element.appendChild(tooltip);
            }
            
            document.addEventListener('DOMContentLoaded', () => {
                const citations = document.querySelectorAll('q[data-source], span[data-source], span[data-sources]');
                citations.forEach(citation => {
                    citation.addEventListener('mouseenter', () => showSourceTooltip(citation));
                });
            });
        </script>
    """, unsafe_allow_html=True)
    
    # Create hidden source data elements
    source_data_html = ""
    for article in st.session_state.selected_cluster['articles']:
        source_id = article.get('source_id', '')
        if source_id:
            source_data_html += f"""
                <div style="display: none;" data-source-id="{source_id}">
                    <strong>{article['name_source']}</strong><br>
                    <a href="{article['link']}" class="source-link" target="_blank">View Source</a>
                </div>
            """
    st.markdown(source_data_html, unsafe_allow_html=True)
    
    def continue_to_audit():
        with st.spinner("Running AI audit..."):
            evaluation = review_article(st.session_state.article_data)
            if evaluation:
                st.session_state.evaluation = evaluation
                st.session_state.current_step = 2
                st.rerun()
    
    buttons = [
        ("Continue to Audit", "continue_review", continue_to_audit)
    ]
    
    # Define color mapping functions
    def get_quality_color(score):
        if score <= 3:
            return "#ff0000"  # Red
        elif score <= 6:
            return "#ffff00"  # Yellow
        else:
            return "#00ff00"  # Green
    
    def get_propagation_color(score):
        if score <= 3:
            return "#ff0000"  # Red
        elif score <= 6:
            return "#ffff00"  # Yellow
        else:
            return "#00ff00"  # Green
    
    # Define bias mapping
    bias_mapping = {
        'Far Left': -1.0,
        'Left': -0.6,
        'Center Left': -0.3,
        'Neutral': 0.0,
        'Center Right': 0.3,
        'Right': 0.6,
        'Far Right': 1.0
    }
    
    # Get color codes for scores
    quality_color = get_quality_color(quality_score)
    bias_color = get_bias_color(bias_mapping.get(bias_text, 0.0))
    propagation_color = get_propagation_color(trend_score)
    
    header_html = f"""
        <style>
            .step-header {{
                margin-bottom: 1rem;
            }}
            .headline-text {{
                font-size: 1.5rem;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }}
            .subheader-text {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
            }}
            .category {{
                color: rgba(192, 160, 128, 0.8);
                font-size: 1rem;
            }}
            .topic {{
                color: rgba(128, 160, 192, 0.8);
                font-size: 1rem;
            }}
            .scores {{
                display: flex;
                gap: 1rem;
                align-items: center;
                color: rgba(255, 255, 255, 0.7);
            }}
            .score {{
                font-weight: 500;
            }}
            .quality-score {{
                color: {'#ff0000' if quality_score < 6 else 'rgba(0, 255, 0, 0.7)'};
            }}
            .bias-score {{
                color: rgba(255, 255, 255, 0.7);
            }}
            .propagation-score {{
                color: rgba(0, 255, 0, 0.7);
            }}
        </style>
        <div class="step-header">
            <div class="headline-text">{headline}</div>
            <div class="subheader-text">
                <div>
                    <span class="category">{category}</span>
                    <span class="topic"> | {st.session_state.article_data.get('topic', 'Unknown Topic')}</span>
                </div>
                <div class="scores">
                    <span class="score quality-score">Quality: {quality_score:.1f}/10</span>
                    <span class="score bias-score">Bias: {bias_text}</span>
                    <span class="score propagation-score">Propagation: {trend_score:.1f}/10</span>
                </div>
            </div>
        </div>
        <div class="action-buttons">
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Create columns for buttons
    cols = st.columns(len(buttons))
    for col, (label, key, callback) in zip(cols, buttons):
        with col:
            if st.button(label, key=key):
                callback()
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    
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
    
    # Display source tags
    st.markdown('<div class="source-tags">', unsafe_allow_html=True)
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
    col1, col2 = st.columns([1.3, 1.2])
    
    with col1:
        # Haiku display
        haiku_lines = st.session_state.article_data['haiku'].split('\n')
        st.markdown("""
            <style>
                .haiku-container {
                    background-color: #1C1C1C;
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
                    color: rgba(255, 255, 255, 0.9);
                    line-height: 1.5;
                    text-align: center;
                }
                .source-list {
                    max-height: 200px;
                    overflow-y: auto;
                    padding-right: 10px;
                }
                .source-list::-webkit-scrollbar {
                    width: 6px;
                }
                .source-list::-webkit-scrollbar-track {
                    background: rgba(74, 111, 165, 0.1);
                    border-radius: 3px;
                }
                .source-list::-webkit-scrollbar-thumb {
                    background: rgba(74, 111, 165, 0.3);
                    border-radius: 3px;
                }
                .source-list::-webkit-scrollbar-thumb:hover {
                    background: rgba(74, 111, 165, 0.5);
                }
            </style>
        """, unsafe_allow_html=True)
        
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

        # Full story and source articles
        with st.expander("Full Story", expanded=True):
            st.markdown(st.session_state.article_data['story'], unsafe_allow_html=True)
            
        # Source articles in a more compact format
        with st.expander("Source Articles", expanded=False):
            st.markdown('<div class="source-list">', unsafe_allow_html=True)
            for article in st.session_state.selected_cluster['articles']:
                source_name = article['name_source']
                title = article['title']
                link = article['link']
                st.markdown(f"- **{source_name}**: [{title}]({link})")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Deep Research Options
        st.markdown("""
            <style>
                .research-options {
                    background-color: #1C1C1C;
                    padding: 1rem;
                    border-radius: 8px;
                    border: 1px solid rgba(74, 111, 165, 0.2);
                    margin-bottom: 1rem;
                }
                .research-header {
                    color: #4A6FA5;
                    font-size: 1.1em;
                    margin-bottom: 0.5rem;
                }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔍 Research Tools")
        
        # Keyword Generation Section
        with st.container():
            st.markdown("#### Keywords")
            # Show current keywords if they exist
            if 'optimized_keywords' in st.session_state:
                try:
                    keyword_data = json.loads(st.session_state.optimized_keywords)
                    current_keywords = keyword_data.get('keywords', '')
                except:
                    current_keywords = st.session_state.optimized_keywords
                
                keywords = st.text_area(
                    "Research Keywords",
                    value=current_keywords,
                    help="Edit keywords to refine your research",
                    key="keyword_input"
                )
            else:
                st.info("Generate keywords to start research")
            
            # Generate keywords button
            if st.button("Generate Keywords", key="generate_keywords"):
                with st.spinner("Optimizing headline..."):
                    headline = st.session_state.article_data.get('headline', '')
                    if not headline:
                        st.error("No headline found to generate keywords from")
                        return
                        
                    keywords = optimize_headline_keywords(headline)
                    if keywords:
                        st.session_state.optimized_keywords = keywords
                        st.success("Keywords generated!")
                        st.rerun()
                    else:
                        st.error("Failed to generate keywords")

        st.markdown("---")

        # Research Type Tabs
        current_tab, historical_tab = st.tabs(["Current Context", "Historical Research"])

        with current_tab:
            st.markdown("#### Additional Context")
            # Time range selector for current context
            time_options = ["24h", "3d", "7d", "14d", "30d"]
            selected_time = st.selectbox(
                "Time Range",
                time_options,
                index=0,
                key="current_context_time_range"
            )

            # Search button for current context
            if 'optimized_keywords' in st.session_state:
                if st.button("Find Additional Context", key="search_current_context", use_container_width=True):
                    with st.spinner("Searching for additional context..."):
                        search_keywords = st.session_state.optimized_keywords
                        if isinstance(search_keywords, str):
                            try:
                                keyword_data = json.loads(search_keywords)
                                search_keywords = keyword_data.get('keywords', '').strip()
                            except json.JSONDecodeError:
                                search_keywords = search_keywords.strip()
                        
                        st.session_state.topic = search_keywords
                        st.session_state.last_topic = search_keywords
                        st.session_state.time_range = selected_time
                        
                        for key in list(st.session_state.keys()):
                            if key not in ['topic', 'time_range', 'last_topic']:
                                del st.session_state[key]
                        
                        with st.spinner("Fetching news..."):
                            news_data = get_news_data("Topic", query=search_keywords, when=selected_time)
                            if news_data and 'clusters' in news_data:
                                st.session_state.news_data = news_data
                                st.session_state.is_loading_clusters = True
                                st.session_state.clusters = []
                                st.rerun()
                            else:
                                st.error("No results found. Try adjusting keywords or time range.")

        with historical_tab:
            st.markdown("#### Historical Research")
            # Historical time range options
            historical_time_options = [
                "3 months",
                "6 months",
                "1 year",
                "2 years",
                "5 years",
                "All time"
            ]

            historical_time_range = st.selectbox(
                "Historical Time Range",
                historical_time_options,
                index=0,
                key="historical_time_range"
            )

            # Convert friendly names to API parameters
            historical_time_map = {
                "3 months": "90d",
                "6 months": "180d",
                "1 year": "365d",
                "2 years": "730d",
                "5 years": "1825d",
                "All time": "all"
            }

            # Add advanced filters in an expander
            with st.expander("Advanced Filters", expanded=False):
                # Category filter
                categories = ["All Categories", "Technology", "Politics", "Science", "Economy", "World", "Society"]
                selected_category = st.selectbox(
                    "Category Filter",
                    categories,
                    key="historical_category_filter"
                )
                
                # Bias range filter
                bias_range = st.slider(
                    "Bias Score Range",
                    min_value=-1.0,
                    max_value=1.0,
                    value=(-1.0, 1.0),
                    step=0.1,
                    key="historical_bias_filter"
                )
                
                # Quality score filter
                quality_range = st.slider(
                    "Quality Score Range",
                    min_value=0.0,
                    max_value=10.0,
                    value=(0.0, 10.0),
                    step=0.5,
                    key="historical_quality_filter"
                )

            # Historical Review button
            if st.button("Search Historical Articles", key="historical_review", use_container_width=True):
                with st.spinner("Searching historical archives..."):
                    keywords = st.session_state.get('keyword_input', '')
                    if not keywords:
                        st.error("Please enter keywords in the Research Keywords field above")
                        return
                    
                    # Prepare filters
                    filters = {
                        "page": st.session_state.get('historical_page', 1),
                        "biasRange": bias_range,
                        "qualityRange": quality_range
                    }
                    
                    if selected_category != "All Categories":
                        filters["category"] = selected_category
                    
                    try:
                        results = search_historical_articles(
                            keywords=keywords,
                            time_range=historical_time_map[historical_time_range],
                            filters=filters,
                            api_key=os.environ.get("PUBLISH_API_KEY")
                        )
                        
                        if not results:
                            st.error("No response received from the server")
                            return
                            
                        if isinstance(results, dict):
                            if 'error' in results:
                                st.error(f"Search failed: {results.get('message', 'Unknown error')}")
                                if 'debug' in results:
                                    with st.expander("Debug Information", expanded=False):
                                        st.json(results['debug'])
                                return
                                
                            if 'status' in results and results['status'] == 'success':
                                st.session_state.historical_results = results
                                st.session_state.historical_page = filters["page"]
                                st.rerun()
                    except Exception as e:
                        st.error(f"Failed to connect to historical search service: {str(e)}")
                        st.exception(e)
                        return

            # Display historical results and AI discussion if we have results
            if hasattr(st.session_state, 'historical_results') and st.session_state.historical_results:
                results = st.session_state.historical_results
                total_results = results.get('metadata', {}).get('totalResults', 0)
                
                # Calculate token count for all articles
                total_tokens = 0
                if 'articles' in results and results['articles']:
                    for article in results['articles']:
                        # Estimate tokens (rough estimate: 1 token ≈ 4 characters)
                        headline_tokens = len(article.get('AIHeadline', '')) // 4
                        story_tokens = len(article.get('AIStory', '')) // 4
                        date_tokens = 10  # Date typically uses about 10 tokens
                        total_tokens += headline_tokens + story_tokens + date_tokens

                # Display results summary with token count
                st.info(f"Found {total_results} matching articles. Estimated token count for analysis: {total_tokens:,}")
                
                # Add AI Discussion section
                st.markdown("### AI Discussion")
                
                # Initialize discussion state if not exists
                if 'historical_discussion_message' not in st.session_state:
                    st.session_state.historical_discussion_message = ""
                if 'historical_discussion_response' not in st.session_state:
                    st.session_state.historical_discussion_response = None
                
                # Discussion input
                user_message = st.text_area(
                    "Enter your question or discussion point about the historical context:",
                    value=st.session_state.historical_discussion_message,
                    key="discussion_input",
                    help="Ask about patterns, trends, or specific aspects you'd like to explore"
                )
                
                # Update stored message if changed
                if user_message != st.session_state.historical_discussion_message:
                    st.session_state.historical_discussion_message = user_message
                
                # Create buttons with custom CSS for horizontal layout
                st.markdown("""
                    <style>
                        .horizontal-button-container {
                            display: flex;
                            gap: 1rem;
                            margin: 1rem 0;
                        }
                        .horizontal-button {
                            flex: 1;
                        }
                    </style>
                    <div class="horizontal-button-container">
                        <div class="horizontal-button">
                """, unsafe_allow_html=True)
                
                # Discussion button
                if st.button("Start AI Discussion", key="start_discussion", use_container_width=True):
                    if not user_message:
                        st.warning("Please enter a question or discussion point")
                    else:
                        try:
                            with st.spinner("Analyzing historical context..."):
                                ai_response = discuss_historical_articles(
                                    st.session_state.article_data,
                                    results.get('articles', []),
                                    user_message
                                )
                                
                                if ai_response and isinstance(ai_response, str) and len(ai_response.strip()) > 0:
                                    st.session_state.historical_discussion_response = ai_response
                                    st.markdown("""
                                        <div class="ai-analysis">
                                    """, unsafe_allow_html=True)
                                    st.markdown("### AI Analysis")
                                    st.markdown(ai_response)
                                    st.markdown("</div>", unsafe_allow_html=True)
                                else:
                                    st.error("Failed to get a valid response from AI. Please try again.")
                        except Exception as e:
                            st.error(f"Error during AI discussion: {str(e)}")

                st.markdown('</div><div class="horizontal-button">', unsafe_allow_html=True)
                
                # Generate Story button
                if st.button("Generate Historical Story", key="generate_story", use_container_width=True):
                    try:
                        with st.spinner("Generating comprehensive story with historical context..."):
                            story_data = generate_historical_story(
                                st.session_state.article_data,
                                results.get('articles', []),
                                st.session_state.historical_discussion_message
                            )
                            
                            if story_data and isinstance(story_data, dict):
                                # Update session state with new story
                                st.session_state.article_data.update({
                                    'headline': story_data['AIHeadline'],
                                    'haiku': story_data['AIHaiku'],
                                    'story': story_data['AIStory'],
                                    'summary': story_data['summary']
                                })
                                # Update citations
                                if 'Cited' in story_data:
                                    st.session_state.article_data['Cited'] = story_data['Cited']
                                
                                st.success("Generated new story incorporating historical context!")
                                st.rerun()  # Refresh to show new story
                            else:
                                st.error("Failed to generate story. Please try again.")
                    except Exception as e:
                        st.error(f"Error generating story: {str(e)}")

                st.markdown('</div></div>', unsafe_allow_html=True)
                
                # Display previous AI response if it exists
                if st.session_state.historical_discussion_response:
                    with st.expander("View Previous Analysis", expanded=False):
                        st.markdown("""
                            <div class="ai-analysis previous-analysis">
                        """, unsafe_allow_html=True)
                        st.markdown(st.session_state.historical_discussion_response)
                        st.markdown("</div>", unsafe_allow_html=True)

    # Display the article content with enhanced citation visibility
    st.markdown("### Article Content")
    st.markdown(st.session_state.article_data.get('story', ''), unsafe_allow_html=True)
    
    # Add source reference section
    st.markdown("### Sources")
    for article in st.session_state.selected_cluster['articles']:
        source_id = article.get('source_id', '')
        if source_id:
            st.markdown(f"""
                <div style="margin-bottom: 0.5rem;">
                    <strong>[{source_id}] {article['name_source']}</strong><br>
                    <a href="{article['link']}" class="source-link" target="_blank">{article['title']}</a>
                </div>
            """, unsafe_allow_html=True)

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
        'Cited': cited
    }
    
    # Add evaluation context to the article
    evaluation_context = """
    EVALUATION GUIDELINES:
    1. Quality Assessment should prioritize:
       - Source credibility and reputation
       - Diversity of sources
       - Writing clarity and structure
       - Internal consistency
       - Professional journalistic standards
       - Is the Article of world or social importance (is it worth talking about?)
       - Is there real and actionable information in the article?
       
    2. For current events and rapidly changing situations:
       - Focus on source reliability over fact verification
       - Consider institutional credibility of cited sources
       - Evaluate internal consistency rather than external validation
       - Accept that positions of leaders and current situations may have changed
       - Look for balanced reporting rather than absolute truth claims
       
    3. Bias Assessment should examine:
       - Language and tone
       - Source selection and emphasis
       - Presentation of multiple viewpoints
       - Treatment of controversial topics
       
    4. Propagation Potential should consider:
       - Topic relevance and timeliness
       - Public interest factors
       - Clarity of presentation
       - Engagement potential
    """
    
    article['evaluation_context'] = evaluation_context
    
    try:
        evaluation = evaluate_article_with_ai(article)
        if not evaluation:
            st.error("AI evaluation returned no results")
            return None
            
        evaluation = {
            'quality_score': evaluation.get('quality_score', 0),
            'cat': evaluation.get('cat', 'Unknown'),
            'bs_p': evaluation.get('bs_p', 'Neutral'),
            'reasoning': evaluation.get('reasoning', 'No analysis provided'),
            'topic': evaluation.get('topic', 'Unknown'),
            'trend': evaluation.get('trend', 0.0),
            'hashtags': evaluation.get('hashtags', '')
        }
        return evaluation
        
    except Exception as e:
        st.error(f"AI Evaluation failed: {str(e)}")
        return None

def extract_section(text, section_header):
    if section_header in text:
        sections = text.split(section_header)
        if len(sections) > 1:
            return sections[1].split("\n")[0].strip()
    return ""

def display_review_step():
    """Display the AI review results and article content"""
    headline = st.session_state.article_data.get('headline', '')
    category = st.session_state.evaluation.get('cat', 'Unknown')
    quality_score = st.session_state.evaluation.get('quality_score', 0)
    bias_text = st.session_state.evaluation.get('bs_p', 'Neutral')
    trend_score = st.session_state.evaluation.get('trend', 0.0)
    
    def continue_to_image():
        # Format citations
        sources = []
        for i, article in enumerate(st.session_state.selected_cluster['articles'][:8], 1):
            sources.append([i, article['link']])
        
        # Create publish data
        bias_mapping = {
            'Far Left': -1.0,
            'Left': -0.6,
            'Center Left': -0.3,
            'Neutral': 0.0,
            'Center Right': 0.3,
            'Right': 0.6,
            'Far Right': 1.0
        }
        
        # Convert text bias to numeric value
        bias_text = st.session_state.evaluation.get('bs_p', 'Neutral')
        bias_numeric = bias_mapping.get(bias_text, 0.0)  # Default to 0.0 if not found
        
        st.session_state.publish_data = {
            "AIHeadline": st.session_state.article_data['headline'],
            "AIHaiku": st.session_state.article_data['haiku'],
            "AIStory": st.session_state.article_data['story'],
            "AISummary": st.session_state.article_data['summary'],
            "bs": f"{st.session_state.selected_cluster['category']} | High Confidence | {st.session_state.selected_cluster['subject']}",
            "topic": st.session_state.evaluation.get('topic', st.session_state.selected_cluster['category']),
            "cat": st.session_state.evaluation.get('cat', st.session_state.selected_cluster['subject']),
            "bs_p": bias_numeric,  # Store as numeric value instead of text
            "qas": st.session_state.evaluation.get('quality_score', ''),
            "trend": st.session_state.evaluation.get('trend', 0.0),
            "Cited": json.dumps(sources)
        }
        
        st.session_state.current_step = 3
        
        # Generate both images at once using the unified generator
        with st.spinner("Running image generation..."):
            standard_image, bluesky_image, image_prompt = generate_haiku_images(
                st.session_state.publish_data.get('AIHaiku', ''),
                st.session_state.publish_data.get('AIHeadline', ''),
                st.session_state.publish_data.get('article_date', ''),
                None,  # No existing prompt for initial generation
                None   # No feedback for initial generation
            )
            
            if standard_image and bluesky_image:
                st.session_state.haiku_image_path = standard_image
                st.session_state.bluesky_image_path = bluesky_image
                st.session_state.publish_data['image_prompt'] = image_prompt
                
                # Generate and store encoded images for publishing
                encoded_standard_image, encoded_standard_image_with_text = generate_and_encode_images(
                    "haikubg.png",  # background without text
                    "haikubg_with_text.jpg"  # image with text overlay
                )
                st.session_state.publish_data.update({
                    'image_data': encoded_standard_image,
                    'image_haiku': encoded_standard_image_with_text
                })
                st.session_state.initial_image_generated = True
                
                encoded_bluesky_image, encoded_bluesky_image_with_text = generate_and_encode_images(
                    "bluesky_haikubg.png",  # background without text
                    "bluesky_haikubg_with_text.jpg"  # image with text overlay
                )
                st.session_state.publish_data.update({
                    'bluesky_image_data': encoded_bluesky_image,
                    'bluesky_image_haiku': encoded_bluesky_image_with_text
                })
                st.session_state.initial_bluesky_image_generated = True
                
                st.success("Haiku images generated successfully!")
            else:
                st.error("Failed to generate haiku images")
        
        st.rerun()
    
    def reject_article():
        st.session_state.article_rejected = True
        st.rerun()
    
    def return_to_research():
        """Return to the research/article step while preserving article data"""
        st.session_state.current_step = 1
        # We preserve article_data and selected_cluster
        # but clear evaluation since we're going back for modifications
        if 'evaluation' in st.session_state:
            del st.session_state.evaluation
        st.rerun()
    
    # Check if the article has been rejected
    if st.session_state.article_rejected:
        st.markdown("""
            <div class="rejected-card">
                <h3 class="rejected-text">Article Rejected</h3>
                <p>The article has been rejected and will not be published.</p>
                <div style="margin-top: 1rem;">
                    <strong>Headline:</strong>
                    <p class="rejected-text">{}</p>
                </div>
            </div>
        """.format(
            st.session_state.article_data.get('headline', 'No headline')
        ), unsafe_allow_html=True)
        
        # Reset article state after displaying the rejection message
        reset_article_state()
        return
    
    # Update the buttons to remove the "Provide Feedback" button
    buttons = [
        ("Continue to Image Generation", "continue_to_image", continue_to_image),
        ("Reject Article", "review_reject", reject_article),
        ("Back to Research", "back_to_research", return_to_research)
    ]
    
    # Define color mapping functions
    def get_quality_color(score):
        if score <= 3:
            return "#ff0000"  # Red
        elif score <= 6:
            return "#ffff00"  # Yellow
        else:
            return "#00ff00"  # Green
    
    def get_propagation_color(score):
        if score <= 3:
            return "#ff0000"  # Red
        elif score <= 6:
            return "#ffff00"  # Yellow
        else:
            return "#00ff00"  # Green
    
    # Get color codes for scores
    quality_color = get_quality_color(quality_score)
    
    # Define bias mapping here
    bias_mapping = {
        'Far Left': -1.0,
        'Left': -0.6,
        'Center Left': -0.3,
        'Neutral': 0.0,
        'Center Right': 0.3,
        'Right': 0.6,
        'Far Right': 1.0
    }
    
    bias_color = get_bias_color(bias_mapping.get(bias_text, 0.0))
    propagation_color = get_propagation_color(trend_score)
    
    header_html = f"""
        <style>
            .step-header {{
                margin-bottom: 1rem;
            }}
            .headline-text {{
                font-size: 1.5rem;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }}
            .subheader-text {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
            }}
            .category {{
                color: rgba(192, 160, 128, 0.8);
                font-size: 1rem;
            }}
            .topic {{
                color: rgba(128, 160, 192, 0.8);
                font-size: 1rem;
            }}
            .scores {{
                display: flex;
                gap: 1rem;
                align-items: center;
                color: rgba(255, 255, 255, 0.7);
            }}
            .score {{
                font-weight: 500;
            }}
            .quality-score {{
                color: {'#ff0000' if quality_score < 6 else 'rgba(0, 255, 0, 0.7)'};
            }}
            .bias-score {{
                color: rgba(255, 255, 255, 0.7);
            }}
            .propagation-score {{
                color: rgba(0, 255, 0, 0.7);
            }}
        </style>
        <div class="step-header">
            <div class="headline-text">{headline}</div>
            <div class="subheader-text">
                <div>
                    <span class="category">{category}</span>
                    <span class="topic"> | {st.session_state.article_data.get('topic', 'Unknown Topic')}</span>
                </div>
                <div class="scores">
                    <span class="score quality-score">Quality: {quality_score:.1f}/10</span>
                    <span class="score bias-score">Bias: {bias_text}</span>
                    <span class="score propagation-score">Propagation: {trend_score:.1f}/10</span>
                </div>
            </div>
        </div>
        <div class="action-buttons">
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Create columns for buttons
    cols = st.columns(len(buttons))
    for col, (label, key, callback) in zip(cols, buttons):
        with col:
            if st.button(label, key=key):
                callback()
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    eval_data = st.session_state.evaluation
    
    if not eval_data:
        st.error("No evaluation data available")
        return
    
    try:
        # Get current article identifier (using headline as unique identifier)
        current_article = st.session_state.article_data.get('headline', '')
        
        # Check if this is a new article, first load, or re-evaluation after feedback
        is_new_article = (
            'review_step_initialized' not in st.session_state or
            'last_reviewed_article' not in st.session_state or
            current_article != st.session_state.last_reviewed_article
        )
        
        if is_new_article:
            # Set the sidebar category filter based on the evaluated article's category
            article_category = eval_data.get('cat', '').strip()
            
            # Normalize category formatting
            if article_category:
                # Convert to title case and handle special cases
                article_category = article_category.title()
                
                # Special case handling for common abbreviations
                special_cases = {
                    "Ai": "AI",
                    "Usa": "USA",
                    "Uk": "UK",
                    # Add more special cases as needed
                }
                
                for case in special_cases:
                    article_category = article_category.replace(case, special_cases[case])
                
                # Update category and reset pagination
                st.session_state.selected_category = article_category
                st.session_state.headline_page = 1
            else:
                # Reset to all categories if no category found
                st.session_state.selected_category = "All Categories"
                st.session_state.headline_page = 1
            
            # Mark review step as initialized and store current article
            st.session_state.review_step_initialized = True
            st.session_state.last_reviewed_article = current_article
            # Force a rerun to apply the category change
            st.rerun()
        
        # Create two columns for AI response and feedback
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Create tabs for different analysis aspects
            quality_tab, bias_tab, prop_tab, hashtag_tab, reasoning_tab = st.tabs([
                 "Quality", "Bias", "Propagation", "Hashtags", "Raw Reasoning"
            ])
            
            with quality_tab:
                quality_score = eval_data.get('quality_score', 0)
                try:
                    quality_score = float(quality_score)
                except (ValueError, TypeError):
                    quality_score = 0.0
                
                # Extract quality-related content from reasoning
                reasoning = eval_data.get('reasoning', '')
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
                bias_text = eval_data.get('bs_p', 'Neutral')
                # Convert text to numeric value
                bias_mapping = {
                    'Far Left': -1.0,
                    'Left': -0.6,
                    'Center Left': -0.3,
                    'Neutral': 0.0,
                    'Center Right': 0.3,
                    'Right': 0.6,
                    'Far Right': 1.0
                }
                bias_numeric = bias_mapping.get(bias_text, 0.0)
                
                # Extract bias-related content from reasoning
                bias_analysis = ""
                
                # Look for the Bias Analysis section
                if "Bias Analysis:" in reasoning:
                    sections = reasoning.split("Bias Analysis:")
                    if len(sections) > 1:
                        bias_section = sections[1].split("Propagation Potential:")[0].strip()
                        bias_analysis = bias_section
                
                if not bias_analysis:
                    bias_analysis = f"""
                        The bias score indicates political lean:
                        - Score {bias_numeric:+.1f} on scale from -1.0 (far left) to +1.0 (far right)
                        - Based on source analysis and content evaluation
                        - Considers perspective balance
                        - Evaluates partisan language
                    """
                
                st.markdown(f"""
                    ### Bias Assessment: {bias_numeric:+.1f}
                    
                    {bias_analysis}
                """)
            
            with prop_tab:
                trend_score = eval_data.get('trend', 0.0)
                if isinstance(trend_score, str):
                    try:
                        trend_score = float(trend_score)
                    except (ValueError, TypeError):
                        trend_score = 0.0
                
                # Extract propagation-related content from reasoning
                prop_analysis = ""
                
                # Look for the Propagation Potential section
                if "Propagation Potential:" in reasoning:
                    sections = reasoning.split("Propagation Potential:")
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
            
            with hashtag_tab:
                hashtags = eval_data.get('hashtags', '')
                st.markdown(f"""
                    ### Recommended Hashtags
                    
                    {hashtags}
                """)
            
            with reasoning_tab:
                reasoning = eval_data.get('reasoning', 'No analysis provided')
                st.markdown(f"""
                    ### Raw Reasoning
                    
                    {reasoning}
                """)
        
        with col2:
            st.markdown("### Provide Feedback")
            feedback = st.text_area("Enter your feedback on the AI review:")
            
            if st.button("Submit Feedback"):
                with st.spinner("Re-evaluating article based on feedback..."):
                    # Create a new chat message with the original evaluation and user feedback
                    message = f"""
                    Original Evaluation:
                    {json.dumps(st.session_state.evaluation, indent=2)}
                    
                    User Feedback:
                    {feedback}
                    
                    Please consider the above feedback and re-evaluate the article, providing an updated evaluation in the same format as the original.
                    """
                    
                    # Send the message to the AI for re-evaluation
                    updated_evaluation = evaluate_article_with_ai(st.session_state.article_data, message)
                    
                    if updated_evaluation:
                        st.session_state.evaluation = updated_evaluation
                        st.success("Article re-evaluated based on feedback!")
                    else:
                        st.error("Failed to re-evaluate article based on feedback")
                    
                    st.session_state.feedback_mode = False
                    st.rerun()
        
        # Add story summary below the AI response and feedback sections
        st.markdown("### Story Summary")
        st.markdown(st.session_state.article_data['story'], unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"Error displaying evaluation results: {str(e)}")
    
    # Pagination for published headlines
    if 'headline_page' not in st.session_state:
        st.session_state.headline_page = 1
    
    def prev_page():
        st.session_state.headline_page = max(1, st.session_state.headline_page - 1)
    
    def next_page():
        st.session_state.headline_page += 1
    
    # Custom CSS for pagination styling
    st.markdown("""
        <style>
            div.stButton > button {
                width: 100%;
            }
            div.stButton > button:hover {
                background-color: #e0e2e6;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Custom CSS for button styling
    st.markdown("""
        <style>
            div.stButton > button {
                width: 100%;
                padding: 0.5rem;
                border-radius: 0.25rem;
                background-color: #4A6FA5;
                color: white;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }
            div.stButton > button:hover {
                background-color: #3E5E8E;
            }
        </style>
    """, unsafe_allow_html=True)

def display_image_step():
    """Display the haiku image generation step"""
    headline = st.session_state.publish_data.get('AIHeadline', '')
    category = st.session_state.publish_data.get('cat', 'Unknown')
    quality_score = st.session_state.publish_data.get('qas', 0)
    bias_text = st.session_state.publish_data.get('bs_p', 'Neutral')
    trend_score = st.session_state.publish_data.get('trend', 0.0)
    
    def regenerate_image():
        # Get user feedback if provided
        feedback = st.session_state.get('image_feedback', '')
        
        with st.spinner("Generating new images..."):
            # Get haiku and metadata from session state
            haiku = st.session_state.publish_data.get('AIHaiku', '')
            headline = st.session_state.publish_data.get('AIHeadline', '')
            article_date = st.session_state.publish_data.get('article_date', '')
            
            # Generate both images using the unified generator
            standard_image, bluesky_image, image_prompt = generate_haiku_images(
                haiku,
                headline,
                article_date,
                None,  # Don't reuse previous prompt when regenerating
                feedback
            )
            
            if standard_image and bluesky_image:
                # Update session state with new image paths
                st.session_state.haiku_image_path = standard_image
                st.session_state.bluesky_image_path = bluesky_image
                
                # Update publish data with new image prompt
                st.session_state.publish_data['image_prompt'] = image_prompt
                
                # Generate and store encoded images for publishing
                encoded_standard_image, encoded_standard_image_with_text = generate_and_encode_images(
                    "haikubg.png",  # background without text
                    "haikubg_with_text.jpg"  # image with text overlay
                )
                st.session_state.publish_data.update({
                    'image_data': encoded_standard_image,
                    'image_haiku': encoded_standard_image_with_text
                })
                
                encoded_bluesky_image, encoded_bluesky_image_with_text = generate_and_encode_images(
                    "bluesky_haikubg.png",  # background without text
                    "bluesky_haikubg_with_text.jpg"  # image with text overlay
                )
                st.session_state.publish_data.update({
                    'bluesky_image_data': encoded_bluesky_image,
                    'bluesky_image_haiku': encoded_bluesky_image_with_text
                })
                
                # Save updated publish data to file
                with open('publish.json', 'w') as f:
                    json.dump(st.session_state.publish_data, f, indent=2)
            else:
                st.error("Failed to generate new images")
    
    def continue_to_final():
        st.session_state.current_step = 4
        st.rerun()
    
    buttons = [
        ("Regenerate Images", "regenerate_image", regenerate_image),
        ("Continue to Final Review", "image_continue_review", continue_to_final)
    ]
    
    # Show current prompt if it exists
    current_prompt = st.session_state.publish_data.get('image_prompt', '')
    if current_prompt:
        with st.expander("Current Image Prompt", expanded=False):
            st.info(current_prompt)
    
    # Add feedback input before the buttons
    st.text_area(
        "Image Feedback (optional)",
        key="image_feedback",
        help="Provide feedback to guide the image regeneration (e.g., 'make it more abstract', 'use warmer colors', etc.)"
    )

    # Define color mapping functions
    def get_quality_color(score):
        if score <= 3:
            return "#ff0000"  # Red
        elif score <= 6:
            return "#ffff00"  # Yellow
        else:
            return "#00ff00"  # Green
    
    def get_propagation_color(score):
        if score <= 3:
            return "#ff0000"  # Red
        elif score <= 6:
            return "#ffff00"  # Yellow
        else:
            return "#00ff00"  # Green
    
    # Define bias mapping here
    bias_mapping = {
        'Far Left': -1.0,
        'Left': -0.6,
        'Center Left': -0.3,
        'Neutral': 0.0,
        'Center Right': 0.3,
        'Right': 0.6,
        'Far Right': 1.0
    }
    
    # Get color codes for scores
    quality_color = get_quality_color(quality_score)
    bias_color = get_bias_color(bias_mapping.get(bias_text, 0.0))
    propagation_color = get_propagation_color(trend_score)
    
    header_html = f"""
        <style>
            .step-header {{
                margin-bottom: 1rem;
            }}
            .headline-text {{
                font-size: 1.5rem;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }}
            .subheader-text {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 1rem;
            }}
            .category {{
                color: rgba(192, 160, 128, 0.8);
                font-size: 1rem;
            }}
            .topic {{
                color: rgba(128, 160, 192, 0.8);
                font-size: 1rem;
            }}
            .scores {{
                display: flex;
                gap: 1rem;
                align-items: center;
                color: rgba(255, 255, 255, 0.7);
            }}
            .score {{
                font-weight: 500;
            }}
            .quality-score {{
                color: {'#ff0000' if quality_score < 6 else 'rgba(0, 255, 0, 0.7)'};
            }}
            .bias-score {{
                color: rgba(255, 255, 255, 0.7);
            }}
            .propagation-score {{
                color: rgba(0, 255, 0, 0.7);
            }}
        </style>
        <div class="step-header">
            <div class="headline-text">{headline}</div>
            <div class="subheader-text">
                <div>
                    <span class="category">{category}</span>
                    <span class="topic"> | {st.session_state.article_data.get('topic', 'Unknown Topic')}</span>
                </div>
                <div class="scores">
                    <span class="score quality-score">Quality: {quality_score:.1f}/10</span>
                    <span class="score bias-score">Bias: {bias_text}</span>
                    <span class="score propagation-score">Propagation: {trend_score:.1f}/10</span>
                </div>
            </div>
        </div>
        <div class="action-buttons">
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Custom CSS for button styling
    st.markdown("""
        <style>
            div.stButton > button {
                width: 100%;
                padding: 0.5rem;
                border-radius: 0.25rem;
                background-color: #4A6FA5;
                color: white;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }
            div.stButton > button:hover {
                background-color: #3E5E8E;
            }
            .published-card {
                background-color: #2c3e50;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-top: 1rem;
                color: rgba(255, 255, 255, 0.8);
            }
            .rejected-text {
                color: #e74c3c;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Create columns for buttons
    cols = st.columns(len(buttons))
    for col, (label, key, callback) in zip(cols, buttons):
        with col:
            if st.button(label, key=key):
                callback()
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    if not st.session_state.publish_data:
        st.error("No publication data available for image generation")
        reset_article_state()
        return
    
    # Main content
    st.markdown("#### Haiku Visualizations")
    
    col1, col2 = st.columns([2, 1])
    
    image_label_style = """
        <style>
            .image-label {
                margin-bottom: 0.5rem;
            }
        </style>
    """
    st.markdown(image_label_style, unsafe_allow_html=True)
    
    with col1:
        st.markdown('<div class="image-label">Standard Image</div>', unsafe_allow_html=True)
        # Check if haiku_image_path exists in session state before displaying
        if st.session_state.haiku_image_path:
            container_style = """
                <style>
                    [data-testid="stImage"] {
                        width: 100%;
                        margin: 0 auto;
                        display: block;
                    }
                    [data-testid="stImage"] img {
                        border-radius: 8px;
                        object-fit: contain;
                    }
                </style>
            """
            st.markdown(container_style, unsafe_allow_html=True)
            st.image(st.session_state.haiku_image_path, caption="", use_container_width=False)
        else:
            st.warning("No standard image available. Please try regenerating the images.")
    
    with col2:
        st.markdown('<div class="image-label">Bluesky Image</div>', unsafe_allow_html=True)
        # Check if bluesky_image_path exists in session state before displaying
        if st.session_state.bluesky_image_path:
            container_style = """
                <style>
                    [data-testid="stImage"] {
                        width: 100%;
                        margin: 0 auto;
                        display: block;
                    }
                    [data-testid="stImage"] img {
                        border-radius: 8px;
                    }
                </style>
            """
            st.markdown(container_style, unsafe_allow_html=True)
            st.image(st.session_state.bluesky_image_path, caption="", use_container_width=False)
        else:
            st.warning("No Bluesky image available. Please try regenerating the images.")
    
    with st.expander("Image Prompt", expanded=False):
        st.info(st.session_state.publish_data.get('image_prompt', ''))
    
    # Clear status after image generation
    if st.session_state.haiku_image_path and st.session_state.bluesky_image_path:
        st.empty()

def display_final_review():
    """Display final review before publication"""
    # Reset publication status on entry
    st.session_state.publication_success = False
    
    # Ensure we have publish data
    if not st.session_state.publish_data:
        st.error("No publication data available")
        reset_article_state()
        return

    headline = st.session_state.publish_data.get('AIHeadline', '')
    category = st.session_state.publish_data.get('cat', 'Unknown')
    quality_score = st.session_state.publish_data.get('qas', 0)
    bias_text = st.session_state.publish_data.get('bs_p', 'Neutral')
    trend_score = st.session_state.publish_data.get('trend', 0.0)
    
    def publish_article_action():
        with st.spinner("Publishing article..."):
            # Create clean copy of publish data without image blobs
            clean_publish_data = st.session_state.publish_data.copy()
            clean_publish_data.update({
                'image_data': None,
                'image_haiku': None,
                'bluesky_image_data': None,
                'bluesky_image_haiku': None
            })
            
            article_id = publish_article(
                clean_publish_data,  # Use cleaned data instead of original
                os.environ.get("PUBLISH_API_KEY")
            )
            
            if article_id:
                st.session_state.publication_success = True
                st.session_state.published_article_id = article_id
                st.session_state.published_article_url = f"https://ainewsbrew.com/article/{article_id}"
                st.success(f"""Article published successfully! 
                    \nID: {article_id}
                    \nView at: [{st.session_state.published_article_url}]({st.session_state.published_article_url})""")
                
                # Upload images to FTP after getting article ID
                with st.spinner("Uploading images to FTP..."):
                    from modules.ftp_image_handler import upload_images_to_ftp
                    try:
                        # Use the base64 encoded images from publish_data
                        bg_url, haiku_url = upload_images_to_ftp(
                            article_id,
                            st.session_state.publish_data.get('image_data'),  # Base64 encoded background image
                            st.session_state.publish_data.get('image_haiku')  # Base64 encoded haiku image
                        )
                        if not bg_url or not haiku_url:
                            st.error("Failed to upload images to FTP - no URLs returned")
                        else:
                            st.success("Images uploaded successfully")
                            
                            # Now publish to social media
                            with st.spinner("Publishing to social media..."):
                                # Get the haiku and hashtags
                                haiku = st.session_state.publish_data.get('AIHaiku', '')
                                headline = st.session_state.publish_data.get('AIHeadline', '')
                                article_url = st.session_state.published_article_url
                                hashtags = st.session_state.evaluation.get('hashtags', '')
                                
                                # Initialize social media status
                                st.session_state.bluesky_success = False
                                st.session_state.instagram_success = False
                                
                                # Publish to Bluesky
                                image_path = "bluesky_haikubg_with_text.jpg"
                                bluesky_result = publish_to_bluesky(haiku, article_url, image_path, hashtags, headline)
                                st.session_state.bluesky_success = bool(bluesky_result)
                                if bluesky_result:
                                    st.success("Article posted successfully to Bluesky!")
                                else:
                                    st.error("Failed to post to Bluesky")
                                
                                # Publish to Instagram
                                try:
                                    instagram = InstagramPublisher()
                                    # Use the square Bluesky image for Instagram
                                    image_path = "bluesky_haikubg_with_text.jpg"
                                    
                                    # Format Instagram caption
                                    instagram_caption = f"""{haiku}

Read more: {article_url}

{hashtags}"""
                                    
                                    instagram_result = instagram.publish_post(image_path, instagram_caption, headline)
                                    st.session_state.instagram_success = bool(instagram_result)
                                    if instagram_result:
                                        st.success("Article posted successfully to Instagram!")
                                    else:
                                        st.error("Failed to post to Instagram")
                                    
                                except Exception as e:
                                    st.error(f"Error posting to Instagram: {str(e)}")
                                    st.session_state.instagram_success = False
                    
                    except Exception as e:
                        st.error(f"Failed to upload images to FTP: {str(e)}")
                
            else:
                st.error("Failed to publish article")
                return
    
    # Check if the article has been published or rejected in the current session
    is_published = st.session_state.get('publication_success', False)
    is_rejected = st.session_state.get('article_rejected', False)
    
    # Custom CSS for button styling
    st.markdown("""
        <style>
            div.stButton > button {
                width: 100%;
                padding: 0.5rem;
                border-radius: 0.25rem;
                background-color: #4A6FA5;
                color: white;
                font-weight: bold;
                margin-bottom: 0.5rem;
            }
            div.stButton > button:hover {
                background-color: #3E5E8E;
            }
            .published-card {
                background-color: #2c3e50;
                padding: 1rem;
                border-radius: 0.5rem;
                margin-top: 1rem;
                color: rgba(255, 255, 255, 0.8);
            }
            .rejected-text {
                color: #e74c3c;
            }
            .button-container {
                display: flex;
                gap: 1rem;
                margin-top: 1rem;
            }
            .button-container > div {
                flex: 1;
            }
        </style>
    """, unsafe_allow_html=True)
    
    if is_rejected:
        st.markdown("""
            <div class="rejected-card">
                <h3 class="rejected-text">Article Rejected</h3>
                <p>The article has been rejected and will not be published.</p>
                <div style="margin-top: 1rem;">
                    <strong>Headline:</strong>
                    <p class="rejected-text">{}</p>
                </div>
            </div>
        """.format(
            st.session_state.publish_data.get('AIHeadline', 'No headline')
        ), unsafe_allow_html=True)
        
        # Reset article state after displaying the rejection message
        reset_article_state()
        return
    
    elif is_published:
        is_published = st.session_state.get('publication_success', False)
        st.markdown("""
            <div class="published-card">
                <div style="display: flex; align-items: center;">
                    <div style="flex: 1;">
                        <h3>Article Published Successfully!</h3>
                        <p>Your article has been published to AI News Brew.</p>
                        <div class="article-links">
                            <div>
                                <strong>Article ID:</strong> 
                                <span class="article-id">{}</span>
                            </div>
                            <div>
                                <strong>View Article:</strong>
                                <a href="{}" target="_blank" class="article-url">{}</a>
                            </div>
                        </div>
                        <div class="social-status">
                            <div class="social-platform">
                                <strong>Bluesky Post:</strong>
                                <span class="{}">
                                    {}
                                </span>
                            </div>
                            <div class="social-platform">
                                <strong>Instagram Post:</strong>
                                <span class="{}">
                                    {}
                                </span>
                            </div>
                        </div>
                    </div>
                    <div class="article-image">
                        <img src="{}" alt="Article Haiku Image" style="width: 30vw; margin-left: 2rem;" />
                    </div>
                </div>
            </div>
            <style>
                .published-card {
                    position: relative;
                    z-index: 100;
                    margin: 2rem 0;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                }
                .published-card h3 {
                    color: #4A6FA5;
                    margin-bottom: 0.5rem;
                }
                .article-image {
                    text-align: center;
                }
                .article-image img {
                    max-width: 100%;
                    border-radius: 4px;
                }
                .article-links {
                    margin-top: 1rem;
                }
                .article-links > div {
                    margin-bottom: 0.5rem;
                }
                .article-id {
                    font-family: monospace;
                    font-size: 0.9em;
                    color: rgba(255, 255, 255, 0.7);
                }
                .article-url {
                    color: #4A6FA5;
                }
                .social-status {
                    margin-top: 1rem;
                }
                .social-platform {
                    margin-top: 0.5rem;
                }
                .success {
                    color: #2ecc71;
                }
                .error {
                    color: #e74c3c;
                }
            </style>
        """.format(
            st.session_state.published_article_id,
            st.session_state.published_article_url,
            st.session_state.published_article_url,
            "success" if st.session_state.get('bluesky_success', False) else "error",
            "Posted successfully" if st.session_state.get('bluesky_success', False) else "Failed to post",
            "success" if st.session_state.get('instagram_success', False) else "error",
            "Posted successfully" if st.session_state.get('instagram_success', False) else "Failed to post",
            st.session_state.publish_data.get('image_haiku', '')
        ), unsafe_allow_html=True)
    
    else:
        # Show the article content and publication buttons
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("### Article Content")
            st.markdown(f"**Headline:** {st.session_state.publish_data.get('AIHeadline', 'No headline')}")
            st.markdown(f"**Category:** {st.session_state.publish_data.get('cat', 'No category')}")
            st.markdown(f"**Topic:** {st.session_state.publish_data.get('topic', 'No topic')}")
            
            # Display haiku image with styling
            if st.session_state.haiku_image_path:
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
                st.image(st.session_state.haiku_image_path, caption="Haiku Visualization")
            else:
                st.warning("No haiku image available")
            
            # Display the article summary
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
            
            # Add Propagation Index metric
            try:
                trend_score = float(st.session_state.publish_data.get('trend', 0))
                st.metric("Propagation Index", f"{trend_score:.1f}/10")
            except (ValueError, TypeError):
                st.metric("Propagation Index", "N/A")
            
            # Add expander for full article content
            with st.expander("View Full Article", expanded=False):
                st.markdown(st.session_state.publish_data.get('AIStory', 'No content'), unsafe_allow_html=True)
            
            # Add buttons without nested columns
            st.markdown('<div class="button-container">', unsafe_allow_html=True)
            if st.button("Publish Article", key="final_review_publish", use_container_width=True):
                publish_article_action()
            if st.button("Cancel Publication", key="final_review_cancel", use_container_width=True):
                st.session_state.article_rejected = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def handle_feedback():
    st.markdown("### Provide Feedback")
    feedback = st.text_area("Enter your feedback on the AI review:")
    
    if st.button("Submit Feedback"):
        with st.spinner("Re-evaluating article based on feedback..."):
            # Create a new chat message with the original evaluation and user feedback
            message = f"""
            Original Evaluation:
            {json.dumps(st.session_state.evaluation, indent=2)}
            
            User Feedback:
            {feedback}
            
            Please consider the above feedback and re-evaluate the article, providing an updated evaluation in the same format as the original.
            """
            
            # Send the message to the AI for re-evaluation
            updated_evaluation = evaluate_article_with_ai(st.session_state.article_data, message)
            
            if updated_evaluation:
                st.session_state.evaluation = updated_evaluation
                st.success("Article re-evaluated based on feedback!")
            else:
                st.error("Failed to re-evaluate article based on feedback")
            
            st.session_state.feedback_mode = False
            st.rerun()

def discuss_historical_articles(current_article, historical_articles, user_message):
    """Discuss historical articles with AI"""
    try:
        if not current_article or not historical_articles:
            raise ValueError("Missing required article data for discussion")

        # Get current date
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Format historical articles data
        historical_data = []
        for article in historical_articles:
            if article.get('AIHeadline') and article.get('Published'):
                historical_data.append({
                    "headline": article.get('AIHeadline', ''),
                    "published_date": article.get('Published', ''),
                    "category": article.get('category', '')
                })
        
        if not historical_data:
            raise ValueError("No valid historical articles found for discussion")

        # Create prompt for AI discussion
        prompt = f"""
        You are analyzing a CURRENT ARTICLE in the context of historical coverage on similar topics.  Your job is to take into account both the included context and recent events and insights from your understanding of the past around similar topics.  Your feedback should be insightful and forward thinking.  You should look to offer an AI's insight into what the outcomes of these predictions might be and impacts.
        Today's Date: {current_date}
        
        CURRENT ARTICLE UNDER ANALYSIS:
        ==============================
        Title: {current_article.get('headline', '')}
        
        Content:
        {current_article.get('story', '')}
        ==============================

        HISTORICAL CONTEXT:
        The following {len(historical_data)} articles provide historical context for analysis.
        Note: Consider the temporal distance between these articles and today ({current_date}):
        {json.dumps(historical_data, indent=2)}

        USER QUESTION:
        {user_message}

        RESPONSE FORMAT:
        The AI should respond to the user conversationally (with a conversational tone) as an assistance exploring the subject with the user  while considering:
        - Deep understanding of the historical context
        - Relevance to the current article's focus
        - Temporal relationships between events
        - Significant patterns or anomalies
        - Potential implications and outcomes - provide a probability assessment score to a potential outcome (and give impact assessment)
        - Nuetral bias and objective analysis - allowed to speak bluntly and candidly to some aspects as long as the perspective is mentioned.
        
        Guidelines:
        - Respond in whatever format best serves the query
        - Use natural organizational patterns rather than forced sections
        - Maintain professional but engaging tone
        - Integrate historical insights organically
        - Focus on substance over rigid structure
        - Allow the analysis to dictate the format
        - Prioritize clarity and insightfulness
        """

        # Get AI response
        response = chat_with_codegpt(prompt)
        
        if not response:
            raise ValueError("Received empty response from AI")
        elif not isinstance(response, str):
            raise ValueError(f"Received invalid response type from AI: {type(response)}")
        elif len(response.strip()) == 0:
            raise ValueError("Received empty string from AI")
            
        return response

    except ValueError as ve:
        st.error(f"Validation Error: {str(ve)}")
        return None
    except Exception as e:
        st.error(f"Error in historical discussion: {str(e)}")
        st.exception(e)
        return None

def generate_historical_story(current_article, historical_articles, user_message):
    """Generate a new story incorporating historical context"""
    try:
        if not current_article or not historical_articles:
            raise ValueError("Missing required article data for story generation")

        # Get current date
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Calculate temporal statistics
        dates = []
        for article in historical_articles:
            if article.get('Published'):
                try:
                    # Convert date string to datetime object
                    pub_date = datetime.strptime(article['Published'], '%b %d, %Y')
                    dates.append(pub_date)
                except (ValueError, TypeError):
                    continue
        
        if dates:
            oldest_date = min(dates).strftime('%B %d, %Y')
            newest_date = max(dates).strftime('%B %d, %Y')
            date_range = f"spanning from {oldest_date} to {newest_date}"
            total_articles = len(historical_articles)
        else:
            date_range = "from recent archives"
            total_articles = len(historical_articles)

        # Get search keywords from session state
        keywords = st.session_state.get('keyword_input', 'relevant topics')

        # Collect all citations
        citations = []
        # Add current article citations
        if st.session_state.selected_cluster and 'articles' in st.session_state.selected_cluster:
            for i, article in enumerate(st.session_state.selected_cluster['articles'], 1):
                citations.append([i, article['link']])
        
        # Add historical article citations
        start_idx = len(citations) + 1
        for i, article in enumerate(historical_articles, start_idx):
            if 'link' in article:
                citations.append([i, article['link']])

        # Format historical articles data
        historical_data = []
        for article in historical_articles:
            if article.get('AIHeadline') and article.get('Published'):
                historical_data.append({
                    "headline": article.get('AIHeadline', ''),
                    "content": article.get('AIStory', ''),
                    "published_date": article.get('Published', ''),
                    "category": article.get('category', '')
                })

        # Create attribution footnote with temporal stats
        # URL encode the keywords for the research link
        encoded_keywords = urllib.parse.quote(keywords.replace(' ', ','))
        research_url = f"https://www.ainewsbrew.com/research?q={encoded_keywords}"
        
        attribution_footnote = f"""
          <div class="ai-attribution">
            <hr>
            <p class="footnote">This article was synthesized by AI from AI News Brew's research archives on {current_date}. 
            The analysis incorporates {total_articles} historical articles {date_range}, researched using the query "{keywords}". 
            It combines current reporting with historical analysis to provide a comprehensive perspective on the topic. 
            All facts and quotes are derived from cited sources. <a href="{research_url}" target="_blank">Explore more research on this topic</a>.</p>
          </div>
        """

        # Create prompt for story generation
        prompt = f"""
        You are giving an AI research journalist's perspective on a news topic that incorporates both current events and recent historical context. You job is to understand the user's question and provide a comprehensive and engaging story that incorporates both the current events and the historical context.  
        Today's Date: {current_date}
        
        CURRENT ARTICLE CONTEXT:
        =======================
        Title: {current_article.get('headline', '')}
        Content: {current_article.get('story', '')}
        
        HISTORICAL CONTEXT:
        Articles from the past, leading up to today ({current_date}):
        {json.dumps(historical_data, indent=2)}

        USER QUESTION/DIRECTION:
        {user_message}
        
        TEMPORAL CONTEXT:
        - Analysis covers articles {date_range}
        - Total historical articles referenced: {total_articles}
        - Search keywords: "{keywords}"
        
        REQUIREMENTS:
        1. Create a JSON response with the following structure:
        {{
            "AIHeadline": "Headline must start with 'AI Perspective:' and then an engaging and informative headline",
            "AIHaiku": "relevant haiku in 5-7-5 format",
            "AIStory": "full story in HTML format",
            "summary": "brief one-paragraph summary"
        }}
        
        2. Story Guidelines:
        - Blend current developments with historical perspective
        - Use semantic HTML tags for structure
        - Include relevant quotes and attributions
        - Maintain objective, balanced reporting
        - Focus on patterns and developments over time
        - Highlight significant changes or consistencies
        - Consider temporal relevance to today
        - End with this exact attribution footnote:
          {attribution_footnote}
        
        3. Haiku Guidelines:
        - Capture the essence of the story's historical significance
        - Follow 5-7-5 syllable format
        - Be insightful while remaining relevant
        - Consider the current moment in time
        
        4. Writing Style:
        - Professional journalistic tone
        - Clear and engaging narrative flow
        - Proper attribution of sources
        - Balance between current events and historical context
        - Emphasize temporal context and relevance to today
        - Reference the temporal span of sources when discussing historical patterns
        """

        # Get AI response
        response = chat_with_codegpt(prompt)
        
        if not response:
            raise ValueError("Received empty response from AI")
            
        # Parse JSON response
        try:
            story_data = json.loads(response)
            # Add citations to the story data
            story_data['Cited'] = json.dumps(citations)
            return story_data
        except json.JSONDecodeError:
            raise ValueError("Failed to parse AI response as JSON")

    except Exception as e:
        st.error(f"Error generating historical story: {str(e)}")
        return None