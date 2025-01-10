"""Keyword optimization module for headline processing"""
import os
from typing import Optional, Dict, List
from chat_codegpt import chat_with_codegpt

# Cache for optimized keywords to avoid redundant processing
keyword_cache: Dict[str, str] = {}

def optimize_headline_keywords(headline: str) -> Optional[str]:
    """
    Convert a headline into optimized search keywords using AI.
    
    Args:
        headline (str): The article headline to optimize
        
    Returns:
        Optional[str]: Comma-separated list of optimized keywords, or None if processing fails
    """
    if not headline or not isinstance(headline, str):
        return None
        
    # Check cache first
    if headline in keyword_cache:
        return keyword_cache[headline]
        
    try:
        prompt = f"""
        Convert this news headline into 3-5 optimal search keywords for topic search.
        Focus on key entities, unique identifiers, and main topics.
        Remove common words and articles.
        Format as comma-separated list.
        
        Headline: {headline}
        
        Rules:
        1. Extract key topics and named entities
        2. Remove common words, articles, and redundant terms
        3. Include relevant synonyms if helpful
        4. Focus on unique identifiers and specific topics
        5. Limit to 3-5 most relevant terms
        6. Format as comma-separated values
        
        Example:
        Headline: "Tesla's Cybertruck Production Faces Delays Due to Battery Constraints"
        Keywords: Tesla, Cybertruck, EV production, battery supply
        
        Keywords for the given headline:
        """
        
        # Get optimized keywords from CodeGPT
        response = chat_with_codegpt(prompt)
        if not response:
            return None
            
        # Clean and validate the response
        keywords = clean_keywords(response)
        if keywords:
            # Cache the result
            keyword_cache[headline] = keywords
            return keywords
            
        return None
        
    except Exception as e:
        print(f"Error optimizing keywords: {str(e)}")
        return None

def clean_keywords(raw_keywords: str) -> Optional[str]:
    """
    Clean and validate the keyword response.
    
    Args:
        raw_keywords (str): Raw keyword string from AI
        
    Returns:
        Optional[str]: Cleaned, comma-separated keywords or None if invalid
    """
    try:
        # Remove any extra whitespace and newlines
        cleaned = raw_keywords.strip()
        
        # Split into individual keywords
        keywords = [k.strip() for k in cleaned.split(',')]
        
        # Filter out empty or invalid keywords
        keywords = [k for k in keywords if k and len(k) >= 2]
        
        # Validate we have at least one keyword
        if not keywords:
            return None
            
        # Rejoin as comma-separated string
        return ', '.join(keywords)
        
    except Exception as e:
        print(f"Error cleaning keywords: {str(e)}")
        return None

def clear_cache() -> None:
    """Clear the keyword cache"""
    keyword_cache.clear()

def get_cached_keywords() -> Dict[str, str]:
    """Get the current keyword cache"""
    return keyword_cache.copy() 