import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class UniversalSchemaService:
    """
    Service for managing the Relationship-Native Query Schema.
    Decouples structural logic from the application binary.
    """

    def __init__(self, queries_dir: Optional[Path] = None):
        if queries_dir is None:
            # Default to the internal queries directory within the package
            package_dir = Path(__file__).parent.parent.parent / "queries"
            if not package_dir.exists():
                # Fallback for development/testing environments
                workspace_dir = Path.cwd() / "src" / "code_index" / "queries"
                if workspace_dir.exists():
                    package_dir = workspace_dir
                else:
                    # Absolute fallback for when running from repo root
                    repo_dir = Path.cwd() / "queries"
                    if repo_dir.exists():
                        package_dir = repo_dir
            
            queries_dir = package_dir
        
        self.queries_dir = queries_dir
        self.minimal_queries_path = self.queries_dir / "queries_minimal.jsonl"
        
        # Internal Cache: { language: { category: [queries] } }
        self._query_cache: Dict[str, Dict[str, List[str]]] = {}
        # Symbol Capture Mapping: { language: { query_str: target_capture } }
        self._target_capture_cache: Dict[str, Dict[str, str]] = {}
        self._initialized = False

    def load_schema(self) -> bool:
        """Load the 908-record query forge into memory."""
        if self._initialized:
            return True

        if not self.minimal_queries_path.exists():
            logger.warning(f"Universal Schema file not found: {self.minimal_queries_path}. Performance may be degraded.")
            return False

        try:
            count = 0
            with open(self.minimal_queries_path, "r") as f:
                for line in f:
                    if not line.strip(): continue
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
                        
                        if lang not in self._target_capture_cache:
                            self._target_capture_cache[lang] = {}
                        self._target_capture_cache[lang][query] = target
                        count += 1

            self._initialized = True
            logger.info(f"Universal Schema Service initialized with {count} high-precision relationship queries.")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Universal Schema Service: {e}")
            return False

    def get_queries_for_language(self, language: str) -> Dict[str, List[str]]:
        """Get relationship-categorized queries for a specific language."""
        if not self._initialized:
            self.load_schema()
        return self._query_cache.get(language, {})

    def get_all_queries_combined(self, language: str) -> Optional[str]:
        """
        Backward compatibility helper: merges all relationship queries into 
        a single S-expression block.
        """
        lang_queries = self.get_queries_for_language(language)
        if not lang_queries:
            return None
        
        combined = []
        for cat_queries in lang_queries.values():
            combined.extend(cat_queries)
        
        return "\n".join(combined)

    def get_target_capture(self, language: str, query_str: str) -> Optional[str]:
        """Retrieve the exact symbol capture name for a given query."""
        return self._target_capture_cache.get(language, {}).get(query_str)
