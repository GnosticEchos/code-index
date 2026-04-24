import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from magika import Magika
    HAS_MAGIKA = True
except ImportError:
    HAS_MAGIKA = False

logger = logging.getLogger(__name__)

class MagikaDetector:
    """
    Intelligent file identification using Google's Magika Deep Learning model.
    Packaged and optimized for standalone Nuitka binaries.
    """
    
    def __init__(self):
        self.magika: Optional[Magika] = None
        if HAS_MAGIKA:
            try:
                self.magika = Magika()
                logger.info("Magika Deep Learning detector initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Magika: {e}. Falling back to extension matching.")
        else:
            logger.info("Magika package not found. Using extension matching fallback.")

        # Mapping of Magika labels to our internal language keys
        # This is where we ensure first-class citizen parity
        self.label_map = {
            "python": "python",
            "rust": "rust",
            "go": "go",
            "javascript": "javascript",
            "typescript": "typescript",
            "vue": "vue",
            "haskell": "haskell",
            "java": "java",
            "kotlin": "kotlin",
            "c": "c",
            "cpp": "cpp",
            "csharp": "csharp",
            "ruby": "ruby",
            "bash": "bash",
            "shell": "bash",
            "markdown": "markdown",
            "json": "json",
            "sql": "sql",
            "yaml": "yaml",
            "toml": "toml",
            "html": "html",
            "css": "css",
            "scss": "scss",
            "zig": "zig",
            "swift": "swift",
            "php": "php",
            "scala": "scala",
            "dart": "dart",
            "lua": "lua",
            "ocaml": "ocaml",
            "nim": "nim",
            "clojure": "clojure",
            "cmake": "cmake",
            "elixir": "elixir",
            "erlang": "erlang",
            "prisma": "prisma",
        }

    def identify_file(self, file_path: str) -> Dict[str, Any]:
        """
        Identify file type using AI with confidence scoring.
        
        Returns:
            Dictionary with 'label', 'score', and 'method'.
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return {"label": "unknown", "score": 0.0, "method": "none"}

        if self.magika:
            try:
                res = self.magika.identify_path(path)
                label = res.output.label
                score = res.score
                
                # Trust Magika if confidence is high and it's not a generic text label
                if label not in ["unknown", "txt"] and score > 0.5:
                    internal_label = self.label_map.get(label, label)
                    return {
                        "label": internal_label,
                        "score": float(score),
                        "method": "magika",
                        "mime": res.output.mime_type
                    }
            except Exception as e:
                logger.debug(f"Magika identification failed for {file_path}: {e}")

        return {"label": "unknown", "score": 0.0, "method": "fallback"}
