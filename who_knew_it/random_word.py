import random
from pathlib import Path


def get_random_word():
    word_file = Path(__file__).parent.parent / "who_knew_it" / "words.txt"

    with open(word_file) as f:
        words = f.read().splitlines()

    return random.choice(words)