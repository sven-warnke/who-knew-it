from pathlib import Path

import imdb  # type: ignore

from who_knew_it import api_call

PROMPT_FOLDER_PATH = Path(__file__).parent / "prompts"


def _get_film_suggestion() -> str:
    prompt_file = "film_suggestion.txt"
    prompt_file_path = PROMPT_FOLDER_PATH / prompt_file

    with open(prompt_file_path) as f:
        prompt = f.read()

    return api_call.prompt_model(prompt=prompt)


def _combine_synopsises(film_name, synopsis_list: list[str]) -> str:
    prompt = f"Please combine the following film synopsises found on imdb for the film {film_name} into one synopsis of length about 3-5 sentences. Don't output anything but the synopsis.\n\n"
    for synopsis in synopsis_list:
        prompt += synopsis
        prompt += "\n\n"

    return api_call.prompt_model(prompt=prompt)


def _is_correct_film(film_suggestion: str, retrieved_title: str) -> bool:
    answer = api_call.prompt_model(
        f"Could the film '{film_suggestion}' actually be the same as '{retrieved_title}'? answer only with y or n and nothing else."
    )
    return answer.startswith("y")


def _get_synopsises_from_suggestion(film_suggestion: str) -> tuple[list[str], str]:
    ia = imdb.IMDb()

    search_movie = ia.search_movie(film_suggestion)
    retrieved_title = search_movie[0].data["title"]
    if not _is_correct_film(
        film_suggestion=film_suggestion, retrieved_title=retrieved_title
    ):
        print(f"Not correctly retrieved{film_suggestion} found {retrieved_title}.")
        return [], retrieved_title

    movie = ia.get_movie(search_movie[0].movieID)
    synopsis_list = movie.data["plot"]
    return synopsis_list, retrieved_title


def select_film_and_generate_synopsis() -> tuple[str, str]:
    while True:
        print("Getting film suggestion")
        film_suggestion = _get_film_suggestion()
        # print(film_suggestion)
        synopsis_list, retrieved_title = _get_synopsises_from_suggestion(
            film_suggestion=film_suggestion
        )
        # print(synopsis_list)
        if not synopsis_list:
            print(f"No synopsis found for {film_suggestion}")
        else:
            combined_synopsis = _combine_synopsises(
                film_name=retrieved_title, synopsis_list=synopsis_list
            )
            print(retrieved_title)
            # print(combined_synopsis)
            break

    return retrieved_title, combined_synopsis


def create_fake_movie_synopsis(info_about_film: str, avoid_examples: list[str]) -> str:
    if avoid_examples:
        avoid_list_string = (
            "Please also avoid anything that is similar to the following examples:\n"
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