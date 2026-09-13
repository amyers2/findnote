from dataclasses import dataclass

@dataclass
class Note:
    collection: str
    file: str
    index: int
    line: int
    title: str
    content: str
