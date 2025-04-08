import random

import arxiv  # type: ignore

from who_knew_it import api_call, questions, random_word


class ArxivQuestion(questions.Question):
    def __init__(self, title: str, area: str):
        self.title = title
        self.area = area

    def question_text(self) -> str:

        area_readable = self.area.split(".")[0]

        if area_readable == "cs":
            area_readable = "Computer Science"

        elif area_readable == "astro-ph":
            area_readable = "Astrophysics"

        elif area_readable == "physics":
            area_readable = "Physics"

        elif area_readable == "cond-mat":
            area_readable = "Physics"
        
        elif area_readable == "quant-ph":
            area_readable = "Physics"
        
        elif area_readable == "hep":
            area_readable = "Physics"

        elif area_readable == "math":
            area_readable = "Mathematics"
        
        elif area_readable == "stat":
            area_readable = "Statistics"
        
        elif area_readable == "nlin":
            area_readable = "Physics"

        elif area_readable.startswith("hep-"):
            area_readable = "Physics"
        
        elif area_readable.startswith("nucl-"):
            area_readable = "Physics"

        elif area_readable == "econ":
            area_readable = "Economics"

        elif area_readable == "eess":
            area_readable = "Electrical Engineering"

        elif area_readable == "q-bio":
            area_readable = "Biology"
        
        elif area_readable == "q-fin":
            area_readable = "Finance"
        
        elif area_readable == "stat":
            area_readable = "Statistics"
        
        return f"What is a real scientific {area_readable} paper?"
    
    def get_correct_answer(self) -> str:
        return self.title
    

class ArxivQuestionGenerator(questions.QuestionGenerator):

    def generate_candidates(self) -> list[arxiv.Result]:
        client = arxiv.Client()
        while True:
            search_word = random_word.get_random_word()
            print("Search word: ", search_word)

            search = arxiv.Search(
                query = f"ti:{search_word}",
                max_results = 10,
                sort_by = arxiv.SortCriterion.SubmittedDate
            )
            results = list(client.results(search))
            if len(results) == 10:
                return results

    def generate_question_and_correct_answer(self) -> ArxivQuestion:
        while True:
            candidates = self.generate_candidates()

            candidates_str ="\n\n".join([f"{i}:{result.title}" for i, result in enumerate(candidates)])

            prompt = f"""
            From the list of the following scientific papers' titles, please choose one that sounds a little weird or funny to a native English speaker.
            Ideally, the paper is not too technical and avoids abbreviations.

            {candidates_str}

            Please answer only with its number as written above and nothing else.
            """

            print(prompt)
            result = api_call.prompt_model(prompt=prompt)

            try:
                result_number = int(result.strip())
                
            except ValueError:
                print("No fitting candidate found for response: ", result_number)
                print("Candidates: ", candidates)
                continue

            if 0 <= result_number < len(candidates):
                selected_candidate = candidates[result_number]
                return ArxivQuestion(title=selected_candidate.title, area=selected_candidate.primary_category)

        
    def write_fake_answers(self, question: str, correct_answer: str, n_fake_answers: int) -> list[str]:
        del correct_answer  # not needed here

        letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z"]
        while True:
            starting_letter_clause = f"The first paper should start with an '{random.choice(letters)}'."  # to add more randomness
            if n_fake_answers > 1:
                starting_letter_clause += f" The second paper should start with an '{random.choice(letters)}'."
            
            for i in range(2, n_fake_answers):
                starting_letter_clause += f" The {i + 1}. paper should start with an '{random.choice(letters)}'."

            prompt = f"""
            You are playing a game where you have to write convincing and fun fake answers, that could trick people into picking it. Please invent fitting scientific paper titles
            that fit the following question: "{question}".
            Please write {n_fake_answers} fake titles and nothing else in a list separated by newlines
            {starting_letter_clause}
            Please answer only with that list and nothing else.
            """
            print(prompt)
            response = api_call.prompt_model(prompt=prompt)

            split_response = response.split("\n")

            fake_answers = [r.replace("*", "").strip() for r in split_response if r.strip()]

            if len(fake_answers) == n_fake_answers:
                return fake_answers
