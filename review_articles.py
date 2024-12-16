import http.client
import json
from typing import Optional
import os
from datetime import datetime
from dotenv import load_dotenv
from chat_codegpt import chat_with_codegpt
from colorama import init, Fore, Style
import time  # Add this to the imports at the top
import traceback
from modules.article_evaluation import evaluate_article_with_ai

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