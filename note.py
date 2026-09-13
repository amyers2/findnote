from dataclasses import dataclass

@dataclass
class Note:
    file: str
    index: int
    line: int
    title: str
    content: str
