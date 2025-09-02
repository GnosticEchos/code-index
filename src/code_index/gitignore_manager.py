"""
Gitignore template manager with GitHub template integration.
"""
import os
import requests
from typing import List, Optional, Dict
from pathlib import Path
from code_index.config import Config


class GitignoreTemplateManager:
    """Manage gitignore templates from GitHub repository."""
    
    def __init__(self, cache_dir: str = "~/.cache/code_index/gitignore", config: Optional[Config] = None):
        """Initialize template manager."""
        self.cache_dir = os.path.expanduser(cache_dir)
        self.config = config or Config()
        self.templates_url = "https://raw.githubusercontent.com/github/gitignore/main"
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Enable/disable ML detection (disabled by default)
        self.ml_enabled = getattr(self.config, 'ml_enabled', False)
        self.ml_model_path = getattr(self.config, 'ml_model_path', None)
    
    def get_language_template(self, language: str) -> List[str]:
        """Get gitignore template for a specific language."""
        # Normalize language name
        language = language.capitalize()
        
        # Check cache first
        cached_template = self._get_cached_template(language)
        if cached_template:
            return cached_template
        
        # Try to download from GitHub
        template_content = self._download_template(language)
        if template_content:
            # Cache the template
            self._cache_template(language, template_content)
            return self._parse_gitignore_content(template_content)
        
        # Return empty list if no template found
        return []
    
    def get_framework_template(self, framework: str) -> List[str]:
        """Get gitignore template for a specific framework."""
        # Many frameworks use language templates
        framework_mapping = {
            'django': 'Python',
            'flask': 'Python', 
            'react': 'Node',
            'vue': 'Node',
            'node': 'Node',
            'rails': 'Ruby',
            'spring': 'Java'
        }
        
        # Get mapped language template
        language = framework_mapping.get(framework.lower())
        if language:
            return self.get_language_template(language)
        
        # Try direct framework template
        return self.get_language_template(framework)
    
    def get_global_template(self, category: str) -> List[str]:
        """Get global templates (OS, editors, etc.)."""
        global_mapping = {
            'linux': 'Global/Linux',
            'macos': 'Global/macOS', 
            'windows': 'Global/Windows',
            'vscode': 'Global/VisualStudioCode',
            'intellij': 'Global/IntelliJ',
            'vim': 'Global/Vim',
            'emacs': 'Global/Emacs'
        }
        
        template_path = global_mapping.get(category.lower())
        if template_path:
            # Check cache first
            cached_template = self._get_cached_template(template_path.replace('/', '-'))
            if cached_template:
                return cached_template
            
            # Download from GitHub
            template_content = self._download_template(template_path)
            if template_content:
                self._cache_template(template_path.replace('/', '-'), template_content)
                return self._parse_gitignore_content(template_content)
        
        return []
    
    def _get_cached_template(self, template_name: str) -> Optional[List[str]]:
        """Get template from cache if it exists."""
        cache_file = os.path.join(self.cache_dir, f"{template_name}.gitignore")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                return self._parse_gitignore_content(content)
            except:
                pass
        return None
    
    def _cache_template(self, template_name: str, content: str) -> None:
        """Cache template content."""
        cache_file = os.path.join(self.cache_dir, f"{template_name}.gitignore")
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
        except:
            pass  # Silently fail on cache write errors
    
    def _download_template(self, template_path: str) -> Optional[str]:
        """Download template from GitHub."""
        try:
            # Try direct template first
            url = f"{self.templates_url}/{template_path}.gitignore"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
            
            # Try with spaces replaced by underscores
            template_path_alt = template_path.replace(' ', '_')
            url = f"{self.templates_url}/{template_path_alt}.gitignore"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
                
        except requests.RequestException:
            pass
        
        return None
    
    def _parse_gitignore_content(self, content: str) -> List[str]:
        """Parse gitignore content into pattern list."""
        patterns = []
        for line in content.splitlines():
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                patterns.append(line)
        return patterns
