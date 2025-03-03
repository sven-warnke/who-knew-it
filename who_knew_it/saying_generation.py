from who_knew_it import api_call


def generate_saying(country: str) -> str:
    prompt = f"""Please give me the english literal translation of a true {country} figure of speech. Ideally,
    the figure of speech sounds interesting and funny (even potentially dark or sexy using double entendres) to a
    native English speaker.
    That figure of speech must exist and cannot be invented. Please answer only with the literal english translation of the 
    figure of speech and a very short definition. Answer should be in the form
    
    original figure of speech: ...
    literal english translation: ...
    definition: ...
    """

    return api_call.prompt_model(prompt=prompt)
