"""Claude AI integration for documentation generation."""
import logging
import anthropic

logger = logging.getLogger("RepoDocumenter")

def generate_documentation(repo_name, repo_analysis, anthropic_client):
    """Generate documentation using Anthropic Claude."""
    logger.info(f"Generating documentation with Claude for {repo_name}")
    
    # Create prompt for Claude
    prompt = create_documentation_prompt(repo_name, repo_analysis)
    
    try:
        # Call Anthropic API with the latest model
        response = anthropic_client.messages.create(
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

def create_documentation_prompt(repo_name, repo_analysis):
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