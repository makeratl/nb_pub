# NB Publisher

NB Publisher is a Python-based project for generating and publishing AI-powered news articles with haiku backgrounds, supporting multiple LLM backends including LMStudio and CodeGPT.

## Features

- Generate news articles based on clustered headlines using multiple LLM backends
- Create and customize haiku backgrounds for articles with text overlay
- Support for local LLM inference using LMStudio
- CodeGPT integration for article generation
- Automated article review and publishing workflow
- Configurable LLM settings and chat interfaces
- Environment validation and setup tools
- Image processing and legacy image update utilities

## Components

- `nb_research.py` / `nb_research_lmstudio.py`: Main article generation scripts
- `lmstudio_config.py`: Configuration for LMStudio backend
- `lmstudio_chat.py`: Chat interface for LMStudio
- `chat_codegpt.py`: Chat interface for CodeGPT
- `review_articles.py`: Article review and processing
- `publishhaiku.py`: Haiku generation and publishing
- `haikubackground.py`: Background image generation
- `update_legacy_images.py`: Tool for updating existing images
- `check_env.py`: Environment validation utility
- `testchat.py`: Chat interface testing utility

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/nb_publisher.git
   cd nb_publisher
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the project root and add the following variables:
   ```
   CODEGPT_API_KEY=your_codegpt_api_key
   CODEGPT_ORG_ID=your_codegpt_org_id
   CODEGPT_AGENT_ID=your_codegpt_agent_id
   PUBLISH_API_KEY=your_publish_api_key
   LMSTUDIO_HOST=your_lmstudio_host  # Optional, for LMStudio backend
   ```

## Usage

### Using LMStudio Backend

1. Start your LMStudio server with desired model
2. Run the LMStudio version of the research script:
   ```
   python nb_research_lmstudio.py
   ```

### Using CodeGPT Backend

1. Run the CodeGPT version:
   ```
   python nb_research.py
   ```

### Testing and Utilities

- Validate environment: `python check_env.py`
- Test chat interfaces: `python testchat.py`
- Update legacy images: `python update_legacy_images.py`

The system will monitor the `publish.json` file for changes and automatically publish new articles.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.