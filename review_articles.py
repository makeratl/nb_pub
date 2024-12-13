import http.client
import json
from typing import Optional
import os
from datetime import datetime
from dotenv import load_dotenv
from chat_codegpt import chat_with_codegpt
from colorama import init, Fore, Style
import time  # Add this to the imports at the top

# Initialize colorama
init(autoreset=True)
load_dotenv()

API_KEY = os.environ.get("PUBLISH_API_KEY")
API_HOST = "fetch.ainewsbrew.com"

def get_next_article() -> Optional[dict]:
    """Fetch the next unreviewed article from the API"""
    conn = http.client.HTTPSConnection(API_HOST)
    headers = {
        'X-API-KEY': API_KEY
    }
    
    conn.request("GET", "/api/index_v5.php?mode=getUnreviewed", headers=headers)
    response = conn.getresponse()
    if response.status == 200:
        return json.loads(response.read().decode('utf-8'))
    return None

def update_article_status(article_id: int, status: str, updates: dict = None) -> bool:
    """Update the review status and optional fields of an article"""
    conn = http.client.HTTPSConnection(API_HOST)
    headers = {
        'X-API-KEY': API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Build the URL for the status update
    url = f"/api/index_v5.php?mode=updateReviewStatus&id={article_id}&status={status}"
    
    try:
        # Send the updates in the request body
        if updates:
            conn.request("POST", url, json.dumps(updates), headers)
        else:
            conn.request("GET", url, headers=headers)
            
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
        
        if response.status == 200:
            result = json.loads(response_data)
            if result.get("status") != "success":
                raise Exception(f"API returned error: {result.get('message', 'Unknown error')}")
            return True
    except Exception as e:
        print(f"\n{Fore.RED}Error updating article {article_id}:")
        print(f"Status: {status}")
        print(f"Updates: {updates}")
        print(f"Error details: {str(e)}")
        print(f"API Response Status Code: {response.status if 'response' in locals() else 'No response'}")
        print(f"API Response Data: {response_data if 'response_data' in locals() else 'No response data'}")
        print(f"Raw API Response: {json.dumps(json.loads(response_data), indent=2) if 'response_data' in locals() else 'No response'}{Style.RESET_ALL}")
        
        if auto_approve:
            print(f"\n{Fore.YELLOW}Auto-approve mode stopped due to update error.{Style.RESET_ALL}")
            auto_approve = False
            
        while True:
            print(f"\n{Fore.YELLOW}Options:")
            print("r = retry this article")
            print("s = skip to next article")
            print("q = quit{Style.RESET_ALL}")
            choice = input("Choice: ").lower()
            
            if choice in ['r', 's', 'q']:
                return choice
            print(f"{Fore.RED}Invalid input. Please use r, s, or q.{Style.RESET_ALL}")
    finally:
        conn.close()
    return False

def evaluate_article_with_ai(article: dict) -> Optional[dict]:
    """Use AI to evaluate the article content"""
    # Safely get values with defaults for missing fields
    headline = article.get('AIHeadline', 'No headline available')
    story = article.get('AIStory', 'No story available')
    category = article.get('cat', 'No category available')
    topic = article.get('topic', 'No topic available')
    cited = article.get('Cited', 'No sources available')
    bs_score = article.get('bs', 'No BS score available')
    bs_prob = article.get('bs_p', 'No BS probability available')

    prompt = f"""Evaluate this article and provide a detailed analysis. Consider the following aspects:

    Scoring Criteria (1-10 scale):
    1. Story quality and factual basis (0-7 points)
       - Clear narrative structure (0-5)
       - Professional writing style (0-5)

    2. Source Analysis (0-1 points)
       - Source Quality Assessment:
         * Source Credibility (+0.8)
           - Sources are established news/media organizations
           - Sources likely contain direct quotes and primary data
         * Source Variety (+0.2)
           - Multiple perspectives available through cited sources
       - Source Political Lean Analysis (informational, not scoring):
         * Note sources as:
           - Left-leaning (e.g., MSNBC, HuffPost)
           - Center/Neutral (e.g., Reuters, AP)
           - Right-leaning (e.g., Fox News, NY Post)
         Note: Our articles summarize key points from fuller source articles.
               Direct quotes may be in source articles rather than our summary.

    3. Context and Completeness (0-2 points)
       - Appropriate context provided
       - Key information included
       - Clear topic focus

    Important Notes on Source Evaluation:
    - Cited sources are complete articles containing additional context
    - Our articles synthesize information from these fuller sources
    - Direct citations are often in the source articles
    - Evaluate source credibility rather than citation style
    - Consider the depth of reporting available in source articles

    Automatic Rejection Criteria (core issues only):
    - Demonstrably false information
    - Severe factual errors
    - Complete lack of sources
    Note: Source diversity and political lean should be noted but not trigger rejection

    Article Details:
    Headline: {headline}
    Story: {story}
    Category: {category}
    Topic: {topic}
    BS Score: {bs_score}
    BS Probability: {bs_prob}
    CitedSources: {cited}

    Return a JSON object with the following structure:
    {{
        "quality_score": "Combined score from criteria above (1-10). Scores below 6 should result in rejection",
        "category_assessment": "Correction to the Category if it is not in the defined list.",
        "cat": "corrected category",
        "topic_assessment": "evaluation of topic accuracy",
        "topic": "corrected topic keywords",
        "bias_analysis": "Source-by-source political lean breakdown:
                         - List each source with its political categorization
                         - Calculate left/center/right ratio
                         - Note any missing viewpoint perspectives",
        "bs_p": "Political lean score (0.0-1.0):
                0.0-0.3: Balanced source distribution
                0.3-0.7: Leans left or right
                0.7-1.0: Heavy left or right bias
                Include + for right bias, - for left bias
                Example: 0.8 (heavy right), -0.8 (heavy left)",
        "suggested_keywords": "list, of, relevant, keywords",
        "recommendations": "'approved' if quality_score >= 6, 'rejected' if quality_score < 6",
        "reasoning": "Detailed explanation including two sections:
                     QUALITY ASSESSMENT:
                     1. Source credibility and reliability
                     2. Raw data quality assessment
                     3. Overall quality score justification
                     
                     POLITICAL LEAN ASSESSMENT:
                     1. Individual source categorization (left/center/right)
                     2. Overall source distribution ratio
                     3. Missing viewpoint analysis
                     4. Final political lean score with direction (+/-)"
    }}

    Important: 
    - Source Analysis Guidelines:
      * Evaluate each source's known political lean
      * Calculate overall source distribution
      * Assess raw data quality from each source
      * Consider source type hierarchy (primary > secondary)
    
    - Scoring Considerations:
      * High scores (6-10): Focus on factual accuracy and clarity
      * Low scores (1-5): Poor factual support or unclear presentation
      * Source political lean should be noted but not heavily impact score
      * Lack of source diversity reduces score by max 0.5 points

    - Bias Score Guidelines:
      * Document source political leans for transparency
      * Calculate approximate left/right distribution
      * Consider the full context available in source articles
      * Focus on source credibility over citation style
      * Missing perspectives should be noted but not heavily penalized
    """
    
    try:
        evaluation = chat_with_codegpt(prompt)
        if evaluation:
            return json.loads(evaluation)
    except Exception as e:
        print(f"Error during AI evaluation: {str(e)}")
    return None

def display_article(article: dict):
    """Display article information in a formatted way"""
    # print("\n" + "="*80)
    # print(f"{Fore.YELLOW}Article ID: {article['ID']}{Style.RESET_ALL}")
    # print(f"{Fore.CYAN}Headline:{Style.RESET_ALL} {article['AIHeadline']}")
    # print("="*80)

def display_evaluation(evaluation: dict):
    """Display the AI evaluation results in a formatted way"""
    print("\n" + "="*80)
    print(f"{Fore.CYAN}AI EVALUATION RESULTS{Style.RESET_ALL}")
    print("="*80)
    
    print(f"{Fore.GREEN}Quality Score:{Style.RESET_ALL} {evaluation['quality_score']}")
    print(f"{Fore.GREEN}Suggested Category:{Style.RESET_ALL} {evaluation.get('cat', 'No category suggestion')}")
    print(f"{Fore.GREEN}Suggested Topic:{Style.RESET_ALL} {evaluation.get('topic', 'No topic suggestion')}")
    print(f"{Fore.GREEN}Bias Score (bs_p):{Style.RESET_ALL} {evaluation.get('bs_p', 'No bias score available')}")
    
    print(f"\n{Fore.GREEN}Recommendations:{Style.RESET_ALL}")
    print(evaluation.get('recommendations', 'No recommendations available'))
    
    # Only show reasoning if the article is recommended for rejection
    if evaluation.get('recommendations', '').lower() == 'rejected':
        print(f"\n{Fore.GREEN}Rejection Reasoning:{Style.RESET_ALL}")
        print(evaluation.get('reasoning', 'No reasoning provided'))
    
    print("="*80)

def main():
    auto_approve = False

    while True:
        # Get next article
        article = get_next_article()
        
        if not article:
            print("\nNo more articles to review!")
            break
            
        # Display article
        display_article(article)
        
        # Get AI evaluation
        print("\nRequesting AI evaluation...")
        try:
            evaluation = evaluate_article_with_ai(article)
            
            if not evaluation:
                raise Exception("AI evaluation returned no results")
                
        except Exception as e:
            print(f"\n{Fore.RED}AI Evaluation Failed!")
            print(f"Error: {str(e)}{Style.RESET_ALL}")
            
            if auto_approve:
                print(f"\n{Fore.YELLOW}Auto-approve mode stopped due to AI evaluation failure.")
                auto_approve = False
            
            while True:
                print(f"\n{Fore.YELLOW}Options:")
                print("r = retry this article")
                print("s = skip to next article")
                print("q = quit{Style.RESET_ALL}")
                choice = input("Choice: ").lower()
                
                if choice == 'r':
                    continue  # Retry the same article
                elif choice == 's':
                    break    # Move to next article
                elif choice == 'q':
                    return   # Exit the program
                else:
                    print(f"{Fore.RED}Invalid input. Please use r, s, or q.{Style.RESET_ALL}")
            
            if choice == 's':
                continue
            elif choice == 'r':
                continue
            
        # Continue with normal flow if AI evaluation succeeded
        if evaluation:
            display_evaluation(evaluation)
            
            # Get AI's recommendation
            ai_recommendation = evaluation.get('recommendations', '').lower()
            if ai_recommendation not in ['approved', 'rejected']:
                print(f"\n{Fore.RED}Invalid AI recommendation: {ai_recommendation}")
                print("Stopping auto-approve mode due to unexpected AI response.{Style.RESET_ALL}")
                auto_approve = False
                continue
            
            if auto_approve:
                status = ai_recommendation
                print(f"\n{Fore.CYAN}Auto-processing with AI recommendation: {status}{Style.RESET_ALL}")
            else:
                # Ask user to accept or reject the evaluation (not the recommendation)
                while True:
                    print(f"\n{Fore.YELLOW}Accept AI evaluation?")
                    print(f"a = accept AI evaluation (will use AI's {ai_recommendation} recommendation)")
                    print(f"c = continue with auto-approve")
                    print(f"s = skip")
                    print(f"q = quit{Style.RESET_ALL}")
                    choice = input("Choice: ").lower()
                    
                    status_map = {
                        'a': ai_recommendation,  # Use AI's recommendation
                        's': 'skip',
                        'q': 'quit',
                        'c': 'auto-approve'
                    }
                    
                    if choice in status_map:
                        status = status_map[choice]
                        break
                    print(f"{Fore.RED}Invalid input. Please use a, c, s, or q.{Style.RESET_ALL}")
            
            if status == 'quit':
                break
            elif status == 'skip':
                continue
            elif status == 'auto-approve':
                auto_approve = True
                status = ai_recommendation
            
            if status in ['approved', 'rejected']:
                try:
                    quality_score = evaluation['quality_score']
                    quality_score = ''.join(c for c in str(quality_score) if c.isdigit() or c == '.')
                    quality_score = float(quality_score)
                    if quality_score > 10:  # If score was like "85" instead of "8.5"
                        quality_score = quality_score / 10
                except (ValueError, TypeError, KeyError):
                    print(f"{Fore.YELLOW}Warning: Could not parse quality score: {evaluation.get('quality_score')}{Style.RESET_ALL}")
                    quality_score = None
                
                updates = {
                    'cat': evaluation.get('cat'),
                    'topic': evaluation.get('topic'),
                    'bs_p': evaluation.get('bs_p'),
                    'qas': quality_score,
                    'reasoning': evaluation.get('reasoning')
                }
                # Remove None values
                updates = {k: v for k, v in updates.items() if v is not None}
            else:  # skip or quit
                updates = None
                
            # Update article status and fields
            if updates is not None:  # Only update if we're not skipping
                update_result = update_article_status(article['ID'], status, updates)
                if update_result == True:
                    print(f"\n{Fore.GREEN}Article {article['ID']} marked as {status}")
                    if updates:
                        print(f"Updated fields: {', '.join(updates.keys())}{Style.RESET_ALL}")
                elif update_result in ['r', 's', 'q']:
                    if update_result == 'q':
                        break
                    elif update_result == 's':
                        continue
                    elif update_result == 'r':
                        continue  # Will retry the same article
                else:
                    print(f"\n{Fore.RED}Error updating article {article['ID']} status{Style.RESET_ALL}")
                    if auto_approve:
                        auto_approve = False
                        continue
            
            # Add throttling delay if in auto-approve mode
            if auto_approve:
                time.sleep(1)  # 1 second delay between updates

if __name__ == "__main__":
    print(f"{Fore.CYAN}Starting article review process...{Style.RESET_ALL}")
    main() 