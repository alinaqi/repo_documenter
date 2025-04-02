"""GitHub utilities for repository operations."""
import os
import subprocess
import logging
from urllib.parse import urlparse
from github import Github, GithubException

logger = logging.getLogger("RepoDocumenter")

def check_gh_cli():
    """Check if GitHub CLI is installed."""
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def extract_org_name(github_url):
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

def get_repositories(github_client, org_name):
    """Get all repositories for the given organization."""
    try:
        org = github_client.get_organization(org_name)
        repos = list(org.get_repos())
        logger.info(f"Found {len(repos)} repositories in organization {org_name}")
        return repos
    except GithubException as e:
        logger.error(f"Error getting repositories for {org_name}: {e}")
        raise

def get_repository_summary(repo):
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

def clone_repository(repo, target_dir, github_token, use_gh_cli):
    """Clone a repository to the target directory."""
    repo_name = repo.name if hasattr(repo, 'name') else os.path.basename(str(target_dir))
    repo_owner = repo.owner.login if hasattr(repo, 'owner') else None
    repo_full_name = f"{repo_owner}/{repo_name}" if repo_owner else repo_name
    
    try:
        if os.path.exists(target_dir):
            logger.info(f"Repository already exists at {target_dir}, pulling latest changes")
            if use_gh_cli:
                process = subprocess.run(
                    ['gh', 'repo', 'sync', repo_full_name],
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
            
            if use_gh_cli:
                process = subprocess.run(
                    ['gh', 'repo', 'clone', repo_full_name, target_dir],
                    capture_output=True,
                    text=True
                )
            else:
                clone_url = repo.clone_url if hasattr(repo, 'clone_url') else f"https://github.com/{repo_full_name}.git"
                auth_url = clone_url.replace('https://', f'https://{github_token}@')
                
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