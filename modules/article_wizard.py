"""Article generation and review wizard"""
import streamlit as st
from .display import get_bias_color
from .article_evaluation import evaluate_article_with_ai
from publish_utils import publish_article, generate_and_encode_images
from .utils import reset_article_state
from .haiku_image_generator import generate_haiku_background
from .bluesky_haiku_image_generator import generate_bluesky_haiku_background
from .bluesky_publish import publish_to_bluesky
import json
import os
import base64

def create_step_header(headline, buttons):
    """Create consistent header with headline and action buttons"""
    # Format the headline string with proper HTML escaping
    formatted_headline = headline.replace('"', '&quot;').replace("'", "&#39;")
    
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
                <span class="category">{category}</span>
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
    col1, col2 = st.columns([1.2, 2.6])
    
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
    
    with col2:
        st.markdown("#### Summary")
        st.markdown(st.session_state.article_data['summary'])
        
        with st.expander("Full Story", expanded=False):
            st.markdown(st.session_state.article_data['story'], unsafe_allow_html=True)
            
        with st.expander("Source Articles", expanded=False):
            for article in st.session_state.selected_cluster['articles']:
                st.markdown(f"- [{article['title']}]({article['link']}) - {article['name_source']}")
    
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
        
        # Trigger image generation when entering step 3
        with st.spinner("Generating initial haiku image..."):
            image_path, image_prompt = generate_haiku_background(
                st.session_state.publish_data.get('AIHaiku', ''),
                st.session_state.publish_data.get('AIHeadline', ''),
                st.session_state.publish_data.get('article_date', '')
            )
            if image_path:
                st.session_state.haiku_image_path = image_path
                st.session_state.publish_data['image_prompt'] = image_prompt
                st.success("Initial haiku image generated successfully!")
                
                encoded_image, encoded_image_with_text = generate_and_encode_images(
                    image_path,
                    "haikubg_with_text.png"
                )
                st.session_state.publish_data.update({
                    'image_data': encoded_image,
                    'image_haiku': encoded_image_with_text
                })
                st.session_state.initial_image_generated = True
            else:
                st.error("Failed to generate initial haiku image")
        
        # Trigger Bluesky image generation when entering step 3
        with st.spinner("Generating initial Bluesky haiku image..."):
            bluesky_image_path, _ = generate_bluesky_haiku_background(
                st.session_state.publish_data.get('AIHaiku', ''),
                st.session_state.publish_data.get('AIHeadline', ''),
                st.session_state.publish_data.get('article_date', '')
            )
            if bluesky_image_path:
                st.session_state.bluesky_image_path = bluesky_image_path
                st.success("Initial Bluesky haiku image generated successfully!")
                
                encoded_bluesky_image, encoded_bluesky_image_with_text = generate_and_encode_images(
                    bluesky_image_path,
                    "bluesky_haikubg_with_text.png"
                )
                st.session_state.publish_data.update({
                    'bluesky_image_data': encoded_bluesky_image,
                    'bluesky_image_haiku': encoded_bluesky_image_with_text
                })
                st.session_state.initial_bluesky_image_generated = True
            else:
                st.error("Failed to generate initial Bluesky haiku image")
        
        st.rerun()
    
    def reject_article():
        st.session_state.article_rejected = True
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
        ("Reject Article", "review_reject", reject_article)
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
                color: {'#ff0000' if trend_score < 8 else 'rgba(0, 255, 0, 0.7)'};
            }}
        </style>
        <div class="step-header">
            <div class="headline-text">{headline}</div>
            <div class="subheader-text">
                <span class="category">{category}</span>
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
            previous_prompt = st.session_state.publish_data.get('image_prompt', '')

            # Generate a single prompt for both images, incorporating feedback if provided
            from modules.haiku_image_generator import generate_image_prompt
            prompt_request = f"Create an image prompt for a background that captures the essence of this haiku:\n{haiku}"
            if previous_prompt:
                prompt_request += f"\n\nThe previous image was generated with this prompt:\n{previous_prompt}"
            if feedback:
                prompt_request += f"\n\nPlease adjust the image based on this feedback while maintaining the haiku's essence: {feedback}"
            prompt_request += "\nUse your rules for Haiku Background Prompt."
            
            image_prompt = generate_image_prompt(prompt_request)
            
            # Generate standard image
            standard_image_path, _ = generate_haiku_background(
                haiku,
                headline,
                article_date,
                image_prompt
            )
            
            if standard_image_path:
                # Update session state with new image paths
                st.session_state.haiku_image_path = standard_image_path
                
                # Update publish data with new image prompt
                st.session_state.publish_data['image_prompt'] = image_prompt
                
                # Generate and store encoded images for publishing
                encoded_standard_image, encoded_standard_image_with_text = generate_and_encode_images(
                    standard_image_path,
                    "haikubg_with_text.png"
                )
                st.session_state.publish_data.update({
                    'image_data': encoded_standard_image,
                    'image_haiku': encoded_standard_image_with_text,
                })
                
                # Generate new Bluesky image using the same prompt
                bluesky_image_path, _ = generate_bluesky_haiku_background(
                    haiku,
                    headline,
                    article_date,
                    image_prompt  # Pass the same prompt
                )
                
                if bluesky_image_path:
                    st.session_state.bluesky_image_path = bluesky_image_path
                    
                    encoded_bluesky_image, encoded_bluesky_image_with_text = generate_and_encode_images(
                        bluesky_image_path,
                        "bluesky_haikubg_with_text.png"
                    )
                    st.session_state.publish_data.update({
                        'bluesky_image_data': encoded_bluesky_image,
                        'bluesky_image_haiku': encoded_bluesky_image_with_text
                    })
                else:
                    st.error("Failed to generate new Bluesky image")
                
                # Save updated publish data to file
                with open('publish.json', 'w') as f:
                    json.dump(st.session_state.publish_data, f, indent=2)
                # st.success("New images generated successfully!")
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
                color: {'#ff0000' if trend_score < 8 else 'rgba(0, 255, 0, 0.7)'};
            }}
        </style>
        <div class="step-header">
            <div class="headline-text">{headline}</div>
            <div class="subheader-text">
                <span class="category">{category}</span>
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
                text-decoration: line-through;
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
    headline = st.session_state.publish_data.get('AIHeadline', '')
    category = st.session_state.publish_data.get('cat', 'Unknown')
    quality_score = st.session_state.publish_data.get('qas', 0)
    bias_text = st.session_state.publish_data.get('bs_p', 'Neutral')
    trend_score = st.session_state.publish_data.get('trend', 0.0)
    
    def publish_article_action():
        with st.spinner("Publishing article..."):
            # Update the AISummary with the raw reasoning data
            st.session_state.publish_data['AISummary'] = st.session_state.evaluation.get('reasoning', '')
            
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
                    except Exception as e:
                        st.error(f"Failed to upload images to FTP: {str(e)}")
                
                # Publish to Bluesky
                haiku = st.session_state.publish_data.get('AIHaiku', '')
                article_url = st.session_state.published_article_url
                image_path = "bluesky_haikubg_with_text.jpg"  # Assuming the image is saved with this filename
                hashtags = st.session_state.evaluation.get('hashtags', '')
                bluesky_result = publish_to_bluesky(haiku, article_url, image_path, hashtags)
                
                st.session_state.bluesky_success = True
                st.success("Article posted successfully to Bluesky!")
                
                st.rerun()  # Rerun to update button state
    
    # Check if the article has been published or rejected in the current session
    is_published = hasattr(st.session_state, 'publication_success') and st.session_state.publication_success
    is_rejected = hasattr(st.session_state, 'article_rejected') and st.session_state.article_rejected
    
    # Reset the publication success and rejection flags for the current article
    if 'current_article' not in st.session_state or st.session_state.current_article != st.session_state.publish_data.get('AIHeadline', ''):
        st.session_state.current_article = st.session_state.publish_data.get('AIHeadline', '')
        st.session_state.publication_success = False
        st.session_state.article_rejected = False
        is_published = False
        is_rejected = False
    
    if not is_published and not is_rejected:
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
                .rejected-card {
                    background-color: #2c3e50;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    margin-top: 1rem;
                    color: rgba(255, 255, 255, 0.8);
                    border: 1px solid #e74c3c;
                }
                .rejected-text {
                    color: #e74c3c;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Create columns for buttons
        cols = st.columns(2)
        
        with cols[0]:
            if st.button("Publish Article", key="final_review_publish"):
                publish_article_action()
        
        with cols[1]:
            if st.button("Cancel Publication", key="final_review_cancel"):
                st.session_state.article_rejected = True
                st.rerun()
        
        st.markdown("</div></div>", unsafe_allow_html=True)
    
    if not st.session_state.publish_data:
        st.error("No publication data available")
        reset_article_state()
        return
    
    try:
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
                st.session_state.publish_data.get('AIHeadline', 'No headline')
            ), unsafe_allow_html=True)
            
            # Reset article state after displaying the rejection message
            reset_article_state()
        
        elif hasattr(st.session_state, 'publication_success') and st.session_state.publication_success:
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
                            <div class="bluesky-status">
                                <strong>Bluesky Post:</strong>
                                <span class="bluesky-success">Posted successfully</span>
                            </div>
                        </div>
                        <div class="article-image">
                            <img src="{}" alt="Article Haiku Image" style="width: 30vw; margin-left: 2rem;" />
                        </div>
                    </div>
                </div>
                <style>
                    .published-card {{
                        background-color: #1c2331;
                        padding: 1.5rem;
                        border-radius: 8px;
                        margin-top: 1rem;
                        color: rgba(255, 255, 255, 0.9);
                        border: 1px solid #4A6FA5;
                    }}
                    .published-card h3 {{
                        color: #4A6FA5;
                        margin-bottom: 0.5rem;
                    }}
                    .article-image {{
                        text-align: center;
                    }}
                    .article-image img {{
                        max-width: 100%;
                        border-radius: 4px;
                    }}
                    .article-links {{
                        margin-top: 1rem;
                    }}
                    .article-links > div {{
                        margin-bottom: 0.5rem;
                    }}
                    .article-id {{
                        font-family: monospace;
                        font-size: 0.9em;
                        color: rgba(255, 255, 255, 0.7);
                    }}
                    .article-url {{
                        color: #4A6FA5;
                    }}
                    .bluesky-status {{
                        margin-top: 1rem;
                    }}
                    .bluesky-success {{
                        color: #2ecc71;
                    }}
                </style>
            """.format(
                st.session_state.published_article_id,
                st.session_state.published_article_url,
                st.session_state.published_article_url,
                st.session_state.publish_data['image_haiku']
            ), unsafe_allow_html=True)
        
        else:
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
                
                # Display the article summary without saving it to the database
                st.markdown("**Summary:**")
                st.markdown(st.session_state.article_data.get('summary', 'No summary'))
            
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
    
    except Exception as e:
        st.error(f"Error displaying final review: {str(e)}")
        reset_article_state()

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