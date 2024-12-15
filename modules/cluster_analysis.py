"""Cluster analysis and article generation functions"""
import json
from chat_codegpt import chat_with_codegpt

def analyze_cluster(cluster):
    """Analyze a single cluster using CodeGPT"""
    articles = cluster.get('articles', [])
    
    # Filter for unique titles and sources
    seen_titles = set()
    seen_sources = set()
    filtered_articles = []
    for article in articles:
        title = article['title']
        source = article.get('name_source', 'Unknown')
        if title not in seen_titles and source not in seen_sources:
            filtered_articles.append(article)
            seen_titles.add(title)
            seen_sources.add(source)
    
    # Check if cluster has enough unique articles
    if len(filtered_articles) < 3:
        return None
    
    titles = [article['title'] for article in filtered_articles]
    sources = [article.get('name_source', 'Unknown') for article in filtered_articles]
    
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
        result['article_count'] = len(filtered_articles)
        result['articles'] = filtered_articles
        return result
    except:
        return None

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
                "link": article.get('link', '')
            })
            seen_titles.add(title)
            seen_sources.add(source)
            
            if len(articles_data) >= 8:
                break

    prompt = f"""Create an article based on these sources. Include a headline, haiku, full story, and a one-paragraph summary.
    The story should be in HTML format.
    
    Sources: {json.dumps(articles_data, indent=2)}"""

    article_json = chat_with_codegpt(prompt)
    try:
        return json.loads(article_json)
    except:
        return None 