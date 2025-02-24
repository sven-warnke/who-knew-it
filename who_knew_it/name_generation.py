import pathlib
import random

NAME_FILES_DIR = pathlib.Path(__file__).parent / "name-generation"


def big_related_words() -> list[str]:
    with open(NAME_FILES_DIR / "big-related-words.txt") as f:
        return f.read().splitlines()


def wet_related_words() -> list[str]:
    with open(NAME_FILES_DIR / "wet-related-words.txt") as f:
        return f.read().splitlines()


def generate_player_name() -> str:
    big_word = random.choice(big_related_words())
    wet_word = random.choice(wet_related_words())
    return f"{big_word} {wet_word}"
