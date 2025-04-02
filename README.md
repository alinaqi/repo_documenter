# Repository Documentation Generator

A powerful AI-driven tool that automatically generates comprehensive documentation for any GitHub organization, enabling developers to understand and contribute to any codebase within 15 minutes.

## Mission: Zero-Day Onboarding

Our mission is to eliminate the traditional weeks-long onboarding process by providing instant, comprehensive understanding of any codebase. We believe that:

- Every developer should be able to understand any codebase within 15 minutes
- Documentation should be intelligent, accurate, and always up-to-date
- AI can bridge the gap between code complexity and human understanding
- Great documentation is the foundation of efficient collaboration

## Features

- **Repository Discovery**: Automatically finds all repositories in a GitHub organization
- **Intelligent Cloning**: Clones repositories locally with proper authentication
- **AI-Powered Documentation**: Uses Claude to analyze codebases and create detailed documentation
- **Documentation Components**:
  - Getting started guides
  - Data elements and models documentation
  - Flow charts (using Mermaid syntax)
  - Complete code architecture overviews

## How It Works

1. **Repository Discovery**: Automatically finds and analyzes all repositories in a GitHub organization
2. **Intelligent Cloning**: Clones repositories with proper authentication and access control
3. **AI-Powered Analysis**: Uses Claude AI to deeply understand the codebase structure, patterns, and purpose
4. **Comprehensive Documentation**: Generates detailed, human-readable documentation that covers:
   - Getting started guides
   - Architecture overviews
   - Data models and flows
   - API documentation
   - Best practices and patterns
   - Common pitfalls and solutions

## Key Features

- **Instant Understanding**: Get up to speed with any codebase in minutes, not weeks
- **AI-Powered Insights**: Deep understanding of code patterns and architecture
- **Comprehensive Coverage**: Documentation for every aspect of the codebase
- **Always Up-to-Date**: Automatically updates with code changes
- **Developer-Focused**: Documentation designed for quick comprehension and contribution

## Documentation Components

For each repository, we generate:

- **Getting Started Guide**
  - Quick setup instructions
  - Essential prerequisites
  - First-time contribution guide
  - Common development workflows

- **Architecture Overview**
  - System design and components
  - Data flow diagrams
  - Key architectural decisions
  - Technology stack details

- **Data Elements Documentation**
  - Data models and schemas
  - Database structure
  - API endpoints and contracts
  - Integration points

- **Flow Charts**
  - Application workflows
  - Data processing pipelines
  - System interactions
  - Error handling flows

- **Code Overview**
  - Key components and modules
  - Design patterns used
  - Important functions and classes
  - Common coding patterns

## Requirements

- Python 3.7+
- GitHub Personal Access Token
- Anthropic API Key
- GitHub CLI (recommended for SAML-protected organizations)

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

## Benefits

- **For New Developers**
  - Instant understanding of codebase
  - Clear contribution guidelines
  - Reduced onboarding time
  - Faster time to first commit

- **For Teams**
  - Consistent documentation
  - Reduced knowledge silos
  - Better code maintainability
  - Improved collaboration

- **For Organizations**
  - Faster developer onboarding
  - Reduced training costs
  - Better code quality
  - Improved knowledge sharing

## Configuration

You can modify these parameters in the script:

- `output_dir`: Directory where repositories will be cloned (default: "./repositories")
- Claude model: Change the model in the `_generate_documentation_with_claude` method (default: "claude-3-opus-20240229")

## Limitations

- **Rate Limiting**: Both GitHub API and Anthropic API have rate limits
- **Repository Size**: Very large repositories may be partially analyzed due to token limits
- **File Types**: The script prioritizes common code files (.py, .js, .ts, etc.)

## Handling SAML-Protected Organizations

For organizations using SAML SSO (Single Sign-On), we recommend using GitHub CLI:

1. **Install GitHub CLI**:
   - Follow instructions at [cli.github.com](https://cli.github.com/)
   - The script will automatically detect and use GitHub CLI if available

2. **Authenticate with GitHub CLI**:
   ```bash
   gh auth login
   ```
   - Follow the prompts to authenticate
   - For SAML organizations, you'll be prompted to authorize the CLI

3. **Running with GitHub CLI**:
   - The script will automatically use GitHub CLI when available
   - GitHub CLI handles SAML authentication seamlessly

If GitHub CLI is not available, the script will fall back to standard Git commands and may prompt you for repository names if it encounters authentication issues.

## License

[MIT License](LICENSE)

## Contributing

We welcome contributions to help us achieve our mission of zero-day onboarding! Please feel free to submit a Pull Request.