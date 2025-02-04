import dataclasses


@dataclasses.dataclass
class Answer:
    text: str
    correct: bool
