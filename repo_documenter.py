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
        
    def extract_org_name(self, github_url):
        """Extract organization name from GitHub URL."""
        parsed_url = urlparse(github_url)
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) >= 2 and path_parts[0] == 'orgs':
            return path_parts[1]
        
        logger.error(f"Could not extract organization name from URL: {github_url}")
        raise ValueError(f"Invalid GitHub organization URL: {github_url}")
    
    def get_repositories(self, org_name):
        """Get all repositories for the given organization."""
        try:
            org = self.github_client.get_organization(org_name)
            return list(org.get_repos())
        except GithubException as e:
            logger.error(f"Error getting repositories for {org_name}: {e}")
            raise
    
    def clone_repository(self, repo, target_dir):
        """Clone a repository to the target directory."""
        clone_url = repo.clone_url
        # Use token authentication for private repositories
        auth_url = clone_url.replace('https://', f'https://{self.github_token}@')
        
        try:
            if os.path.exists(target_dir):
                logger.info(f"Repository already exists at {target_dir}, pulling latest changes")
                # Pull the latest changes if the repository already exists
                subprocess.run(
                    ['git', '-C', target_dir, 'pull', 'origin', 'main'],
                    check=True,
                    capture_output=True
                )
            else:
                logger.info(f"Cloning repository {repo.name} to {target_dir}")
                subprocess.run(
                    ['git', 'clone', auth_url, target_dir],
                    check=True,
                    capture_output=True
                )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error cloning repository {repo.name}: {e}")
            return False
    
    def create_documentation(self, repo_path):
        """Generate documentation for a repository using Anthropic Claude."""
        repo_name = os.path.basename(repo_path)
        logger.info(f"Generating documentation for repository: {repo_name}")
        
        # Create docs directory if it doesn't exist
        docs_dir = os.path.join(repo_path, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        
        # Analyze repository structure
        repo_analysis = self._analyze_repository(repo_path)
        
        # Generate documentation using Anthropic
        documentation = self._generate_documentation_with_claude(repo_name, repo_analysis)
        
        # Save documentation
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
        # We'll need to chunk large repositories
        files_to_analyze = repo_analysis["files"]
        
        # Create prompt for Claude
        prompt = self._create_documentation_prompt(repo_name, repo_analysis)
        
        try:
            # Call Anthropic API
            response = self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4000,
                temperature=0,
                system="You are a technical documentation expert. Analyze the repository files and create comprehensive documentation including getting started guide, data elements, flow charts and code overview.",
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

Your task is to create comprehensive documentation for this repository. Based on the files I'll show you, please create:

1. A Getting Started guide
2. Data Elements/Models documentation
3. Flow charts (using Mermaid syntax)
4. Code architecture overview

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

Please create the following documentation in Markdown format:

1. **Getting Started Guide**
   - Prerequisites
   - Installation steps
   - Basic usage examples

2. **Data Elements Documentation**
   - Key data structures/models
   - Database schema (if applicable)
   - API endpoints (if applicable)

3. **Flow Charts**
   - Application workflow
   - Data flow
   - Key processes
   (Use Mermaid syntax for these diagrams)

4. **Code Overview**
   - Architecture description
   - Key components/modules
   - Design patterns used
   - Important functions/classes

Please format your response as a single Markdown document with clear sections.
"""
        
        return prompt
    
    def _save_documentation(self, docs_dir, documentation):
        """Save generated documentation to the docs directory."""
        try:
            # Save main documentation file
            main_doc_path = os.path.join(docs_dir, "README.md")
            with open(main_doc_path, 'w', encoding='utf-8') as f:
                f.write(documentation)
            
            logger.info(f"Documentation saved to {main_doc_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving documentation: {e}")
            return False
    
    def process_organization(self, github_org_url):
        """Process all repositories in the given GitHub organization."""
        try:
            # Extract organization name
            org_name = self.extract_org_name(github_org_url)
            logger.info(f"Processing organization: {org_name}")
            
            # Get all repositories
            repositories = self.get_repositories(org_name)
            logger.info(f"Found {len(repositories)} repositories")
            
            # Process each repository
            for repo in repositories:
                repo_dir = self.output_dir / repo.name
                
                # Clone repository
                if self.clone_repository(repo, str(repo_dir)):
                    # Generate documentation
                    self.create_documentation(str(repo_dir))
                    
                    # Add small delay to avoid rate limits
                    time.sleep(1)
            
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