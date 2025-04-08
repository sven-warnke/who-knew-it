import pathlib
import random

import pandas as pd

from who_knew_it import api_call, questions

POKEMON_FOLDER = pathlib.Path(__file__).parent / "pokemon"


class PokemonQuestion(questions.Question):
    def __init__(self, name: str):
        self.name = name

    def get_correct_answer(self) -> str:
        return self.name
    
    def question_text(self) -> str:
        return f"What's a real name of a Pokémon?"


class PokemonQuestionGenerator(questions.QuestionGenerator):

    @staticmethod
    def random_pokemon() -> list[str]:
        file = POKEMON_FOLDER / "pokemon.csv"

        df = pd.read_csv(file, names=["name"])

        how_many = 10

        return df.sample(how_many).reset_index(drop=True)["name"].tolist()

    def generate_question_and_correct_answer(self):
        while True:
            candidates = self.random_pokemon()

            prompt = f"""
            From the list of the following pokemon, choose the one that sounds the funniest to a native English speaker. 

            {", ".join(candidates)}

            Please answer only with the exact pokemon name as written above and nothing else.
            """

            answer = api_call.prompt_model(prompt=prompt)

            fitting_answers = [a for a in candidates if a.lower().strip() == answer.lower().strip()]
            if len(fitting_answers) == 1:
                return PokemonQuestion(name=fitting_answers[0])
            
            print("No fitting candidate found for response: ", answer)
            print("Candidates: ", candidates)

    
    def write_fake_answers(self, question: str, correct_answer: str, n_fake_answers: int) -> list[str]:
        del correct_answer  # not needed here

        file = POKEMON_FOLDER / "pokemon.csv"

        df = pd.read_csv(file, names=["name"])
        
        letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
        while True:
            starting_letter_clause = f"The first pokemon should start with an '{random.choice(letters)}'."  # to add more randomness
            if n_fake_answers > 1:
                starting_letter_clause += f" The second pokemon should start with an '{random.choice(letters)}'."
            
            for i in range(2, n_fake_answers):
                starting_letter_clause += f" The {i + 1}. pokemon should start with an '{random.choice(letters)}'."

            prompt = f"""
            You are playing a game where you have to write convincing and fun fake answers, that could trick people into picking it. Please invent fitting fake Pokemon names.
            Please write {n_fake_answers} animal names and nothing else in a list separated by newlines. Don't start the names with 'The'.
            {starting_letter_clause}
            Please answer only with that list and nothing else.
            """
            print(prompt)
            response = api_call.prompt_model(prompt=prompt)

            split_response = response.split("\n")

            fake_answers = [r.replace("*", "").strip() for r in split_response if r.strip()]

            if real_pokemon:=[a for a in df["name"].tolist() if a in fake_answers]:
                print(f"Some of the fake answers are already in the dataset: {real_pokemon}. Try again.")
                continue

            if len(fake_answers) == n_fake_answers:
                return fake_answers
        

