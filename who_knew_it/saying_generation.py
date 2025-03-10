import dataclasses
import random

from who_knew_it import api_call, questions, random_word


def _random_divider() -> str:
    return random.choice(["\n" * 2, " | ", " - ", " " * 3, "  ", ])



@dataclasses.dataclass
class Saying:
    literal_translation: str
    definition: str
    divider: str

    def format(self) -> str:
        return f"{self.literal_translation}{self.divider}{self.definition}"


@dataclasses.dataclass
class SayingQuestion(questions.Question):
    language: str
    saying: Saying

    @property
    def correct_answer(self) -> str:
        return self.saying.format()

    def question_text(self) -> str:
        return f'What is a real {self.language} figure of speech? Please write the literal translation and the meaning of the figure of speech.'


class SayingQuestionGenerator(questions.QuestionGenerator):
    def generate_question_and_correct_answer(self) -> SayingQuestion:
        while True:
            language = generate_random_languages()
            print(language)
            saying = generate_saying(language)
            extracted_question = extract_saying_if_possible(saying, language)
            if extracted_question:
                return extracted_question
    
    def write_fake_answers(self, question: str, correct_answer: str, n_fake_answers: int) -> list[str]:
        
        fake_answers: list[str] = []
        avoid_examples = [correct_answer]

        while len(fake_answers) < n_fake_answers:
            wrong_answer = _fake_saying(question=question, avoid_examples=avoid_examples)

            if fake_answer := extract_fake_saying_if_possible(wrong_answer):
                fake_answers.append(fake_answer.format())
                avoid_examples.append(
                    f"""literal english translation: {fake_answer.literal_translation}
definition: {fake_answer.definition}"""
                )

        return fake_answers


def generate_random_languages() -> str:
    list_of_languages = [
        "Spanish",
        "French",
        "Italian",
        "Portuguese",
        "Russian",
        "Japanese",
        "Korean",
        "Chinese",
        "Arabic",
        "Hindi",
        "Bengali",
        "Tamil",
        "Telugu",
        "Malayalam",
        "Urdu",
        "Gujarati",
        "Punjabi",
        "Sinhalese",
        "Burmese",
        "Khmer",
        "Thai",
        "Indonesian",
        "Vietnamese",
        "Malay",
        "Mandarin",
        "Cantonese",
        "Mexican",
        "Polish",
        "Romanian",
        "Serbian",
        "Ukrainian",
        "Bulgarian",
        "Czech",
        "Danish",
        "Dutch",
        "Finnish",
        "Greek",
        "Hungarian",
        "Icelandic",
        "Latvian",
        "Lithuanian",
        "Norwegian",
        "Slovak",
        "Slovakian",
        "Swedish",
        "Turkish",
        "Welsh",
        "Yiddish",
    ]

    return random.choice(list_of_languages)


def _fake_saying(question: str, avoid_examples: list[str]) -> str:
    
    avoid_str = "\n\n".join(avoid_examples)
    
    prompt = f"""
    You are playing a game where you have to write convincing and fun fake answers, that could trick people into picking it. For the following question: "{question}"
    Please write a convincing fake figure of speech, that doesn't exist but is completely made up. The figure of speech should sound interesting and funny.
    Please make your answer completely different
    from the following examples:

    {avoid_str}

    Please output only the literal English translation of the invented figure of speech and its supposed meaning in the following form.

    literal english translation: ...
    definition: ... 
    """
    return api_call.prompt_model(prompt=prompt)


def extract_fake_saying_if_possible(saying: str) -> Saying | None:
    answer_lines = saying.split("\n")
    print(answer_lines)
    if len(answer_lines) not in [2, 3]:
        print("wrong number of lines")
        return None
    
    for line in answer_lines[:2]:
        if ":" not in line:
            print("No : in line")
            return None
    
    literal_translation = answer_lines[0].split(":", 1)[1].strip()
    definition = answer_lines[1].split(":", 1)[1].strip()
    
    if not literal_translation or not definition:
        print("wrong format")
        return None
    
    return Saying(literal_translation=literal_translation, definition=definition, divider=_random_divider())


def generate_saying(country: str) -> str:

    random_words = [random_word.get_random_word() for _ in range(10)]  # To inject randomness
    print(random_words)

    prompt = f"""Please give me the english literal translation of a true {country} figure of speech. Ideally,
    the figure of speech sounds interesting and funny (even potentially dark or sexy using double entendres) to a
    native English speaker. It should be a unknown to most non {country} people. If you can, the figure of speech 
    should have something to do with one of the following words:
    {", ".join(random_words)}
    That figure of speech must exist and cannot be invented. Your answer should be in the following form and nothing else:
    
    original figure of speech: ...
    literal english translation: ...
    definition: ...
    """

    return api_call.prompt_model(prompt=prompt)


def extract_saying_if_possible(answer: str, language: str) -> SayingQuestion | None:
    answer_lines = answer.split("\n")
    print(answer_lines)
    if len(answer_lines) not in [3, 4]:
        print("wrong number of lines")
        return None
    
    for line in answer_lines[:3]:
        if ":" not in line:
            print("No : in line")
            return None
    
    original_figure_of_speech = answer_lines[0].split(":", 1)[1].strip()
    literal_translation = answer_lines[1].split(":", 1)[1].strip()
    definition = answer_lines[2].split(":", 1)[1].strip()
    
    if not original_figure_of_speech or not literal_translation or not definition:
        print("wrong format")
        return None
    
    prompt = f"""
    Please check whether the following is an existing figure of speech in {language}. Also check whether the figure of speech
    is correctly translated and the meaning is correct. If it is, answer "yes", otherwise answer "no".:
    
    {answer}
    """

    model_answer = api_call.prompt_model(prompt=prompt)
    print(model_answer)

    if not model_answer.lower().startswith("yes"):
        return None

    return SayingQuestion(
        language=language, 
        saying=Saying(
            literal_translation=literal_translation,
            definition=definition,
            divider=_random_divider(),
        )
    )

