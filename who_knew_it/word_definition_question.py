import pathlib
import random

from who_knew_it import api_call, questions

WORDS_CSV = pathlib.Path(__file__).parent / "dictionary"/ "nouns.csv"


class OldEnglishWordDefinitionQuestion(questions.Question):
    def __init__(self, word: str, definition: str) -> None:
        self.word = word
        self.definition = definition

    def question_text(self) -> str:
        return f"What's the definition of the old english word '{self.word}'?"

    def get_correct_answer(self) -> str:
        return self.definition


class OldEnglishWordDefinitionQuestionGenerator(questions.QuestionGenerator):
    def generate_question_and_correct_answer(self) -> OldEnglishWordDefinitionQuestion:
        word, definition = _select_random_old_english_word()
        rewritten_definition = _make_definition_more_natural(word, definition)
        return OldEnglishWordDefinitionQuestion(word=word, definition=rewritten_definition)
    
    def write_fake_answers(self, question: str, correct_answer: str, n_fake_answers: int) -> list[str]:
        fake_answers: list[str] = []
        for _ in range(n_fake_answers):
            fake_answer = _create_fake_answers(question=question, definition=correct_answer, avoid_examples=fake_answers)
            fake_answers.append(fake_answer)
        return fake_answers


def _select_random_old_english_word() -> tuple[str, str]:
    with open(WORDS_CSV, "r") as f:
        lines = f.read().splitlines()
    
    how_many = 20
    while True:
        selected_lines = [(line.split("|")[0], line.split("|")[1]) for line in random.sample(lines, how_many)]

        select_best = _select_best_definition(selected_lines)
        if select_best:
            print("As in dictionary:", select_best)
            return select_best


def _select_best_definition(word_definitions: list[tuple[str, str]]) -> tuple[str, str] | None:
    
    definitions_str = ",\n".join([f"{word}: {definition}" for word, definition in word_definitions])
    
    prompt=f"""
    You are hosting a game where players have to write convincing and fun fake definitions of an obscureold english word.
    Then the players have to quess which one is correct. You need to select a suitable word for the game.
    I have provided a list of old english words and their definitions according to the oxford dictionary. 
    Please select the word for the game based on the following criteria:

    1. None of the players should be able to guess the correct answer
    2. The word is ideally a bit funny
    3. There is enough of a definition to make it interesting
    
    Here is the list of old english words and their definitions:
    {definitions_str}

    Please answer only with the chosen word and nothing else.
    """
    print(prompt)
    
    best = api_call.prompt_model(
        prompt
    )
    print("best: ", best)
    candidates = [line for line in word_definitions if line[0].lower() == best.strip().lower()]
    if len(candidates) != 1:
        return None
    return candidates[0]


def _make_definition_more_natural(word: str, definition: str) -> str:
    prompt = f"""
    You have to rewrite the following oxford dictionary definition, such that it is more natural, like a human would write it.
    The definition should be very short and simple. If the definition is already like or almost like how a human would write it,
    it is fine to just leave it as is or just make minimal changes.
    The word is: {word}
    The definition according to the oxford dictionary is: {definition}

    Please answer only with the rewritten definition and nothing else.
    """
    print(prompt)
    return api_call.prompt_model(prompt)


def _create_fake_answers(question: str, definition: str, avoid_examples: list[str]) -> str:
    
    avoid_examples_str = "\n\n".join(avoid_examples)
    
    avoid_clause = f"""
    Further, avoid anything that is similar in content to the following examples:
    {avoid_examples_str}
    """ if avoid_examples else ""

    prompt = f"""
    You are hosting a game where players have to write a convincing fake definition of an obscure, 
    old english word. It should be very short and simple.
    You have to write a confincing fake definition for the following question: {question}
    The definition is: {definition}
    Please make it similar in style to the definition but with completetly different content.

    {avoid_clause}
    
    Please answer only with the fake definition and nothing else.
    """
    print(prompt)
    return api_call.prompt_model(prompt)