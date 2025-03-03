import dataclasses
from pathlib import Path

import imdb  # type: ignore

from who_knew_it import api_call, questions, random_word

PROMPT_FOLDER_PATH = Path(__file__).parent / "prompts"


@dataclasses.dataclass
class MovieQuestion(questions.Question):
    title: str
    year: int
    correct_answer: str

    def question_text(self) -> str:
        return f'What is the plot of the {self.year} film "{self.title}"?'


class MovieQuestionGenerator(questions.QuestionGenerator):
    def __init__(self, avoid_examples: list[str] | None = None):
        self.avoid_examples = avoid_examples or []

    def generate_question_and_correct_answer(self) -> MovieQuestion:
        return select_film_and_generate_synopsis()
    
    def write_fake_answers(self, question: str, correct_answer: str, n_fake_answers: int) -> list[str]:
        if n_fake_answers < 0:
            raise ValueError("n_fake_answers must be >= 0")

        fake_answers = []
        avoid_examples = self.avoid_examples + [correct_answer]

        for _ in range(n_fake_answers):
            fake_answer_text = create_fake_movie_synopsis(
                info_about_film=question,
                avoid_examples=avoid_examples,
            )
            avoid_examples.append(fake_answer_text)
            fake_answers.append(fake_answer_text)

        return fake_answers


def _combine_synopsises(film_name, synopsis_list: list[str]) -> str:
    prompt = f"Please combine the following film synopsises found on imdb for the film {film_name} into one synopsis of length about 3-5 sentences. Don't output anything but the synopsis.\n\n"
    for synopsis in synopsis_list:
        prompt += synopsis
        prompt += "\n\n"

    return api_call.prompt_model(prompt=prompt)





def random_unknown_movie() -> imdb.Movie:
    ia = imdb.Cinemagoer()

    while True:
        word = random_word.get_random_word()
        print("random word: ", word)
        try:
            searched_movie_list = ia.search_movie(word, results=10)
        except imdb.IMDbError:
            continue

        for searched_movie in searched_movie_list:
            movie = ia.get_movie(searched_movie.movieID)
            if not movie.data.get("plot"):
                print("unsuitable: ", movie.data["title"], "no plot")

            elif not movie.data.get("votes", 0) < 100000:
                print("unsuitable: ", movie.data["title"], "too many votes")
                
            elif not movie.data["year"]:
                print("unsuitable: ", movie.data["title"], "no year")
                
            elif "episode" in movie.data["title"].lower():
                print("unsuitable: ", movie.data["title"], "episode")

            elif not movie.data.get("kind") == "movie":
                print("unsuitable: ", movie.data["title"], "not a movie")
                
            else:
                return movie


def _get_synopsises_from_suggestion(movie: imdb.Movie) -> tuple[list[str], str, int]:
    synopsis_list = movie.data["plot"]
    year = movie.data["year"]
    return synopsis_list, movie.data["title"], year


def select_film_and_generate_synopsis() -> MovieQuestion:
    print("Getting film suggestion")
    film_suggestion = random_unknown_movie()
    print("Film:", film_suggestion)
    synopsis_list, retrieved_title, year = _get_synopsises_from_suggestion(
        movie=film_suggestion
    )
    print(synopsis_list)
    
    combined_synopsis = _combine_synopsises(
        film_name=retrieved_title, synopsis_list=synopsis_list
    )
    print(retrieved_title)


    return MovieQuestion(title=retrieved_title, year=year, correct_answer=combined_synopsis)


def create_fake_movie_synopsis(info_about_film: str, avoid_examples: list[str]) -> str:
    if avoid_examples:
        avoid_list_string = (
            "Please make the synopsis completely different from the following examples. Don't reuse character names,"
            " and use a different genre of film:\n"
        )
        avoid_list_string += "\n\n".join(
            [" " * 4 + example for example in avoid_examples]
        )
        avoid_list_string += "\n\n"

    else:
        avoid_list_string = ""

    prompt = f"""
Please write a fake film synopsis for the following film: {info_about_film}.
The synopsis should roughly be 3-5 sentences long. Ideally a bit funny or bizarre but still
somewhat believable. The synopsis should be entirely made up, don't use any knowledge you
might have of the actual film. 
{avoid_list_string}
Please output only the synopsis and nothing else. 
"""
    return api_call.prompt_model(prompt=prompt)
