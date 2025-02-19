"""Cluster analysis and article generation functions"""
import json
from chat_codegpt import chat_with_codegpt
import streamlit as st

# Define specific agent IDs for different functions
ANALYSIS_AGENT_ID = "03d17f5c-0c9b-40ee-8a53-3829f2746f0e"
ARTICLE_CREATION_AGENT_ID = "c065444b-510f-4ab0-97b8-3840c66109d3"

def analyze_cluster(cluster):
    """Analyze a single cluster by extracting basic stats and most recent article"""
    articles = cluster.get('articles', [])
    
    # Debug: Print initial articles data
    st.write("Debug: Number of articles received:", len(articles))
    if articles:
        st.write("Debug: First article sample:", {
            'title': articles[0].get('title', 'NO TITLE'),
            'source': articles[0].get('name_source', 'NO SOURCE'),
            'date': articles[0].get('published_date', 'NO DATE')
        })
    
    if not articles:
        return None
        
    # Get unique sources
    unique_sources = set(article.get('name_source', 'Unknown') for article in articles)
    
    # Debug: Print unique sources
    st.write("Debug: Number of unique sources:", len(unique_sources))
    st.write("Debug: Unique sources:", list(unique_sources))
    
    # Sort articles by published date and get most recent
    sorted_articles = sorted(
        articles,
        key=lambda x: x.get('published_date', ''),
        reverse=True
    )
    
    # Get the first article's headline as a fallback
    first_article_headline = articles[0].get('title', 'No title available')
    
    # Use most recent if available, otherwise use first article
    most_recent = sorted_articles[0] if sorted_articles else articles[0]
    
    # Debug: Print result before returning
    result = {
        'article_count': len(articles),
        'unique_source_count': len(unique_sources),
        'most_recent_headline': most_recent.get('title', first_article_headline),
        'most_recent_date': most_recent.get('published_date', 'No date available'),
        'articles': articles
    }
    
    st.write("Debug: Final analysis result:", {
        'article_count': result['article_count'],
        'unique_source_count': result['unique_source_count'],
        'most_recent_headline': result['most_recent_headline']
    })
    
    return result

def create_article(cluster):
    """Generate article from cluster using CodeGPT"""
    articles_data = []
    seen_titles = set()
    seen_sources = set()
    
    for article in cluster['articles']:
        title = article['title'] 
        source = article.get('name_source', 'Unknown')
        if title not in seen_titles and source not in seen_sources:
            articles_data.append({
                "title": title,
                "content": article.get('content', ''),
                "name_source": source,
                "link": article.get('link', ''),
                "source_id": len(articles_data) + 1  # Add source ID for citation
            })
            seen_titles.add(title)
            seen_sources.add(source)
            
            if len(articles_data) >= 8:
                break

    prompt = f"""Create an article based on these sources with the following components:

    1. Headline: 
    - Keep it objective, clear and factual
    - Avoid clickbait or sensationalized language
    - Focus on informing rather than attracting clicks
    - Use concise, straightforward language

    2. Haiku:
    - Follow traditional 5-7-5 syllable format
    - Be clever and insightful while remaining relevant
    - Capture the essence of the story creatively
    - Avoid mundane or obvious statements

    3. Full Story:
    - Structure with clear paragraphs and sections
    - Use semantic HTML tags (<p>, <h2>, etc.) for organization
    - Avoid inline styles - keep HTML clean and semantic
    - Include relevant quotes and attributions using the following format:
      * For direct quotes: <q data-source="[source_id]">quote text</q>
      * For paraphrased facts: <span data-source="[source_id]">fact text</span>
      * For multiple sources: <span data-sources="[source_id1,source_id2]">fact text</span>
    - Each paragraph should have at least one cited fact or quote
    - When stating statistics, numbers, or specific claims, always include a citation
    - For editorial content, cite multiple sources to show balanced perspective
    - Maintain objective, balanced reporting
    - Be mindful of special characters in the content that could break JSON object storage. If double quotes are present, use single quotes instead.

    4. Summary:
    - Provide a single, concise paragraph
    - Capture key points and significance
    - Keep focused and avoid unnecessary details
    - End with clear takeaway or context

    The story should be in HTML format with proper semantic structure and citations.
    Each source has a unique source_id that should be used in the data-source attributes.
    
    Sources: {json.dumps(articles_data, indent=2)}"""

    article_json = chat_with_codegpt(prompt, agent_id=ARTICLE_CREATION_AGENT_ID)
    try:
        return json.loads(article_json)
    except Exception as e:
        print(f"Failed to parse article JSON. Raw response:\n{article_json}")
        print(f"Error: {str(e)}")
        return None