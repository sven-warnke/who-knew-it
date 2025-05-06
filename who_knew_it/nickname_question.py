import dataclasses
import pathlib
import random

from who_knew_it import api_call, questions

NICKNAMES_FOLDER = pathlib.Path(__file__).parent / "nicknames"


@dataclasses.dataclass
class NicknameQuestion(questions.Question):
    name: str
    nickname: str
    profession: str

    def question_text(self) -> str:
        return f"What is the nickname of {self.profession} {self.name}?"
    
    def get_correct_answer(self) -> str:
        return self.nickname
    


class NicknameQuestionGenerator(questions.QuestionGenerator):

    @staticmethod
    def random_sport() -> str:
        sports_weights = {
            "basketball": 134,
            "boxing": 31,
            "american-football": 103,
            "cricket": 33,
            "cycling": 39,
        }
        return random.choices(
            list(sports_weights.keys()), 
            weights=list(sports_weights.values())
        )[0]
    

    @staticmethod
    def profession_from_sport(sport: str) -> str:
        return {
            "basketball": "basketball player",
            "boxing": "boxer",
            "american-football": "american-football player",
            "cricket": "cricket player",
            "cycling": "cyclist",
        }[sport]


    def generate_question_and_correct_answer(self) -> NicknameQuestion:
        sport = NicknameQuestionGenerator.random_sport()
        file = NICKNAMES_FOLDER / f"{sport}.csv"
        with open(file, "r") as f:
            lines = f.readlines()

        while True:
            random_line = random.choice(lines).strip()

            nickname_name = random_line.split(",", 1)
            if len(nickname_name) == 2:
                return NicknameQuestion(
                    name=nickname_name[1].strip(), 
                    nickname=nickname_name[0].strip(), 
                    profession=NicknameQuestionGenerator.profession_from_sport(sport)
                    )
    
    def write_fake_answers(self, question: str, correct_answer: str, n_fake_answers: int) -> list[str]:
        raise NotImplementedError
