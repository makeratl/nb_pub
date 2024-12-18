# AI News Brew

AI News Brew is a Python-based project for generating and publishing AI-powered news articles. It has evolved from a series of Python scripts into a full-fledged web application dashboard with expanding capabilities.

## Key Features

- Fetch latest news headlines and articles using the NewsCatcher API
- Analyze news clusters to identify common topics, categories, subjects, and political bias
- Generate AI-written news articles based on selected news clusters 
- Create customized haiku background images for articles with text overlay
- Automated article review process with AI evaluation and user feedback
- Publish articles to the AI News Brew platform with images
- Web-based research and publishing interface built with Streamlit
- Support for multiple LLM backends, including CodeGPT and LMStudio
- Configurable LLM settings and prompts for article generation and analysis
- Utilities for environment validation, chat interface testing, and legacy image updates

## Main Components

- `web_research.py`: Web application dashboard for news research and publishing
- `nb_research.py`: Main script for fetching news, analyzing clusters, and generating articles
- `review_articles.py`: Automated article review process with AI evaluation 
- `publish_utils.py`: Utilities for generating haiku images and publishing articles
- `lmstudio_config.py` / `lmstudio_chat.py`: Configuration and chat interface for LMStudio backend
- `chat_codegpt.py`: Chat interface for CodeGPT backend
- `haikubackground.py` / `publishhaiku.py`: Haiku generation and image creation
- `modules/`: Additional utility modules for the web app (state management, API clients, display formatting, etc.)

## Setup and Usage

1. Clone the repository and install dependencies:
   ```
   git clone https://github.com/yourusername/ainewsbrew.git
   cd ainewsbrew
   pip install -r requirements.txt
   ```

2. Set up required environment variables in a `.env` file:
   ```
   NEWSCATCHER_API_KEY=your_newscatcher_api_key
   PUBLISH_API_KEY=your_publish_api_key
   CODEGPT_API_KEY=your_codegpt_api_key
   CODEGPT_ORG_ID=your_codegpt_org_id
   CODEGPT_AGENT_ID=your_codegpt_agent_id
   LMSTUDIO_HOST=your_lmstudio_host  # Optional, for LMStudio backend
   ```

3. Run the web application:
   ```
   streamlit run web_research.py
   ```

4. Access the web interface at `http://localhost:8501` to research news, analyze clusters, generate articles, and publish.

5. Alternatively, run the command-line scripts directly:
   - Fetch news and generate articles: `python nb_research.py`
   - Review and process articles: `python review_articles.py`

6. Utility scripts:
   - Check environment setup: `python check_env.py` 
   - Test chat interfaces: `python testchat.py`
   - Update legacy haiku images: `python update_legacy_images.py`

## Contributing

Contributions to improve and expand the capabilities of AI News Brew are welcome! Please submit a pull request or open an issue to discuss proposed changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.