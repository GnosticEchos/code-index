"""
Data models for the code index tool.
"""


class CodeBlock:
    """Represents a code block extracted from a file."""

    def __init__(self, file_path: str, identifier: str, type: str, start_line: int,
                 end_line: int, content: str, file_hash: str, segment_hash: str):
        self.file_path = file_path
        self.identifier = identifier
        self.type = type
        self.start_line = start_line
        self.end_line = end_line
        self.content = content
        self.file_hash = file_hash
        self.segment_hash = segment_hash
