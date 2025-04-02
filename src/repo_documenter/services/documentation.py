"""Documentation generation and saving service."""
import os
import logging
from pathlib import Path

logger = logging.getLogger("RepoDocumenter")

def create_documentation_structure(repo_path):
    """Create the documentation directory structure."""
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
    
    return docs_dir

def analyze_repository(repo_path):
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

def save_documentation(docs_dir, documentation):
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
            section_content = extract_section(documentation, heading)
            
            if section_content:
                with open(os.path.join(section_dir, "README.md"), 'w', encoding='utf-8') as f:
                    f.write(section_content)
        
        logger.info(f"Documentation saved to {docs_dir}")
        return True
    except Exception as e:
        logger.error(f"Error saving documentation: {e}")
        return False

def extract_section(documentation, heading):
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