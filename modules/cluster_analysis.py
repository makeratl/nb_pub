"""Cluster analysis and article generation functions"""
import json
from chat_codegpt import chat_with_codegpt

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
        return None 