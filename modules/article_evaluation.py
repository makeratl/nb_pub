import json
import traceback
from chat_codegpt import chat_with_codegpt

def evaluate_article_with_ai(article, feedback_message=None):
    """Evaluate article using AI"""
    evaluation_context = article.get('evaluation_context', '')
    
    if feedback_message:
        prompt = f"""
        {evaluation_context}
        
        Original Article:
        Headline: {article.get('AIHeadline', 'No headline provided')}
        Story: {article.get('AIStory', 'No story provided')}
        Sources: {article.get('Cited', 'No sources provided')}
        
        Original Evaluation:
        {json.dumps(article, indent=2)}
        
        Feedback:
        {feedback_message}
        
        Please evaluate the article based on the above Human feedback, providing an updated evaluation in JSON Format.

        Return a JSON object with:
        {{
            "quality_score": (0-10),
            "bs_p": ("Far Left"/"Left"/"Center Left"/"Neutral"/"Center Right"/"Right"/"Far Right"),
            "cat": "category",
            "topic": "main topic", 
            "trend": (0-10),
            "reasoning": "Detailed analysis with Quality Analysis:, Bias Analysis:, and Propagation Potential: sections"
        }}
        """
    else:
        prompt = f"""
        {evaluation_context}
        
        Please evaluate this news article according to the above guidelines:
        
        Headline: {article.get('AIHeadline', 'No headline provided')}
        Story: {article.get('AIStory', 'No story provided')}
        Sources: {article.get('Cited', 'No sources provided')}
        
        Provide a detailed analysis covering:
        1. Quality Analysis: Evaluate based on the guidelines, focusing on source credibility and journalistic standards 
        2. Bias Analysis: Assess political lean and perspective balance
        3. Propagation Potential: Rate shareability and public interest
        
        Return a JSON object with:
        {{
            "quality_score": (0-10),
            "bs_p": ("Far Left"/"Left"/"Center Left"/"Neutral"/"Center Right"/"Right"/"Far Right"),
            "cat": "category",
            "topic": "main topic", 
            "trend": (0-10),
            "reasoning": "Detailed analysis with Quality Analysis:, Bias Analysis:, and Propagation Potential: sections"
        }}
        """
    
    try:
        response = chat_with_codegpt(prompt)
        
        parsed_response = json.loads(response)
        
        # Validate trend score exists and is numeric
        trend_score = parsed_response.get('trend')
        
        if trend_score is not None:
            try:
                parsed_response['trend'] = float(trend_score)
            except (ValueError, TypeError):
                parsed_response['trend'] = 0.0
        
        return parsed_response
    except Exception as e:
        print(f"Error in evaluate_article_with_ai: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return None