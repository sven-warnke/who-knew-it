import random
from pathlib import Path


def get_random_word() -> str:
    word_file = Path(__file__).parent.parent / "who_knew_it" / "words.txt"

    with open(word_file) as f:
        words = f.read().splitlines()

    return random.choice(words)


def random_letter() -> str:
    letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
    return random.choice(letters)
