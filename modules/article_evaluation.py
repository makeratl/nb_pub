import json
import traceback
from chat_codegpt import chat_with_codegpt
from datetime import datetime

# Define the specific agent ID for article evaluation
EVALUATION_AGENT_ID = "c065444b-510f-4ab0-97b8-3840c66109d3"

def evaluate_article_with_ai(article, feedback_message=None):
    """Evaluate article using AI"""
    evaluation_context = article.get('evaluation_context', '')
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    if feedback_message:
        prompt = f"""
        {evaluation_context}
        
        Current Date Context: {current_date}
        Please consider the temporal relevance of the article relative to today's date when evaluating its quality and propagation potential.
        
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
            "topic": "Comma Separated List of Topics keywords", 
            "trend": (0-10),
            "reasoning": "Detailed analysis with Quality Analysis:, Bias Analysis:, and Propagation Potential: sections",
            "hashtags": "List of relevant hashtags formatted for publishing direct on social media"
        }}
        """
    else:
        prompt = f"""
        {evaluation_context}
        
        Current Date Context: {current_date}
        Please consider the temporal relevance of the article relative to today's date when evaluating its quality and propagation potential.
        
        Please evaluate this news article according to the above guidelines:
        
        Headline: {article.get('AIHeadline', 'No headline provided')}
        Story: {article.get('AIStory', 'No story provided')}
        Sources: {article.get('Cited', 'No sources provided')}
        
        Provide a detailed analysis covering:
        1. Source Analysis: Carefully evaluate each cited source for:
           - Credibility and reputation of source organizations/authors
           - Verification of claims against primary sources where possible
           - Red flags for potential propaganda or extremist content
           - For "AI Perspective:" articles: Verify that analysis is grounded in factual source material without speculation
        2. Quality Analysis: Evaluate based on the guidelines, focusing on:
           - Journalistic standards and objectivity
           - Proper attribution and sourcing
           - Clarity and accuracy of reporting
           - For "AI Perspective:" articles: Assess if analysis adds meaningful insight without unfounded assumptions
        3. Bias Analysis:
           - Assess political lean based strictly on narrative framing and policy positions
           - Check for loaded language, emotional manipulation, or provocative word choices
           - Evaluate fairness in presentation of different viewpoints and perspectives
           - Note: Neither humanizing subjects nor focusing purely on statistics/facts indicates political bias
           - Focus on actual political positions, rhetoric and narrative choices rather than style choices
           - For "AI Perspective:" articles: Check for biased interpretations of source material
        4. Propagation Potential: 
           - Rate shareability and public interest
           - Consider temporal relevance
           - Assess educational/informational value
           - For "AI Perspective:" articles: Evaluate if analysis enhances understanding
        5. Hashtag recommendation: Provide relevant, factual hashtags that accurately represent the article content
        
        Return a JSON object with:
        {{
            "quality_score": (0-10),
            "bs_p": ("Far Left"/"Left"/"Center Left"/"Neutral"/"Center Right"/"Right"/"Far Right"),
            "cat": "category",
            "topic": "Comma Separated List of Topics keywords", 
            "trend": (0-10),
            "reasoning": "Detailed analysis with Quality Analysis:, Bias Analysis:, and Propagation Potential: sections",
            "hashtags": "List of relevant hashtags formatted for publishing direct on social media"
        }}
        """
    
    try:
        response = chat_with_codegpt(prompt, agent_id=EVALUATION_AGENT_ID)
        
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