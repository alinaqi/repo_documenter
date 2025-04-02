import os
import sys
import time
import json
import shutil
import logging
import anthropic
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from github import Github, GithubException
from urllib.parse import urlparse

# Load environment variables from .env file
load_dotenv()

# Check if GitHub CLI is installed
def check_gh_cli():
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("repo_documenter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RepoDocumenter")

class RepoDocumenter:
    """Tool to clone and document GitHub repositories using Anthropic's Claude."""
    
    def __init__(self, github_token, anthropic_api_key, output_dir="./repositories"):
        """
        Initialize the repository documenter.
        
        Args:
            github_token (str): GitHub Personal Access Token
            anthropic_api_key (str): Anthropic API key
            output_dir (str): Directory to store cloned repositories
        """
        self.github_token = github_token
        self.github_client = Github(github_token)
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if GitHub CLI is available
        self.use_gh_cli = check_gh_cli()
        if self.use_gh_cli:
            logger.info("GitHub CLI detected, will use for repository operations")
        else:
            logger.warning("GitHub CLI not found, falling back to git commands")
            logger.warning("For SAML-protected organizations, we recommend installing GitHub CLI: https://cli.github.com/")
        
    def extract_org_name(self, github_url):
        """Extract organization name from GitHub URL."""
        parsed_url = urlparse(github_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # Handle different URL formats
        if len(path_parts) >= 2 and path_parts[0] == 'orgs':
            return path_parts[1]
        elif len(path_parts) >= 1:
            # If URL is in format github.com/orgname or similar
            return path_parts[0]
        
        logger.error(f"Could not extract organization name from URL: {github_url}")
        raise ValueError(f"Invalid GitHub organization URL: {github_url}")
    
    def get_repositories(self, org_name):
        """Get all repositories for the given organization."""
        try:
            org = self.github_client.get_organization(org_name)
            repos = list(org.get_repos())
            logger.info(f"Found {len(repos)} repositories in organization {org_name}")
            return repos
        except GithubException as e:
            logger.error(f"Error getting repositories for {org_name}: {e}")
            raise

    def get_repository_summary(self, repo):
        """Get a summary of the repository including README and last update."""
        try:
            # Get repository details
            name = repo.name
            description = repo.description or "No description available"
            last_updated = repo.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            stars = repo.stargazers_count
            forks = repo.forks_count
            
            # Try to get README content
            readme_content = "No README found"
            try:
                readme = repo.get_readme()
                readme_content = readme.decoded_content.decode('utf-8')
            except:
                pass
            
            # Create summary
            summary = f"""
Repository: {name}
Description: {description}
Last Updated: {last_updated}
Stars: {stars} | Forks: {forks}

README Preview:
{readme_content[:500]}{'...' if len(readme_content) > 500 else ''}
"""
            return summary
        except Exception as e:
            logger.error(f"Error getting repository summary: {e}")
            return f"Error getting summary for repository {repo.name}"

    def clone_repository(self, repo, target_dir):
        """Clone a repository to the target directory."""
        repo_name = repo.name if hasattr(repo, 'name') else os.path.basename(str(target_dir))
        repo_owner = repo.owner.login if hasattr(repo, 'owner') else None
        repo_full_name = f"{repo_owner}/{repo_name}" if repo_owner else repo_name
        
        try:
            if os.path.exists(target_dir):
                logger.info(f"Repository already exists at {target_dir}, pulling latest changes")
                # Pull the latest changes if the repository already exists
                if self.use_gh_cli:
                    process = subprocess.run(
                        ['gh', 'repo', 'sync', repo_full_name, '--source', 'upstream', '--branch', 'main'],
                        cwd=target_dir,
                        capture_output=True,
                        text=True
                    )
                else:
                    process = subprocess.run(
                        ['git', '-C', target_dir, 'pull', 'origin', 'main'],
                        capture_output=True,
                        text=True
                    )
                
                if process.returncode != 0:
                    logger.warning(f"Failed to pull latest changes: {process.stderr}")
                    logger.warning(f"Continuing with existing repository files")
            else:
                logger.info(f"Cloning repository {repo_name} to {target_dir}")
                
                if self.use_gh_cli:
                    # Clone using GitHub CLI
                    process = subprocess.run(
                        ['gh', 'repo', 'clone', repo_full_name, target_dir],
                        capture_output=True,
                        text=True
                    )
                else:
                    # Fall back to git with token authentication for private repositories
                    clone_url = repo.clone_url if hasattr(repo, 'clone_url') else f"https://github.com/{repo_full_name}.git"
                    auth_url = clone_url.replace('https://', f'https://{self.github_token}@')
                    
                    process = subprocess.run(
                        ['git', 'clone', auth_url, target_dir],
                        capture_output=True,
                        text=True
                    )
                
                if process.returncode != 0:
                    logger.error(f"Clone output: {process.stdout}")
                    logger.error(f"Clone error: {process.stderr}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error cloning repository {repo_name}: {e}")
            return False
    
    def create_documentation(self, repo_path):
        """Generate documentation for a repository using Anthropic Claude."""
        repo_name = os.path.basename(repo_path)
        logger.info(f"Generating documentation for repository: {repo_name}")
        
        # Create docs directory structure
        docs_dir = os.path.join(repo_path, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        
        # Create subdirectories for different documentation types
        subdirs = [
            "getting-started",
            "data-models",
            "flows",
            "architecture",
            "faqs"
        ]
        for subdir in subdirs:
            os.makedirs(os.path.join(docs_dir, subdir), exist_ok=True)
        
        # Analyze repository structure
        repo_analysis = self._analyze_repository(repo_path)
        
        # Generate documentation using Anthropic
        documentation = self._generate_documentation_with_claude(repo_name, repo_analysis)
        
        # Save documentation in appropriate files
        self._save_documentation(docs_dir, documentation)
        
        return True
    
    def _analyze_repository(self, repo_path):
        """Analyze repository structure and gather key information."""
        logger.info(f"Analyzing repository structure at {repo_path}")
        
        # Get list of all files
        all_files = []
        for root, _, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in root:
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                
                # Skip binary files and very large files
                try:
                    if os.path.getsize(file_path) > 1000000:  # Skip files larger than 1MB
                        all_files.append({"path": rel_path, "content": "File too large to analyze"})
                        continue
                        
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    all_files.append({"path": rel_path, "content": content})
                except Exception as e:
                    logger.warning(f"Could not read file {rel_path}: {e}")
                    all_files.append({"path": rel_path, "content": "Could not read file"})
        
        # Find key files
        readme = next((f for f in all_files if f["path"].lower() == "readme.md"), None)
        
        return {
            "files": all_files,
            "readme": readme,
            "total_files": len(all_files)
        }
    
    def _generate_documentation_with_claude(self, repo_name, repo_analysis):
        """Generate documentation using Anthropic Claude."""
        logger.info(f"Generating documentation with Claude for {repo_name}")
        
        # Prepare repository data for Claude
        files_to_analyze = repo_analysis["files"]
        
        # Create prompt for Claude
        prompt = self._create_documentation_prompt(repo_name, repo_analysis)
        
        try:
            # Call Anthropic API with the latest model
            response = self.anthropic_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0,
                system="You are a technical documentation expert. Analyze the repository files and create comprehensive documentation including getting started guide, data elements, flow charts, architecture overview, and FAQs.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract documentation from response
            documentation = response.content[0].text
            return documentation
            
        except Exception as e:
            logger.error(f"Error generating documentation with Claude: {e}")
            return f"# Documentation Generation Failed\n\nError: {str(e)}"
    
    def _create_documentation_prompt(self, repo_name, repo_analysis):
        """Create prompt for Claude to generate documentation."""
        readme_content = repo_analysis.get("readme", {}).get("content", "No README found")
        
        # Get some key files to include in the prompt
        important_file_types = [".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".cs"]
        important_files = []
        
        # Find important files (limit to 10 to avoid token limits)
        for file in repo_analysis["files"]:
            if any(file["path"].endswith(ext) for ext in important_file_types):
                important_files.append(file)
                if len(important_files) >= 10:
                    break
        
        # Create the prompt
        prompt = f"""
# Repository Analysis Task: {repo_name}

Your task is to create comprehensive documentation for this repository. Based on the files I'll show you, please create separate documentation sections:

1. Getting Started Guide
2. Data Models Documentation
3. Flow Charts (using Mermaid syntax)
4. Architecture Overview
5. FAQs

## Repository Overview

The repository name is: {repo_name}
Total number of files: {repo_analysis["total_files"]}

## README Content

{readme_content}

## Key Files in the Repository

"""

        # Add key files
        for file in important_files:
            prompt += f"\n### File: {file['path']}\n"
            prompt += "```\n"
            # Limit content to avoid exceeding token limits
            prompt += file["content"][:5000] + ("..." if len(file["content"]) > 5000 else "")
            prompt += "\n```\n"
        
        prompt += """
## Documentation Deliverables

Please create the following documentation sections in separate Markdown files:

1. **Getting Started Guide** (getting-started/README.md)
   - Prerequisites
   - Installation steps
   - Basic usage examples
   - Configuration options

2. **Data Models Documentation** (data-models/README.md)
   - Key data structures/models
   - Database schema (if applicable)
   - API endpoints (if applicable)
   - Data flow diagrams

3. **Flow Charts** (flows/README.md)
   - Application workflow diagrams
   - Data flow diagrams
   - Process flow diagrams
   - Use Mermaid syntax for all diagrams

4. **Architecture Overview** (architecture/README.md)
   - System architecture
   - Key components/modules
   - Design patterns used
   - Important functions/classes
   - Integration points

5. **FAQs** (faqs/README.md)
   - Common questions and answers
   - Troubleshooting guide
   - Best practices
   - Known issues and workarounds

Please format each section as a separate Markdown file with clear headings and proper formatting.
"""
        
        return prompt
    
    def _save_documentation(self, docs_dir, documentation):
        """Save generated documentation to the appropriate files in the docs directory."""
        try:
            # Split documentation into sections
            sections = {
                "getting-started": "## Getting Started Guide",
                "data-models": "## Data Models Documentation",
                "flows": "## Flow Charts",
                "architecture": "## Architecture Overview",
                "faqs": "## FAQs"
            }
            
            # Create main README.md with links to all sections
            main_readme = "# Documentation\n\n"
            for section, heading in sections.items():
                main_readme += f"- [{heading.replace('## ', '')}]({section}/README.md)\n"
            
            with open(os.path.join(docs_dir, "README.md"), 'w', encoding='utf-8') as f:
                f.write(main_readme)
            
            # Save each section to its respective file
            for section, heading in sections.items():
                section_dir = os.path.join(docs_dir, section)
                section_content = self._extract_section(documentation, heading)
                
                if section_content:
                    with open(os.path.join(section_dir, "README.md"), 'w', encoding='utf-8') as f:
                        f.write(section_content)
            
            logger.info(f"Documentation saved to {docs_dir}")
            return True
        except Exception as e:
            logger.error(f"Error saving documentation: {e}")
            return False
    
    def _extract_section(self, documentation, heading):
        """Extract a specific section from the documentation."""
        try:
            # Find the start of the section
            start_idx = documentation.find(heading)
            if start_idx == -1:
                return None
            
            # Find the start of the next section
            next_sections = [s for s in [
                "## Getting Started Guide",
                "## Data Models Documentation",
                "## Flow Charts",
                "## Architecture Overview",
                "## FAQs"
            ] if s != heading]
            
            end_idx = len(documentation)
            for next_section in next_sections:
                next_idx = documentation.find(next_section, start_idx)
                if next_idx != -1 and next_idx < end_idx:
                    end_idx = next_idx
            
            # Extract the section content
            section_content = documentation[start_idx:end_idx].strip()
            return section_content
        except Exception as e:
            logger.error(f"Error extracting section {heading}: {e}")
            return None
    
    def clone_repository_cli(self, repo_full_name, target_dir):
        """Clone a repository using GitHub CLI."""
        try:
            if os.path.exists(target_dir):
                logger.info(f"Repository already exists at {target_dir}, pulling latest changes")
                process = subprocess.run(
                    ['gh', 'repo', 'sync', repo_full_name],
                    cwd=target_dir,
                    capture_output=True,
                    text=True
                )
            else:
                logger.info(f"Cloning repository {repo_full_name} to {target_dir}")
                process = subprocess.run(
                    ['gh', 'repo', 'clone', repo_full_name, target_dir],
                    capture_output=True,
                    text=True
                )
                
            if process.returncode != 0:
                logger.error(f"GitHub CLI clone output: {process.stdout}")
                logger.error(f"GitHub CLI clone error: {process.stderr}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error cloning repository {repo_full_name} with GitHub CLI: {e}")
            return False
            
    def manual_repository_input(self, org_name):
        """Prompt user for manual repository input."""
        logger.info("Prompting user for manual repository input")
        
        print("\nUnable to automatically list repositories.")
        print("Please provide repository names (comma-separated) to clone and document:")
        repo_input = input("> ")
        
        repo_names = [name.strip() for name in repo_input.split(",")]
        total_repos = len(repo_names)
        
        for idx, repo_name in enumerate(repo_names, 1):
            if not repo_name:
                continue
                
            print(f"\n{'='*80}")
            print(f"Repository {idx}/{total_repos}: {repo_name}")
            print(f"{'='*80}")
            
            repo_dir = self.output_dir / repo_name
            repo_full_name = f"{org_name}/{repo_name}"
            
            # Try to get repository info using GitHub CLI
            if self.use_gh_cli:
                try:
                    process = subprocess.run(
                        ['gh', 'repo', 'view', repo_full_name, '--json', 'name,description,updatedAt,stargazerCount,forkCount'],
                        capture_output=True,
                        text=True
                    )
                    
                    if process.returncode == 0:
                        repo_data = json.loads(process.stdout)
                        summary = f"""
Repository: {repo_data['name']}
Description: {repo_data.get('description', 'No description available')}
Last Updated: {repo_data['updatedAt']}
Stars: {repo_data['stargazerCount']} | Forks: {repo_data['forkCount']}
"""
                        print(summary)
                except:
                    pass
            
            # Ask for confirmation
            while True:
                response = input("\nDo you want to document this repository? (y/n): ").lower()
                if response in ['y', 'n']:
                    break
                print("Please enter 'y' or 'n'")
            
            if response == 'n':
                print(f"Skipping repository {repo_name}")
                continue
            
            if self.use_gh_cli:
                # Try with GitHub CLI first
                print(f"\nCloning repository {repo_name}...")
                if self.clone_repository_cli(repo_full_name, str(repo_dir)):
                    print(f"Generating documentation for {repo_name}...")
                    self.create_documentation(str(repo_dir))
                    print(f"Documentation generated successfully for {repo_name}")
            else:
                # Create a minimal repo object
                class MinimalRepo:
                    def __init__(self, name, full_name):
                        self.name = name
                        self.full_name = full_name
                        self.clone_url = f"https://github.com/{full_name}.git"
                        
                        class Owner:
                            def __init__(self, login):
                                self.login = login
                        
                        self.owner = Owner(full_name.split('/')[0])
                
                minimal_repo = MinimalRepo(repo_name, repo_full_name)
                
                print(f"\nCloning repository {repo_name}...")
                if self.clone_repository(minimal_repo, str(repo_dir)):
                    print(f"Generating documentation for {repo_name}...")
                    self.create_documentation(str(repo_dir))
                    print(f"Documentation generated successfully for {repo_name}")
    
    def process_organization(self, github_org_url):
        """Process all repositories in the given GitHub organization."""
        try:
            # Extract organization name
            org_name = self.extract_org_name(github_org_url)
            logger.info(f"Processing organization: {org_name}")
            
            try:
                # Try using the GitHub API
                repositories = self.get_repositories(org_name)
                total_repos = len(repositories)
                logger.info(f"Found {total_repos} repositories using GitHub API")
                
                # Process each repository
                for idx, repo in enumerate(repositories, 1):
                    print(f"\n{'='*80}")
                    print(f"Repository {idx}/{total_repos}: {repo.name}")
                    print(f"{'='*80}")
                    
                    # Show repository summary
                    summary = self.get_repository_summary(repo)
                    print(summary)
                    
                    # Ask for confirmation
                    while True:
                        response = input("\nDo you want to document this repository? (y/n): ").lower()
                        if response in ['y', 'n']:
                            break
                        print("Please enter 'y' or 'n'")
                    
                    if response == 'n':
                        print(f"Skipping repository {repo.name}")
                        continue
                    
                    repo_dir = self.output_dir / repo.name
                    
                    # Clone repository
                    print(f"\nCloning repository {repo.name}...")
                    if self.clone_repository(repo, str(repo_dir)):
                        # Generate documentation
                        print(f"Generating documentation for {repo.name}...")
                        self.create_documentation(str(repo_dir))
                        print(f"Documentation generated successfully for {repo.name}")
                    else:
                        print(f"Failed to clone repository {repo.name}")
                    
                    # Add small delay to avoid rate limits
                    time.sleep(1)
                
            except GithubException as api_error:
                # If GitHub API fails due to SAML enforcement or other issues
                logger.warning(f"GitHub API error: {api_error}")
                
                if self.use_gh_cli:
                    logger.info("Using GitHub CLI to list repositories")
                    
                    # Use GitHub CLI to list repositories
                    try:
                        process = subprocess.run(
                            ['gh', 'repo', 'list', org_name, '--limit', '100', '--json', 'name,description,updatedAt,stargazerCount,forkCount', '--jq', '.[]'],
                            capture_output=True,
                            text=True
                        )
                        
                        if process.returncode == 0:
                            repos_data = json.loads(process.stdout)
                            total_repos = len(repos_data)
                            
                            for idx, repo_data in enumerate(repos_data, 1):
                                print(f"\n{'='*80}")
                                print(f"Repository {idx}/{total_repos}: {repo_data['name']}")
                                print(f"{'='*80}")
                                
                                # Show repository summary
                                summary = f"""
Repository: {repo_data['name']}
Description: {repo_data.get('description', 'No description available')}
Last Updated: {repo_data['updatedAt']}
Stars: {repo_data['stargazerCount']} | Forks: {repo_data['forkCount']}
"""
                                print(summary)
                                
                                # Ask for confirmation
                                while True:
                                    response = input("\nDo you want to document this repository? (y/n): ").lower()
                                    if response in ['y', 'n']:
                                        break
                                    print("Please enter 'y' or 'n'")
                                
                                if response == 'n':
                                    print(f"Skipping repository {repo_data['name']}")
                                    continue
                                
                                repo_dir = self.output_dir / repo_data['name']
                                repo_full_name = f"{org_name}/{repo_data['name']}"
                                
                                # Clone using GitHub CLI
                                print(f"\nCloning repository {repo_data['name']}...")
                                if self.clone_repository_cli(repo_full_name, str(repo_dir)):
                                    # Generate documentation
                                    print(f"Generating documentation for {repo_data['name']}...")
                                    self.create_documentation(str(repo_dir))
                                    print(f"Documentation generated successfully for {repo_data['name']}")
                                else:
                                    print(f"Failed to clone repository {repo_data['name']}")
                                
                                # Add small delay to avoid rate limits
                                time.sleep(1)
                        else:
                            logger.error(f"Error listing repositories with GitHub CLI: {process.stderr}")
                            self.manual_repository_input(org_name)
                            
                    except subprocess.CalledProcessError as e:
                        logger.error(f"GitHub CLI error: {e}")
                        self.manual_repository_input(org_name)
                else:
                    # If GitHub CLI is not available, prompt for manual input
                    self.manual_repository_input(org_name)
            
            logger.info(f"Completed processing organization: {org_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing organization: {e}")
            return False

def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python repo_documenter.py <github_org_url>")
        print("Make sure to set GITHUB_TOKEN and ANTHROPIC_API_KEY in your .env file")
        sys.exit(1)
    
    # Get the GitHub organization URL from command line argument
    github_org_url = sys.argv[1]
    
    # Get API tokens from environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Check if tokens are available
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set. Please add it to your .env file.")
        sys.exit(1)
    
    if not anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set. Please add it to your .env file.")
        sys.exit(1)
    
    # Initialize the documenter and process the organization
    documenter = RepoDocumenter(github_token, anthropic_api_key)
    documenter.process_organization(github_org_url)

if __name__ == "__main__":
    main()