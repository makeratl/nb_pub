import requests
import json
from chat_codegpt import chat_with_codegpt
from colorama import init, Fore, Style
from dotenv import load_dotenv
import os
load_dotenv()

# Initialize colorama
init(autoreset=True)

# NewsCatcher API credentials
API_KEY = os.environ.get("NEWSCATCHER_API_KEY")

def get_latest_headlines(when="1d"):
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
    print("Available news clusters:")
    for i, cluster in enumerate(analyzed_clusters, 1):
        bias = cluster['bias']
        if bias < 0:
            bias_color = Fore.BLUE
        elif bias > 0:
            bias_color = Fore.RED
        else:
            bias_color = Fore.WHITE
        
        print(f"{i}. {cluster['subject']} ({cluster['category']}) - {cluster['article_count']} articles - Bias: {bias_color}{bias:.2f}{Style.RESET_ALL}")
    
    while True:
        choice = int(input("Enter the number of the cluster you want to process (or 0 to start over): ")) - 1
        if choice == -1:
            return None
        if 0 <= choice < len(analyzed_clusters):
            selected_cluster = analyzed_clusters[choice]
            if selected_cluster['article_count'] < 3:
                print(f"Warning: This cluster has only {selected_cluster['article_count']} articles.")
                print("\nAvailable articles:")
                for i, article in enumerate(selected_cluster['articles'], 1):
                    print(f"{i}. {article['title']} ({article['name_source']})")
                
                override = input("Do you want to process this cluster anyway? (y/n): ").lower()
                if override == 'y':
                    return selected_cluster
                else:
                    analyzed_clusters.pop(choice)
                    if not analyzed_clusters:
                        print("No more clusters available.")
                        return None
                    print("Cluster removed. Please choose another cluster.")
            else:
                return selected_cluster
        else:
            print("Invalid choice. Please try again.")

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

        print(json.dumps(publish_data, indent=2))
        print("\nArticle references:")
        for article in articles_list:
            print(f"- {article['title']} ({article['name_source']}) - {article['link']}")

        # Save the publish.json file
        with open('publish.json', 'w') as f:
            json.dump(publish_data, f, indent=2)
            
        print("\npublish.json has been updated with the new article data.")
        
        # Remove the processed cluster
        analyzed_clusters.pop(cluster_index)
    else:
        print("Error: The generated article data is missing required fields.")
        retry = input("Would you like to retry? (y/n): ").lower()
        if retry == 'y':
            return present_menu_and_process(selected_cluster, analyzed_clusters)
        else:
            analyzed_clusters.pop(cluster_index)  # Remove the cluster if we're not retrying
            return None, analyzed_clusters

    return article_data, analyzed_clusters

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
