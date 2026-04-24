import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class UniversalSchemaLoader:
    """
    Loads and manages the Universal Relationship Schema from JSONL/JSON files.
    """

    def __init__(self, queries_dir: Optional[Path] = None):
        """
        Initialize the schema loader.
        
        Args:
            queries_dir: Directory containing the query schema files.
        """
        if queries_dir is None:
            # Default to the internal queries directory
            queries_dir = Path(__file__).parent.parent.parent / "queries"
        
        self.queries_dir = queries_dir
        self.minimal_queries_path = self.queries_dir / "queries_minimal.jsonl"
        self.schema_path = self.queries_dir / "queries_metadata.schema.json"
        
        # Cache for loaded queries: { language: { category: [queries] } }
        self._query_cache: Dict[str, Dict[str, List[str]]] = {}
        self._target_capture_cache: Dict[str, Dict[str, str]] = {}

    def load_schema(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Load the minimal relationship schema from JSONL.
        
        Returns:
            Dictionary mapping language -> { category: [query_strings] }
        """
        if self._query_cache:
            return self._query_cache

        if not self.minimal_queries_path.exists():
            logger.warning(f"Universal Schema file not found: {self.minimal_queries_path}")
            return {}

        try:
            with open(self.minimal_queries_path, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    lang = record.get("language")
                    cat = record.get("capture")
                    query = record.get("query")
                    target = record.get("target_capture")
                    
                    if lang and cat and query:
                        if lang not in self._query_cache:
                            self._query_cache[lang] = {}
                        if cat not in self._query_cache[lang]:
                            self._query_cache[lang][cat] = []
                        
                        self._query_cache[lang][cat].append(query)
                        
                        # Store target capture mapping for symbol extraction
                        if lang not in self._target_capture_cache:
                            self._target_capture_cache[lang] = {}
                        self._target_capture_cache[lang][query] = target

            logger.info(f"Loaded {sum(len(v) for l in self._query_cache.values() for v in l.values())} relationship queries across {len(self._query_cache)} languages.")
            return self._query_cache
            
        except Exception as e:
            logger.error(f"Failed to load Universal Schema: {e}")
            return {}

    def get_queries_for_language(self, language: str) -> Dict[str, List[str]]:
        """Get categorized queries for a specific language."""
        if not self._query_cache:
            self.load_schema()
        return self._query_cache.get(language, {})

    def get_target_capture(self, language: str, query_str: str) -> Optional[str]:
        """Get the specific target capture name for symbol extraction."""
        return self._target_capture_cache.get(language, {}).get(query_str)
