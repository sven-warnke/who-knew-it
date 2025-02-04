from who_knew_it import api_call


def create_fake_movie_synopsis(info_about_film: str, avoid_examples: list[str]) -> str:
    if avoid_examples:
        avoid_list_string = "Please also avoid anything that is similar to the following examples:\n"
        avoid_list_string += "\n\n".format([" " * 4 + example for example in avoid_examples])
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




