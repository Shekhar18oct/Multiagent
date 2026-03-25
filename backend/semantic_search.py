# Semantic code search for project code chunks
# This module provides a simple in-memory search over code chunks extracted during preprocessing.

from typing import List, Dict
import re

def search_code_chunks(chunks: List[Dict], query: str, max_results: int = 10) -> List[Dict]:
    """
    Search code chunks for query in name or code (case-insensitive).
    Returns top matches with metadata.
    """
    results = []
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    for chunk in chunks:
        if pattern.search(chunk.get('name', '')):
            results.append(chunk)
        # Optionally, search in code body if available
        # if 'code' in chunk and pattern.search(chunk['code']):
        #     results.append(chunk)
        if len(results) >= max_results:
            break
    return results
