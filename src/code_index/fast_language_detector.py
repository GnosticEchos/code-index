"""
Enhanced ignore pattern system with fast language detection.
"""
import os
import glob
from pathlib import Path
from typing import List, Set, Dict, Optional
from whats_that_code.extension_based import guess_by_extension
from code_index.config import Config


class FastLanguageDetector:
    """Fast language detection using file extensions and content analysis."""
    
    def __init__(self, config: Config):
        """Initialize detector with configuration."""
        self.config = config
        self.sample_size = getattr(self.config, 'sample_size', 50)
        self.confidence_threshold = getattr(self.config, 'confidence_threshold', 0.5)
    
    def detect_languages(self, workspace_path: str) -> List[str]:
        """Detect programming languages in workspace."""
        languages = set()
        
        # Sample files from workspace
        sampled_files = self._sample_files(workspace_path, self.sample_size)
        
        # Detect languages for each file
        for file_path in sampled_files:
            try:
                # Get file extension
                _, ext = os.path.splitext(file_path)
                if ext:
                    # Use extension to guess language
                    file_langs = guess_by_extension(file_path)
                    languages.update(file_langs)
            except Exception:
                # Continue with next file on error
                continue
        
        return list(languages)
    
    def detect_frameworks(self, workspace_path: str) -> List[str]:
        """Detect frameworks based on project files."""
        frameworks = []
        
        # Framework detection based on indicator files
        framework_indicators = {
            'django': ['manage.py', 'requirements.txt'],
            'flask': ['requirements.txt'],
            'react': ['package.json'],
            'vue': ['package.json'],
            'node': ['package.json'],
            'rails': ['Gemfile', 'config.ru'],
            'spring': ['pom.xml', 'build.gradle'],
        }
        
        # Check for framework indicator files
        for framework, indicators in framework_indicators.items():
            if self._has_framework_indicators(workspace_path, indicators):
                frameworks.append(framework)
        
        return frameworks
    
    def _sample_files(self, workspace_path: str, max_files: int) -> List[str]:
        """Sample files from workspace for analysis."""
        files = []
        workspace_path = os.path.abspath(workspace_path)
        
        # Walk through directory and collect code-like files
        for root, dirs, filenames in os.walk(workspace_path):
            # Skip common ignored directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git']]
            
            for filename in filenames:
                # Skip hidden and obviously non-code files
                if filename.startswith('.') or '.' not in filename:
                    continue
                
                # Focus on files that look like source code
                ext = os.path.splitext(filename)[1]
                if ext in ['.py', '.js', '.ts', '.java', '.cpp', '.h', '.rs', '.go', '.rb', '.php']:
                    file_path = os.path.join(root, filename)
                    if os.path.isfile(file_path):
                        files.append(file_path)
                        
                        # Limit number of files
                        if len(files) >= max_files:
                            return files
        
        return files
    
    def _has_framework_indicators(self, workspace_path: str, indicators: List[str]) -> bool:
        """Check if workspace has framework indicator files."""
        for indicator in indicators:
            if isinstance(indicator, str):
                # Check for file existence
                if os.path.exists(os.path.join(workspace_path, indicator)):
                    return True
        return False
