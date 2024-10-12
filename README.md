# NB Publisher

NB Publisher is a Python-based project for generating and publishing AI-powered news articles with haiku backgrounds.

## Features

- Generate news articles based on clustered headlines
- Create haiku backgrounds for articles
- Publish articles to a specified API endpoint
- Monitor file changes for automatic publishing

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
   ```

## Usage

1. Run the main script:
   ```
   python nb_research.py
   ```

2. Follow the prompts to search for news, generate articles, and publish them.

3. The script will monitor the `publish.json` file for changes and automatically publish new articles.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.