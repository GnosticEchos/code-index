"""
Enhanced language detection for tree-sitter integration.

Provides robust language detection with fallback mechanisms and
support for common file extensions.
"""

from typing import Optional
from pathlib import Path
import mimetypes


class LanguageDetector:
    """Enhanced language detection with tree-sitter support."""
    
    # Comprehensive file extension to language mapping
    EXTENSION_MAP = {
        # Python
        '.py': 'python',
        '.pyx': 'python',
        '.pyi': 'python',
        
        # JavaScript/TypeScript
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.mjs': 'javascript',
        '.cjs': 'javascript',
        
        # Vue
        '.vue': 'vue',
        
        # Rust
        '.rs': 'rust',
        
        # Go
        '.go': 'go',
        
        # Java
        '.java': 'java',
        '.kt': 'kotlin',
        '.scala': 'scala',
        
        # C/C++
        '.c': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.hxx': 'cpp',
        
        # C#
        '.cs': 'csharp',
        
        # PHP
        '.php': 'php',
        '.php3': 'php',
        '.php4': 'php',
        '.php5': 'php',
        '.phtml': 'php',
        
        # Ruby
        '.rb': 'ruby',
        '.rake': 'ruby',
        '.gemspec': 'ruby',
        
        # Swift
        '.swift': 'swift',
        
        # Web
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        
        # Configuration/Data
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        
        # Shell
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'zsh',
        '.fish': 'fish',
        
        # Docker
        '.dockerfile': 'dockerfile',
        'Dockerfile': 'dockerfile',
    }
    
    # MIME type to language mapping
    MIME_MAP = {
        'text/x-python': 'python',
        'text/javascript': 'javascript',
        'application/javascript': 'javascript',
        'text/typescript': 'typescript',
        'text/x-rust': 'rust',
        'text/x-go': 'go',
        'text/x-java': 'java',
        'text/x-c': 'c',
        'text/x-c++': 'cpp',
        'text/x-csharp': 'csharp',
        'text/x-php': 'php',
        'text/x-ruby': 'ruby',
        'text/x-swift': 'swift',
        'text/html': 'html',
        'text/css': 'css',
        'application/json': 'json',
        'application/xml': 'xml',
        'text/yaml': 'yaml',
        'text/x-bash': 'bash',
    }
    
    def detect_language(self, file_path: str) -> str:
        """
        Detect programming language from file path with robust fallback.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language identifier string
        """
        path = Path(file_path)
        
        # 1. Extension-based detection (primary)
        language = self._detect_by_extension(file_path)

        # Try filename-based detection if extension failed
        if not language:
            language = self._detect_by_filename(file_path)
        if language != 'unknown':
            return language
            
        # 2. MIME type detection
        language = self._detect_by_mime_type(path)
        if language != 'unknown':
            return language
            
        # 4. Content-based detection (fallback)
        language = self._detect_by_content(path)
        
        return language
        
    def _detect_by_extension(self, path: Path) -> str:
        """Detect language by file extension."""
        extension = path.suffix.lower()
        return self.EXTENSION_MAP.get(extension, 'unknown')
        
    def _detect_by_filename(self, path: Path) -> str:
        """Detect language by filename."""
        filename = path.name.lower()
        
        # Special cases
        if filename == 'dockerfile':
            return 'dockerfile'
        elif filename.endswith('.dockerfile'):
            return 'dockerfile'
        elif filename.endswith('.sh'):
            return 'bash'
        elif filename.endswith('.zsh'):
            return 'zsh'
            
        return self.EXTENSION_MAP.get(filename, 'unknown')
        
    def _detect_by_mime_type(self, path: Path) -> str:
        """Detect language by MIME type."""
        try:
            mime_type, _ = mimetypes.guess_type(str(path))
            if mime_type:
                return self.MIME_MAP.get(mime_type, 'unknown')
        except Exception:
            pass
        return 'unknown'
        
    def _detect_by_content(self, path: Path) -> str:
        """Detect language by file content (basic heuristic)."""
        try:
            if not path.exists() or path.stat().st_size == 0:
                return 'unknown'
                
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024)  # Read first 1KB
                
            # Python indicators
            if any(indicator in content for indicator in ['#!/usr/bin/env python', 'def ', 'import ', 'class ']):
                return 'python'
                
            # JavaScript indicators
            if any(indicator in content for indicator in ['#!/usr/bin/env node', 'function ', 'const ', 'let ']):
                return 'javascript'
                
            # Rust indicators
            if any(indicator in content for indicator in ['fn ', 'use ', 'mod ', 'struct ']):
                return 'rust'
                
            # Go indicators
            if any(indicator in content for indicator in ['package ', 'func ', 'import ']):
                return 'go'
                
            # Vue indicators
            if '<template>' in content and '<script>' in content:
                return 'vue'
                
        except Exception:
            pass
            
        return 'unknown'
        
    def get_tree_sitter_language(self, language: str) -> Optional[str]:
        """Get tree-sitter language identifier."""
        tree_sitter_map = {
            'python': 'python',
            'javascript': 'javascript',
            'typescript': 'typescript',
            'vue': 'vue',
            'rust': 'rust',
            'go': 'go',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'csharp': 'c_sharp',
            'php': 'php',
            'ruby': 'ruby',
            'swift': 'swift',
            'kotlin': 'kotlin',
            'scala': 'scala',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'bash': 'bash',
            'dockerfile': 'dockerfile',
        }
        
        return tree_sitter_map.get(language)
        
    def is_supported_language(self, language: str) -> bool:
        """Check if language is supported by tree-sitter."""
        supported_languages = {
            'python', 'javascript', 'typescript', 'vue', 'rust', 'go', 'java',
            'c', 'cpp', 'csharp', 'php', 'ruby', 'swift', 'kotlin', 'scala',
            'html', 'css', 'json', 'xml', 'yaml', 'bash', 'dockerfile'
        }
        return language in supported_languages
