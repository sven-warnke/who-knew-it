from who_knew_it import api_call
import imdb
from pathlib import Path

PROMPT_FOLDER_PATH = Path(__file__).parent / "prompts"


def get_film_suggestion() -> str:

    prompt_file = "film_suggestion.txt"
    prompt_file_path =  PROMPT_FOLDER_PATH / prompt_file

    with open(prompt_file_path) as f:
        prompt = f.read()

    return api_call.prompt_model(prompt=prompt)


def combine_synopsises(film_name, synopsis_list: list[str]) -> str:
    prompt = f"Please combine the following film synopsises found on imdb for the film {film_name} into one synopsis of length about 3-5 sentences. Don't output anything but the synopsis.\n\n"
    for synopsis in synopsis_list:
        prompt += synopsis
        prompt += "\n\n"
    
    return api_call.prompt_model(prompt=prompt)


def is_correct_film(film_suggestion: str, retrieved_title: str) -> str:
    answer = api_call.prompt_model(
        f"Could the film '{film_suggestion}' actually be the same as '{retrieved_title}'? answer only with y or n and nothing else."
    )
    return answer.startswith("y")



def get_synopsises_from_suggestion(film_suggestion: str) -> tuple[str, str]:
    ia = imdb.IMDb()

    search_movie = ia.search_movie(film_suggestion)
    retrieved_title = search_movie[0].data["title"]
    if not is_correct_film(film_suggestion=film_suggestion, retrieved_title=retrieved_title):
        print(f"Not correctly retrieved{film_suggestion} found {retrieved_title}.")
        return [], retrieved_title


    movie = ia.get_movie(search_movie[0].movieID)
    synopsis_list = movie.data["plot"]
    return synopsis_list, retrieved_title


def select_film_and_generate_synopsis() -> tuple[str, str]:
    while True:
        print("Getting film suggestion")
        film_suggestion = get_film_suggestion()
        #print(film_suggestion)
        synopsis_list, retrieved_title = get_synopsises_from_suggestion(film_suggestion=film_suggestion)
        #print(synopsis_list)
        if not synopsis_list:
            print(f"No synopsis found for {film_suggestion}")
        else:
            combined_synopsis = combine_synopsises(film_name=retrieved_title, synopsis_list=synopsis_list)
            print(retrieved_title)
            #print(combined_synopsis)
            break
    
    return retrieved_title, combined_synopsis

    