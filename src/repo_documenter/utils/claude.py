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
            system="""You are a technical documentation expert. Your task is to analyze repository files and create comprehensive documentation. Follow these guidelines:

1. Be specific and detailed in your explanations
2. Use real code examples from the repository
3. Create proper Mermaid diagrams that accurately represent the system
4. Focus on practical, actionable information
5. Include security and performance best practices
6. Write in a clear, professional style
7. Structure documentation with proper headings and sections
8. Include code snippets and configuration examples
9. Add troubleshooting guides and common issues
10. Ensure all documentation is accurate based on the code

Format your response as a complete Markdown document with all sections properly formatted.""",
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
    # Get project structure information
    project_structure = repo_analysis.get("project_structure", {})
    main_readme = repo_analysis.get("main_readme", {}).get("content", "No README found")
    source_files = repo_analysis.get("source_files", [])
    config_files = repo_analysis.get("config_files", [])
    
    # Create the prompt
    prompt = f"""
# Repository Documentation Task: {repo_name}

## Project Overview

Repository Name: {repo_name}
Main Technology: {project_structure.get("main_tech", "unknown")}
Total Files: {project_structure.get("total_files", 0)}
Source Files: {project_structure.get("source_files", 0)}
Configuration Files: {project_structure.get("config_files", 0)}
Has Docker: {"Yes" if project_structure.get("has_docker") else "No"}
Has Tests: {"Yes" if project_structure.get("has_tests") else "No"}
Has Existing Docs: {"Yes" if project_structure.get("has_docs") else "No"}

## Current README Content

{main_readme}

## Repository Structure

### Source Files:
{chr(10).join(f"- {file['path']}" for file in source_files)}

### Config Files:
{chr(10).join(f"- {file['path']}" for file in config_files)}

## Key Source Files Content

"""

    # Add important source files
    for file in source_files:
        if any(pattern in file["path"].lower() for pattern in [
            "main", "index", "app", "server", "config", "model", "type", "interface", "service"
        ]):
            prompt += f"\n### {file['path']}\n```\n"
            prompt += file["content"][:3000] + ("..." if len(file["content"]) > 3000 else "")
            prompt += "\n```\n"
    
    # Add configuration files
    prompt += "\n## Configuration Files\n"
    for file in config_files:
        prompt += f"\n### {file['path']}\n```\n"
        prompt += file["content"][:1500] + ("..." if len(file["content"]) > 1500 else "")
        prompt += "\n```\n"
    
    prompt += """
## Required Documentation Sections

Please create comprehensive documentation with the following sections. Each section should be detailed and include real examples from the code:

1. ## Getting Started Guide

Create a practical guide that includes:
- Prerequisites and system requirements (based on package.json, requirements.txt, etc.)
- Step-by-step installation instructions
- Configuration setup with real examples
- Environment variables setup
- Basic usage examples using real code from the repository
- Development setup instructions
- Common issues and solutions

2. ## Data Models Documentation

Document all data structures including:
- Database schemas and models
- TypeScript/JavaScript interfaces and types
- API request/response models
- Data validation rules
- Example data structures
- Entity relationships (with Mermaid ER diagrams)
- Data flow between components

3. ## Flow Charts

Create detailed diagrams using Mermaid syntax for:
- Application workflow
- Request/response flow
- Data processing pipelines
- State management
- Component interactions
- Authentication/authorization flow
- Error handling flow

Example Mermaid diagram:
```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Database
    Client->>API: Request
    API->>Database: Query
    Database-->>API: Response
    API-->>Client: Result
```

4. ## Architecture Overview

Provide a comprehensive overview including:
- System architecture (with Mermaid diagram)
- Component breakdown
- Design patterns used
- Security measures
- Performance optimizations
- Integration points
- Deployment architecture
- Scalability considerations
- Error handling strategy

5. ## FAQs

Create a practical FAQ section covering:
- Common development questions
- Troubleshooting guide
- Best practices
- Performance tips
- Security guidelines
- Known issues and workarounds
- Deployment considerations
- Maintenance procedures

Format your response as a complete Markdown document. Use proper headings, code blocks, and Mermaid diagrams. Focus on practical, actionable information that will help developers understand and work with the codebase.

## Important Notes

1. Use actual code examples from the repository
2. Create accurate Mermaid diagrams based on the code structure
3. Include security and performance considerations
4. Add troubleshooting guides for common issues
5. Make the documentation practical and actionable
6. Structure the content with clear headings
7. Include configuration examples
8. Add code snippets for common tasks
9. Reference actual file paths and components
10. Explain architectural decisions and trade-offs

Begin your response with the Getting Started Guide section.
"""
    
    return prompt 