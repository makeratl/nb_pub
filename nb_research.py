import requests
import json
from chat_codegpt import chat_with_codegpt
from colorama import init, Fore, Style
from dotenv import load_dotenv
import os
from review_articles import evaluate_article_with_ai, display_article, display_evaluation, update_article_status
from publish_utils import generate_and_encode_images, publish_article
import http.client
import traceback
load_dotenv()

# Initialize colorama
init(autoreset=True)

# NewsCatcher API credentials
API_KEY = os.environ.get("NEWSCATCHER_API_KEY")

def get_latest_headlines(when="1d"):
    print(f"\n{Fore.CYAN}Fetching headlines...{Style.RESET_ALL}")
    url = "https://v3-api.newscatcherapi.com/api/latest_headlines"
    params = {
        "when": when,
        "countries": "US, CA, MX, GB",
        "predefined_sources": "top 80 US,top 50 CA,top 20 MX,top 20 GB",
        "lang": "en",
        "ranked_only": "true",
        "is_opinion": "false",
        "is_paid_content": "false",
        "word_count_min": "1000",
        "has_nlp": "true",
        "clustering_enabled": "true",
        "clustering_threshold": "0.8",
        "exclude_duplicates": "true",
        "page_size": "800"
    }
    headers = {
        "x-api-token": API_KEY
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # This will raise an HTTPError for bad responses
        data = response.json()
        if 'status' in data and data['status'] == 'error':
            print(f"\n{Fore.RED}API Error: {data.get('message', 'Unknown error')}{Style.RESET_ALL}")
            return None
        print(f"\n{Fore.GREEN}Found {data.get('total_hits', 0)} articles in {data.get('clusters_count', 0)} clusters{Style.RESET_ALL}")
        return data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP Error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")
    return None

def search_news_by_topic(topic, when="1d"):
    url = "https://v3-api.newscatcherapi.com/api/search"
    params = {
        "q": topic,
        "from_": when,
        "countries": "US, CA, MX, GB",
        "lang": "en",
        "ranked_only": "true",
        "page_size": "100",
        "clustering_enabled": "true",
        "clustering_threshold": "0.8",
        "exclude_duplicates": "true"
    }
    headers = {
        "x-api-token": API_KEY
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'status' in data and data['status'] == 'error':
            print(f"API returned an error: {data.get('message', 'Unknown error')}")
            return None
        total_hits = data.get('total_hits', 0)
        clusters_count = data.get('clusters_count', 0)
        print(f"Total articles found: {total_hits}")
        print(f"Number of clusters: {clusters_count}")
        return data
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP Error occurred: {http_err}")
    except Exception as err:
        print(f"An error occurred: {err}")
    return None

def analyze_clusters(headlines_data):
    analyzed_clusters = []
    for cluster in headlines_data.get('clusters', []):
        cluster_id = cluster.get('cluster_id')
        cluster_size = cluster.get('cluster_size')
        if cluster_size >= 3:
            titles = [article['title'] for article in cluster.get('articles', [])]
            sources = [article.get('name_source', 'Unknown') for article in cluster.get('articles', [])]
            prompt = f"Analyze these news headlines and their sources:\n\nHeadlines:\n{json.dumps(titles, indent=2)}\n\nSources:\n{json.dumps(sources, indent=2)}\n\nDetermine the common topic, categorize it, identify the main subject, and assess the overall political bias BiasWeight by scoring -1 to left sources, 0 to neutral, and 1 to right on each article.  Then averaging the value for all of them as the bias weight. Return a JSON object with the structure: {{\"category\": \"Category name\", \"subject\": \"Main subject or focus\", \"bias\": \"BiasWeight\"}}"
            
            cluster_analysis = chat_with_codegpt(prompt)
            
            if cluster_analysis is None:
                print(f"Skipping cluster {cluster_id} due to API error.")
                continue

            try:
                analysis_json = json.loads(cluster_analysis)
                category = analysis_json.get("category", "Unknown")
                subject = analysis_json.get("subject", "Unknown")
                bias = float(analysis_json.get("bias", 0))
            except (json.JSONDecodeError, ValueError):
                print(f"Error parsing JSON for cluster {cluster_id}. Using default values.")
                category = "Unknown"
                subject = "Unknown"
                bias = 0

            analyzed_clusters.append({
                "cluster_id": cluster_id,
                "category": category,
                "subject": subject,
                "bias": bias,
                "article_count": cluster_size,
                "articles": cluster.get('articles', [])
            })

    return analyzed_clusters

def select_cluster(analyzed_clusters):
    display_cluster_list(analyzed_clusters)
    
    while True:
        try:
            choice = input(f"\n{Fore.YELLOW}Select cluster (0 to start over):{Style.RESET_ALL} ")
            if not choice.strip():
                continue
            choice = int(choice) - 1
            if choice == -1:
                return None
            if 0 <= choice < len(analyzed_clusters):
                selected_cluster = analyzed_clusters[choice]
                if selected_cluster['article_count'] < 3:
                    print(f"\n{Fore.YELLOW}Warning: Only {selected_cluster['article_count']} articles in cluster.{Style.RESET_ALL}")
                    if input("Process anyway? (y/n): ").lower() != 'y':
                        analyzed_clusters.pop(choice)
                        if not analyzed_clusters:
                            print(f"\n{Fore.RED}No more clusters available.{Style.RESET_ALL}")
                            return None
                        return select_cluster(analyzed_clusters)
                return selected_cluster
            print(f"{Fore.RED}Invalid choice. Please select 0-{len(analyzed_clusters)}{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Please enter a number{Style.RESET_ALL}")

def publish_with_images(publish_data, api_key):
    """Publish article with generated haiku images"""
    print(f"\n{Fore.CYAN}Starting publication process...{Style.RESET_ALL}")
    
    # Generate haiku background
    haiku = publish_data.get('AIHaiku', '')
    ai_headline = publish_data.get('AIHeadline', '')
    article_date = publish_data.get('date', '') or publish_data.get('publishDate', '') or ''
    
    if haiku:
        while True:
            image_data, image_haiku = generate_and_encode_images(haiku, ai_headline, article_date)
            
            if image_data is None:
                print(f"\n{Fore.RED}Failed to generate images{Style.RESET_ALL}")
                return None
                
            print(f"\n{Fore.YELLOW}Options:")
            print("1. Accept and continue")
            print("2. Retry (generate a new image)")
            print("3. Cancel publication{Style.RESET_ALL}")
            choice = input("Enter your choice (1/2/3): ").strip()
            
            if choice == '1':
                publish_data['image_data'] = image_data
                publish_data['image_haiku'] = image_haiku
                break
            elif choice == '2':
                continue
            elif choice == '3':
                print(f"{Fore.YELLOW}Publication cancelled.{Style.RESET_ALL}")
                return None
            else:
                print(f"{Fore.RED}Invalid choice. Please try again.{Style.RESET_ALL}")
    
    # Publish the article
    return publish_article(publish_data, api_key)

def review_published_article(publish_data):
    """Review an article before publication"""
    # print(f"\n{Fore.CYAN}Starting article review process...{Style.RESET_ALL}")
    
    # Convert publish_data to match the format expected by review_articles
    article = {
        'ID': 'DRAFT',
        'AIHeadline': publish_data.get('AIHeadline', ''),
        'AIStory': publish_data.get('AIStory', ''),
        'cat': publish_data.get('cat', ''),
        'topic': publish_data.get('topic', ''),
        'Cited': publish_data.get('Cited', ''),
        'bs': publish_data.get('bs', ''),
        'bs_p': publish_data.get('bs_p', '')
    }
    
    # Display article
    display_article(article)
    
    try:
        evaluation = evaluate_article_with_ai(article)
        
        if not evaluation:
            raise Exception("AI evaluation returned no results")
            
    except Exception as e:
        print(f"\n{Fore.RED}AI Evaluation Failed!")
        print(f"Error: {str(e)}{Style.RESET_ALL}")
        return handle_review_error()
    
    # Display evaluation results
    if evaluation:
        display_evaluation(evaluation)
        return handle_review_choice(evaluation)
    
    return 's', None

def handle_review_error():
    """Handle errors during review process"""
    while True:
        print(f"\n{Fore.YELLOW}Options:")
        print("r = retry review")
        print("s = skip review")
        print("q = quit{Style.RESET_ALL}")
        choice = input("Choice: ").lower()
        
        if choice in ['r', 's', 'q']:
            return choice, None
        print(f"{Fore.RED}Invalid input. Please use r, s, or q.{Style.RESET_ALL}")

def handle_review_choice(evaluation):
    """Handle user choice after review"""
    while True:
        print(f"\n{Fore.YELLOW}Accept AI evaluation?")
        print("a = accept AI evaluation")
        print("s = skip")
        print("q = quit{Style.RESET_ALL}")
        choice = input("Choice: ").lower()
        
        if choice == 'a':
            return prepare_review_updates(evaluation)
        elif choice in ['s', 'q']:
            return choice, None
        
        print(f"{Fore.RED}Invalid input. Please use a, s, or q.{Style.RESET_ALL}")

def prepare_review_updates(evaluation):
    """Prepare updates from review evaluation"""
    try:
        quality_score = evaluation['quality_score']
        quality_score = ''.join(c for c in str(quality_score) if c.isdigit() or c == '.')
        quality_score = float(quality_score)
        if quality_score > 10:
            quality_score = quality_score / 10
    except (ValueError, TypeError, KeyError):
        print(f"{Fore.YELLOW}Warning: Could not parse quality score{Style.RESET_ALL}")
        quality_score = None
    
    updates = {
        'cat': evaluation.get('cat'),
        'topic': evaluation.get('topic'),
        'bs_p': evaluation.get('bs_p'),
        'qas': quality_score,
        'AISummary': evaluation.get('reasoning')
    }
    updates = {k: v for k, v in updates.items() if v is not None}
    
    return 'continue', updates

def present_menu_and_process(selected_cluster, analyzed_clusters):
    # Find the index of the selected cluster to remove it later
    cluster_index = analyzed_clusters.index(selected_cluster)
    
    # Prepare data for the CodeGPT agent
    articles_data = {}
    seen_headlines = set()
    all_articles = selected_cluster['articles']

    for article in all_articles:
        name_source = article.get('name_source', 'Unknown source')
        headline = article.get('title', 'No title')
        
        # Check for unique source and headline
        if name_source not in articles_data and headline not in seen_headlines:
            articles_data[name_source] = {
                "title": headline,
                "content": article.get('content', 'No content available'),
                "name_source": name_source,
                "link": article.get('link', 'No link available')
            }
            seen_headlines.add(headline)

    if len(articles_data) < 3:
        print(f"Error: Not enough unique sources and headlines found. Only {len(articles_data)} available.")
        print("\nAll articles in the cluster:")
        for i, article in enumerate(all_articles, 1):
            title = article.get('title', 'No title')
            source = article.get('name_source', 'Unknown source')
            is_selected = source in articles_data and articles_data[source]['title'] == title
            color = Fore.GREEN if is_selected else Fore.RED
            print(f"{color}{i}. {title} ({source}){Style.RESET_ALL}")
        
        override = input("Do you want to process this cluster anyway? (y/n): ").lower()
        analyzed_clusters.pop(cluster_index)  # Remove the cluster
        if override != 'y':
            return None, analyzed_clusters

    articles_list = list(articles_data.values())[:8]  # Limit to 8 articles

    prompt = f"2. Article Creation:\n\nCreate an article based on these sources. Include a headline, haiku, full story, and a one-paragraph summary. The story should be in HTML format.\n\n{json.dumps(articles_list, indent=2)}"
    article_json = chat_with_codegpt(prompt)

    if article_json is None:
        print("Failed to generate article due to API error.")
        retry = input("Would you like to retry? (y/n): ").lower()
        if retry == 'y':
            return present_menu_and_process(selected_cluster, analyzed_clusters)
        else:
            analyzed_clusters.pop(cluster_index)  # Remove the cluster if we're not retrying
            return None, analyzed_clusters

    try:
        article_data = json.loads(article_json.replace('\n', '').replace('\r', ''))
    except json.JSONDecodeError:
        print("Non-JSON response from CodeGPT. Here's the raw response:")
        print(article_json)
        retry = input("Would you like to retry? (y/n): ").lower()
        if retry == 'y':
            return present_menu_and_process(selected_cluster, analyzed_clusters)
        else:
            analyzed_clusters.pop(cluster_index)  # Remove the cluster if we're not retrying
            return None, analyzed_clusters

    if all(key in article_data for key in ['headline', 'haiku', 'story', 'summary']):
        # Create initial publish data
        publish_data = {
            "AIHeadline": article_data.get('headline', ''),
            "AIHaiku": article_data.get('haiku', ''),
            "AIStory": article_data.get('story', ''),
            "AISummary": article_data.get('summary', ''),
            "deta_bs_align": "9",
            "bs": f"{selected_cluster['category']} | High Confidence | {selected_cluster['subject']}",
            "Cited": json.dumps([[i+1, article['link']] for i, article in enumerate(articles_list)]),
            "topic": selected_cluster['category'],
            "cat": selected_cluster['subject']
        }

        # Display initial article
        display_article_preview(publish_data, articles_list)

        # Review process
        review_result, updates = review_published_article(publish_data)
        
        if review_result == 'q':
            return None, []
        elif review_result == 'r':
            return present_menu_and_process(selected_cluster, analyzed_clusters)
        elif review_result == 'continue' and updates:
            # Apply updates silently
            publish_data.update(updates)
            with open('publish.json', 'w') as f:
                json.dump(publish_data, f, indent=2)
            
            # Move directly to publication
            article_id = publish_with_images(publish_data, os.environ.get("PUBLISH_API_KEY"))
            if article_id:
                print(f"\n{Fore.GREEN}Published successfully! ID: {article_id}{Style.RESET_ALL}")
        
        analyzed_clusters.pop(analyzed_clusters.index(selected_cluster))
    else:
        print(f"\n{Fore.RED}Error: Missing required article fields{Style.RESET_ALL}")
        if input("Retry? (y/n): ").lower() == 'y':
            return present_menu_and_process(selected_cluster, analyzed_clusters)
        analyzed_clusters.pop(analyzed_clusters.index(selected_cluster))
        return None, analyzed_clusters

    return article_data, analyzed_clusters

def display_cluster_list(analyzed_clusters):
    """Display available clusters in a clean format"""
    print(f"\n{Fore.CYAN}Available News Clusters:{Style.RESET_ALL}")
    print("=" * 80)
    for i, cluster in enumerate(analyzed_clusters, 1):
        bias = cluster['bias']
        bias_color = Fore.BLUE if bias < 0 else (Fore.RED if bias > 0 else Fore.WHITE)
        
        print(f"{i:2d}. {Fore.YELLOW}{cluster['subject']}{Style.RESET_ALL}")
        print(f"    Category: {cluster['category']}")
        print(f"    Articles: {cluster['article_count']}")
        print(f"    Bias: {bias_color}{bias:.2f}{Style.RESET_ALL}")
        print("-" * 40)

def display_article_preview(publish_data, articles_list):
    """Display article preview in a clean format"""
    print("\n" + "=" * 80)
    print(f"{Fore.CYAN}Article Preview:{Style.RESET_ALL}")
    print("-" * 80)
    print(f"{Fore.YELLOW}Headline:{Style.RESET_ALL} {publish_data['AIHeadline']}")
    print(f"\n{Fore.YELLOW}Summary:{Style.RESET_ALL}\n{publish_data['AISummary']}")
    # print(f"\n{Fore.YELLOW}Sources:{Style.RESET_ALL}")
    # for article in articles_list:
    #     print(f"- {article['name_source']}: {article['title']}")
    print("=" * 80)

def display_review_results(updates):
    """Display review updates in a clean format"""
    print(f"\n{Fore.CYAN}Review Results:{Style.RESET_ALL}")
    print("-" * 80)
    if 'cat' in updates:
        print(f"Category: {updates['cat']}")
    if 'topic' in updates:
        print(f"Topic: {updates['topic']}")
    if 'bs_p' in updates:
        print(f"Bias Score: {updates['bs_p']}")
    if 'qas' in updates:
        print(f"Quality Score: {updates['qas']}")
    if 'AISummary' in updates:
        print(f"\nAnalysis:\n{updates['AISummary']}")
    print("-" * 80)

def main():
    while True:
        search_type = input("Enter '1' to search by headlines or '2' to search by topic: ")
        
        if search_type == '1':
            when = input("Enter the time range for headlines (e.g., 1h, 12h, 1d, 7d, 30d): ").strip()
            headlines_data = get_latest_headlines(when)
            if not headlines_data:
                print("Failed to retrieve headlines data.")
                continue
        elif search_type == '2':
            topic = input("Enter the topic you want to search for: ").strip()
            when = input("Enter the time range for the search (e.g., 1h, 12h, 1d, 7d, 30d): ").strip()
            headlines_data = search_news_by_topic(topic, when)
            if not headlines_data:
                print("Failed to retrieve news data.")
                continue
        else:
            print("Invalid choice. Please enter '1' or '2'.")
            continue

        analyzed_clusters = analyze_clusters(headlines_data)

        try:
            while analyzed_clusters:
                selected_cluster = select_cluster(analyzed_clusters)
                if selected_cluster is None:
                    break

                article_data, analyzed_clusters = present_menu_and_process(selected_cluster, analyzed_clusters)
                if article_data:
                    print("\nArticle created successfully and saved to publish.json!")

                if not analyzed_clusters:
                    print("\nNo more clusters available.")
                    break

                choice = input("\nDo you want to create another article? (y/n): ").lower()
                if choice != 'y':
                    print("Exiting the program. Goodbye!")
                    return

            choice = input("\nDo you want to start a new search? (y/n): ").lower()
            if choice != 'y':
                print("Exiting the program. Goodbye!")
                break
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            break

if __name__ == "__main__":
    main()
