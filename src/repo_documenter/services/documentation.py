"""Documentation generation and saving service."""
import os
import re
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
    
    # Initialize lists for different file types
    important_files = []
    readme_files = []
    config_files = []
    source_files = []
    
    # Define patterns for different file types
    source_patterns = [".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".cs"]
    config_patterns = [".json", ".yaml", ".yml", ".env", ".config", ".toml"]
    readme_patterns = ["README.md", "README", "readme.md"]
    
    # Walk through the repository
    for root, _, files in os.walk(repo_path):
        # Skip hidden directories
        if any(part.startswith('.') for part in Path(root).parts):
            continue
            
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            
            # Skip binary files and large files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, IOError):
                continue
                
            # Categorize files
            if any(rel_path.endswith(ext) for ext in source_patterns):
                source_files.append({
                    "path": rel_path,
                    "content": content
                })
            elif any(rel_path.endswith(ext) for ext in config_patterns):
                config_files.append({
                    "path": rel_path,
                    "content": content
                })
            elif file in readme_patterns:
                readme_files.append({
                    "path": rel_path,
                    "content": content
                })
    
    # Find main README (prefer README.md in root)
    main_readme = None
    for readme in readme_files:
        if readme["path"] == "README.md":
            main_readme = readme
            break
    if not main_readme and readme_files:
        main_readme = readme_files[0]
    
    # Analyze project structure
    project_structure = {
        "total_files": len(source_files) + len(config_files) + len(readme_files),
        "source_files": len(source_files),
        "config_files": len(config_files),
        "readme_files": len(readme_files),
        "has_docker": any(f["path"].endswith("Dockerfile") for f in config_files),
        "has_tests": any("test" in f["path"].lower() for f in source_files),
        "has_docs": any("docs" in f["path"].lower() for f in readme_files),
        "main_tech": detect_main_technology(source_files)
    }
    
    return {
        "files": source_files + config_files + readme_files,
        "source_files": source_files,
        "config_files": config_files,
        "readme_files": readme_files,
        "main_readme": main_readme or {"content": "No README found"},
        "project_structure": project_structure
    }

def detect_main_technology(source_files):
    """Detect the main technology used in the project."""
    tech_counts = {}
    
    for file in source_files:
        ext = os.path.splitext(file["path"])[1]
        if ext in [".py"]:
            tech_counts["Python"] = tech_counts.get("Python", 0) + 1
        elif ext in [".js", ".jsx"]:
            tech_counts["JavaScript"] = tech_counts.get("JavaScript", 0) + 1
        elif ext in [".ts", ".tsx"]:
            tech_counts["TypeScript"] = tech_counts.get("TypeScript", 0) + 1
        elif ext in [".java"]:
            tech_counts["Java"] = tech_counts.get("Java", 0) + 1
        elif ext in [".go"]:
            tech_counts["Go"] = tech_counts.get("Go", 0) + 1
        elif ext in [".rb"]:
            tech_counts["Ruby"] = tech_counts.get("Ruby", 0) + 1
        elif ext in [".php"]:
            tech_counts["PHP"] = tech_counts.get("PHP", 0) + 1
        elif ext in [".cs"]:
            tech_counts["C#"] = tech_counts.get("C#", 0) + 1
    
    if not tech_counts:
        return "Unknown"
    
    return max(tech_counts.items(), key=lambda x: x[1])[0]

def save_documentation(docs_dir, documentation):
    """Save generated documentation to the appropriate files in the docs directory."""
    try:
        # Define section markers
        sections = {
            "getting-started": {
                "title": "Getting Started Guide",
                "pattern": r"#+\s*Getting Started Guide\s*\n(.*?)(?=#+\s*(?:Data Models Documentation|Flow Charts|Architecture Overview|FAQs)\s*\n|$)",
                "required_elements": ["Prerequisites", "Installation", "Configuration", "Usage"]
            },
            "data-models": {
                "title": "Data Models Documentation",
                "pattern": r"#+\s*Data Models Documentation\s*\n(.*?)(?=#+\s*(?:Flow Charts|Architecture Overview|FAQs)\s*\n|$)",
                "required_elements": ["Models", "Schema", "Validation"]
            },
            "flows": {
                "title": "Flow Charts",
                "pattern": r"#+\s*Flow Charts\s*\n(.*?)(?=#+\s*(?:Architecture Overview|FAQs)\s*\n|$)",
                "required_elements": ["```mermaid"]
            },
            "architecture": {
                "title": "Architecture Overview",
                "pattern": r"#+\s*Architecture Overview\s*\n(.*?)(?=#+\s*(?:FAQs)\s*\n|$)",
                "required_elements": ["Components", "Design", "Integration"]
            },
            "faqs": {
                "title": "FAQs",
                "pattern": r"#+\s*FAQs\s*\n(.*?)(?=#+|$)",
                "required_elements": ["Question", "Answer"]
            }
        }
        
        # Create main README.md with links to all sections
        main_readme = "# Documentation\n\n"
        for section, info in sections.items():
            main_readme += f"- [{info['title']}]({section}/README.md)\n"
        
        with open(os.path.join(docs_dir, "README.md"), 'w', encoding='utf-8') as f:
            f.write(main_readme)
        
        # Extract and save each section
        for section, info in sections.items():
            section_dir = os.path.join(docs_dir, section)
            
            # Extract section content using regex pattern
            match = re.search(info["pattern"], documentation, re.DOTALL | re.MULTILINE)
            if match and any(element.lower() in match.group(1).lower() for element in info["required_elements"]):
                section_content = match.group(1).strip()
                
                # Add title if not present
                if not section_content.startswith("# "):
                    section_content = f"# {info['title']}\n\n{section_content}"
                
                with open(os.path.join(section_dir, "README.md"), 'w', encoding='utf-8') as f:
                    f.write(section_content)
            else:
                # Create a placeholder with more information about what's missing
                with open(os.path.join(section_dir, "README.md"), 'w', encoding='utf-8') as f:
                    f.write(f"""# {info['title']}

This section requires manual documentation. The following elements are expected:

{chr(10).join(f"- {element}" for element in info["required_elements"])}

Please add appropriate documentation covering these elements.

For reference, this section should include:
1. Detailed explanations with code examples
2. Diagrams where applicable
3. Best practices and guidelines
4. Common issues and solutions
""")
        
        logger.info(f"Documentation saved to {docs_dir}")
        return True
    except Exception as e:
        logger.error(f"Error saving documentation: {e}")
        return False 