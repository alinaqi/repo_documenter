"""Main repository documenter class."""
import os
import sys
import time
import json
import logging
import anthropic
import subprocess
from pathlib import Path
from github import Github, GithubException

from ..utils.github import (
    check_gh_cli,
    extract_org_name,
    get_repositories,
    get_repository_summary,
    clone_repository
)
from ..utils.claude import generate_documentation
from ..services.documentation import (
    create_documentation_structure,
    analyze_repository,
    save_documentation
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
    
    def create_documentation(self, repo_path):
        """Generate documentation for a repository using Anthropic Claude."""
        repo_name = os.path.basename(repo_path)
        logger.info(f"Generating documentation for repository: {repo_name}")
        
        # Create docs directory structure
        docs_dir = create_documentation_structure(repo_path)
        
        # Analyze repository structure
        repo_analysis = analyze_repository(repo_path)
        
        # Generate documentation using Anthropic
        documentation = generate_documentation(repo_name, repo_analysis, self.anthropic_client)
        
        # Save documentation in appropriate files
        save_documentation(docs_dir, documentation)
        
        return True
    
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
                if clone_repository(minimal_repo, str(repo_dir), self.github_token, self.use_gh_cli):
                    print(f"Generating documentation for {repo_name}...")
                    self.create_documentation(str(repo_dir))
                    print(f"Documentation generated successfully for {repo_name}")
    
    def process_organization(self, github_org_url):
        """Process all repositories in the given GitHub organization."""
        try:
            # Extract organization name
            org_name = extract_org_name(github_org_url)
            logger.info(f"Processing organization: {org_name}")
            
            try:
                # Try using the GitHub API
                repositories = get_repositories(self.github_client, org_name)
                total_repos = len(repositories)
                logger.info(f"Found {total_repos} repositories using GitHub API")
                
                # Process each repository
                for idx, repo in enumerate(repositories, 1):
                    print(f"\n{'='*80}")
                    print(f"Repository {idx}/{total_repos}: {repo.name}")
                    print(f"{'='*80}")
                    
                    # Show repository summary
                    summary = get_repository_summary(repo)
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
                    if clone_repository(repo, str(repo_dir), self.github_token, self.use_gh_cli):
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

    def clone_and_setup_repos(self, github_org_url, skip_documentation=True):
        """
        Clone repositories and create documentation structure without generating documentation.
        
        Args:
            github_org_url (str): URL of the GitHub organization
            skip_documentation (bool): Whether to skip documentation generation (default: True)
        """
        try:
            # Extract organization name
            org_name = extract_org_name(github_org_url)
            logger.info(f"Processing organization: {org_name}")
            
            try:
                # Try using the GitHub API
                repositories = get_repositories(self.github_client, org_name)
                total_repos = len(repositories)
                logger.info(f"Found {total_repos} repositories using GitHub API")
                
                # Process each repository
                for idx, repo in enumerate(repositories, 1):
                    print(f"\n{'='*80}")
                    print(f"Repository {idx}/{total_repos}: {repo.name}")
                    print(f"{'='*80}")
                    
                    # Show repository summary
                    summary = get_repository_summary(repo)
                    print(summary)
                    
                    # Ask for confirmation
                    while True:
                        response = input("\nDo you want to clone this repository? (y/n): ").lower()
                        if response in ['y', 'n']:
                            break
                        print("Please enter 'y' or 'n'")
                    
                    if response == 'n':
                        print(f"Skipping repository {repo.name}")
                        continue
                    
                    repo_dir = self.output_dir / repo.name
                    
                    # Clone repository
                    print(f"\nCloning repository {repo.name}...")
                    if clone_repository(repo, str(repo_dir), self.github_token, self.use_gh_cli):
                        # Create documentation structure
                        print(f"Creating documentation structure for {repo.name}...")
                        create_documentation_structure(str(repo_dir))
                        print(f"Repository cloned and documentation structure created for {repo.name}")
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
                                    response = input("\nDo you want to clone this repository? (y/n): ").lower()
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
                                    # Create documentation structure
                                    print(f"Creating documentation structure for {repo_data['name']}...")
                                    create_documentation_structure(str(repo_dir))
                                    print(f"Repository cloned and documentation structure created for {repo_data['name']}")
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