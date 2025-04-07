import pathlib
import random

import pandas as pd

from who_knew_it import api_call, questions

ANIMALS_FOLDER = pathlib.Path(__file__).parent / "animals"


class AnimalQuestion(questions.Question):
    def __init__(self, species: str, group: str):
        self.species = species
        self.group = group

    def get_correct_answer(self) -> str:
        return self.species
    
    def question_text(self) -> str:
        return f"What's a real species of {self.group}?"


class AnimalQuestionGenerator(questions.QuestionGenerator):

    @staticmethod
    def _random_animal_group_and_species() -> tuple[str, list[str]]:
        group_file = random.choice([f for f in ANIMALS_FOLDER.iterdir() if f.suffix == ".csv"])

        every_nth = 5
        residual = random.randint(0, every_nth - 1)
        df = pd.read_csv(group_file, skiprows=lambda x: x % every_nth != residual, names=["species"])
        how_many = 50

        selected_animals = df.sample(how_many).reset_index(drop=True)
        return group_file.stem.replace("-", " "), selected_animals["species"].tolist()


    def generate_question_and_correct_answer(self):
        while True:
            group, candidates = self._random_animal_group_and_species()

            prompt = f"""
            From the list of the following animals, choose the one that sounds the funniest to a native English speaker, would be unknown
            to most people and doesn't contain any special characters of accents. 

            {", ".join(candidates)}

            Please answer only with the animal's name as written above and nothing else.
            """

            answer = api_call.prompt_model(prompt=prompt)

            fitting_answers = [a for a in candidates if a.lower().strip() == answer.lower().strip()]
            if len(fitting_answers) == 1:
                return AnimalQuestion(species=fitting_answers[0], group=group)
            
            print("No fitting candidate found for response: ", answer)
            print("Candidates: ", candidates)

    
    def write_fake_answers(self, question: str, correct_answer: str, n_fake_answers: int) -> list[str]:
        del correct_answer  # not needed here
        
        letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
        while True:
            starting_letter_clause = f"The first species should start with an '{random.choice(letters)}'."  # to add more randomness
            if n_fake_answers > 1:
                starting_letter_clause += f" The second species should start with an '{random.choice(letters)}'."
            
            for i in range(2, n_fake_answers):
                starting_letter_clause += f" The {i + 1}. species should start with an '{random.choice(letters)}'."

            prompt = f"""
            You are playing a game where you have to write convincing and fun fake answers, that could trick people into picking it. Please invent fitting fake animal names
            for the following question: "{question}"
            Please write convincing fake animal names that are of the required group of animals but which don't exist but are completely made up. 
            Please write {n_fake_answers} animal names and nothing else in a list separated by newlines. Don't start the names with 'The'.
            {starting_letter_clause}
            Please answer only with that list and nothing else.
            """
            print(prompt)
            response = api_call.prompt_model(prompt=prompt)

            split_response = response.split("\n")

            fake_answers = [r.replace("*", "").strip() for r in split_response if r.strip()]

            if len(fake_answers) == n_fake_answers:
                return fake_answers
        
