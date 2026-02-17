"""
Emergency tree-sitter language detection fix.

Quick patch to restore language detection functionality.
"""

from pathlib import Path
from typing import Optional

# Emergency language mapping
LANGUAGE_MAP = {
    '.py': 'python',
    '.rs': 'rust',
    '.ts': 'typescript',
    '.js': 'javascript',
    '.vue': 'vue',
    '.go': 'go',
    '.java': 'java',
    '.cpp': 'cpp',
    '.c': 'c',
    '.cs': 'csharp',
    '.php': 'php',
    '.rb': 'ruby',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.html': 'html',
    '.css': 'css',
    '.json': 'json',
    '.xml': 'xml',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.md': 'markdown',
    '.dockerfile': 'dockerfile',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'zsh',
    '.fish': 'fish',
    '.ps1': 'powershell',
}

def detect_language_emergency(file_path: str) -> str:
    """Emergency language detection."""
    path = Path(file_path)
    extension = path.suffix.lower()
    
    # Handle special cases
    if path.name.lower() == 'dockerfile':
        return 'dockerfile'
    elif path.name.lower().endswith('.dockerfile'):
        return 'dockerfile'
    
    return LANGUAGE_MAP.get(extension, 'unknown')

def get_tree_sitter_language_emergency(language: str) -> Optional[str]:
    """Get tree-sitter language for emergency detection."""
    ts_map = {
        'python': 'python',
        'rust': 'rust',
        'typescript': 'typescript',
        'javascript': 'javascript',
        'vue': 'vue',
        'go': 'go',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c',
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
    return ts_map.get(language)
