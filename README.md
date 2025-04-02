# Repository Documentation Generator

A Python tool that automatically clones GitHub repositories from an organization and generates comprehensive documentation using Anthropic's Claude AI.

## Features

- **Repository Discovery**: Automatically finds all repositories in a GitHub organization
- **Intelligent Cloning**: Clones repositories locally with proper authentication
- **AI-Powered Documentation**: Uses Claude to analyze codebases and create detailed documentation
- **Documentation Components**:
  - Getting started guides
  - Data elements and models documentation
  - Flow charts (using Mermaid syntax)
  - Complete code architecture overviews

## Requirements

- Python 3.7+
- GitHub Personal Access Token
- Anthropic API Key

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/repo-documentation-generator.git
   cd repo-documentation-generator
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   Or install dependencies directly:
   ```bash
   pip install PyGithub anthropic requests gitpython markdown python-dotenv
   ```

## Usage

1. Create a `.env` file in the project directory with your API keys:
   ```
   GITHUB_TOKEN=your_github_token_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

2. Run the script with the following command:
   ```bash
   python repo_documenter.py <github_org_url>
   ```

   Example:
   ```bash
   python repo_documenter.py https://github.com/orgs/your-organization/repositories
   ```

## How It Works

1. **Organization Analysis**: The script parses the GitHub organization URL and retrieves all repositories.
2. **Repository Cloning**: Each repository is cloned to a local directory structure.
3. **Code Analysis**: The script analyzes each repository's structure, identifying key files and patterns.
4. **Documentation Generation**: Claude AI analyzes the codebase and generates comprehensive documentation.
5. **Output**: Documentation is saved as Markdown files in a `/docs` folder within each repository.

## Documentation Structure

For each repository, the script generates:

- **Getting Started Guide**
  - Prerequisites
  - Installation steps
  - Basic usage examples

- **Data Elements Documentation**
  - Key data structures/models
  - Database schema (if applicable)
  - API endpoints (if applicable)

- **Flow Charts**
  - Application workflow
  - Data flow
  - Key processes
  (Using Mermaid syntax)

- **Code Overview**
  - Architecture description
  - Key components/modules
  - Design patterns used
  - Important functions/classes

## Configuration

You can modify these parameters in the script:

- `output_dir`: Directory where repositories will be cloned (default: "./repositories")
- Claude model: Change the model in the `_generate_documentation_with_claude` method (default: "claude-3-opus-20240229")

## Limitations

- **Rate Limiting**: Both GitHub API and Anthropic API have rate limits
- **Repository Size**: Very large repositories may be partially analyzed due to token limits
- **File Types**: The script prioritizes common code files (.py, .js, .ts, etc.)

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.