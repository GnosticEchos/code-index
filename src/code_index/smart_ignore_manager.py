"""
Smart ignore pattern manager combining multiple sources.
"""
import os
import fnmatch
from typing import List, Set, Dict, Optional
from pathlib import Path

from code_index.config import Config
from code_index.fast_language_detector import FastLanguageDetector
from code_index.gitignore_manager import GitignoreTemplateManager


class SmartIgnoreManager:
    """Smart ignore pattern manager with multi-source integration."""
    
    def __init__(self, workspace_path: str, config: Config):
        """Initialize smart ignore manager."""
        self.workspace_path = os.path.abspath(workspace_path)
        self.config = config
        self.ignore_patterns: Optional[List[str]] = None
        
        # Initialize components
        self.language_detector = FastLanguageDetector(self.config)
        self.gitignore_manager = GitignoreTemplateManager(config=self.config)
        
        # Configuration options
        self.apply_github_templates = getattr(self.config, 'auto_ignore_detection', True)
        self.apply_project_gitignore = getattr(self.config, 'apply_project_gitignore', True)
        self.apply_global_ignores = getattr(self.config, 'apply_global_ignores', True)
        self.learn_from_indexing = getattr(self.config, 'learn_from_indexing', False)
    
    def get_all_ignore_patterns(self) -> List[str]:
        """Get all ignore patterns from all sources."""
        if self.ignore_patterns is not None:
            return self.ignore_patterns

        patterns = set()
        
        # 1. GitHub community templates (language-specific)
        if self.apply_github_templates:
            print("DEBUG: Loading community patterns")
            community_patterns = self._get_community_patterns()
            print(f"DEBUG: Loaded {len(community_patterns)} community patterns")
            patterns.update(community_patterns)
        
        # 2. Project .gitignore files
        if self.apply_project_gitignore:
            print("DEBUG: Loading project patterns")
            project_patterns = self._get_project_patterns()
            print(f"DEBUG: Loaded {len(project_patterns)} project patterns")
            patterns.update(project_patterns)
        
        # 3. Global user preferences
        if self.apply_global_ignores:
            print("DEBUG: Loading global patterns")
            global_patterns = self._get_global_patterns()
            print(f"DEBUG: Loaded {len(global_patterns)} global patterns")
            patterns.update(global_patterns)
        
        # 4. Adaptive learning patterns (future enhancement)
        if self.learn_from_indexing:
            adaptive_patterns = self._get_adaptive_patterns()
            patterns.update(adaptive_patterns)
        
        self.ignore_patterns = list(patterns)
        print(f"DEBUG: All ignore patterns: {self.ignore_patterns}")
        return self.ignore_patterns
    
    def should_ignore_file(self, file_path: str) -> bool:
        """Check if a file should be ignored based on all patterns."""
        # Convert to relative path
        rel_file_path = os.path.relpath(file_path, self.workspace_path)
        
        # Get all ignore patterns
        ignore_patterns = self.get_all_ignore_patterns()
        
        # Check each pattern
        for pattern in ignore_patterns:
            if self._matches_pattern(rel_file_path, pattern):
                print(f"DEBUG: Ignoring '{rel_file_path}' because it matches pattern '{pattern}'")
                return True
        
        return False
    
    def _get_community_patterns(self) -> List[str]:
        """Get ignore patterns from GitHub community templates."""
        patterns = []
        
        # Detect languages in workspace
        languages = self.language_detector.detect_languages(self.workspace_path)
        
        # Get templates for each language
        for language in languages:
            lang_patterns = self.gitignore_manager.get_language_template(language)
            patterns.extend(lang_patterns)
        
        # Detect frameworks
        frameworks = self.language_detector.detect_frameworks(self.workspace_path)
        
        # Get templates for each framework
        for framework in frameworks:
            fw_patterns = self.gitignore_manager.get_framework_template(framework)
            patterns.extend(fw_patterns)
        
        return patterns
    
    def _get_project_patterns(self) -> List[str]:
        """Get patterns from project .gitignore files."""
        patterns = []
        
        # Check if we should only read root .gitignore
        if getattr(self.config, 'read_root_gitignore_only', True):
            # Only read root .gitignore file
            root_gitignore = os.path.join(self.workspace_path, '.gitignore')
            if os.path.exists(root_gitignore):
                print(f"DEBUG: Reading project gitignore: {root_gitignore}")
                try:
                    with open(root_gitignore, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                patterns.append(line)
                except:
                    pass
        else:
            # Original behavior: recursively walk through workspace
            for root, dirs, files in os.walk(self.workspace_path):
                if '.gitignore' in files:
                    gitignore_path = os.path.join(root, '.gitignore')
                    print(f"DEBUG: Reading project gitignore: {gitignore_path}")
                    try:
                        with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    patterns.append(line)
                    except:
                        continue
        
        return patterns
    
    def _get_global_patterns(self) -> List[str]:
        """Get global ignore patterns."""
        patterns = []
        
        # Detect OS and add appropriate global patterns
        import platform
        os_name = platform.system().lower()
        
        if 'linux' in os_name:
            patterns.extend(self.gitignore_manager.get_global_template('linux'))
        elif 'darwin' in os_name:
            patterns.extend(self.gitignore_manager.get_global_template('macos'))
        elif 'windows' in os_name:
            patterns.extend(self.gitignore_manager.get_global_template('windows'))
        
        # Add common editor patterns
        patterns.extend(self.gitignore_manager.get_global_template('vscode'))
        patterns.extend(self.gitignore_manager.get_global_template('intellij'))
        
        return patterns
    
    def _get_adaptive_patterns(self) -> List[str]:
        """Get patterns learned from previous indexing (future enhancement)."""
        # Placeholder for adaptive learning
        return []
    
    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if file path matches ignore pattern."""
        import fnmatch
        
        # Handle directory patterns ending with /
        if pattern.endswith('/'):
            dir_pattern = pattern[:-1]  # Remove trailing slash
            
            # Check if any parent directory matches the pattern
            path_parts = file_path.split(os.sep)
            for i in range(len(path_parts)):
                # Reconstruct directory path up to this level
                dir_path = os.sep.join(path_parts[:i+1])
                if fnmatch.fnmatch(dir_path, dir_pattern):
                    return True
                if fnmatch.fnmatch(path_parts[i], dir_pattern):
                    return True
                    
            return False

        # Handle wildcard patterns
        if '*' in pattern or '?' in pattern:
            try:
                return fnmatch.fnmatch(file_path, pattern)
            except:
                pass
        
        # Handle exact matches
        if file_path == pattern:
            return True
        
        # Handle extensions
        if pattern.startswith('*.'):
            _, ext = os.path.splitext(file_path)
            if ext == pattern[1:]:
                return True
        
        return False