import abc


class Question(abc.ABC):

    @abc.abstractmethod
    def get_correct_answer(self) -> str:
        ...
    @abc.abstractmethod
    def question_text(self) -> str:
        ...


class QuestionGenerator(abc.ABC):
    @abc.abstractmethod
    def generate_question_and_correct_answer(self) -> Question:
        ...
    
    @abc.abstractmethod
    def write_fake_answers(self, question: str, correct_answer: str, n_fake_answers: int) -> list[str]:
        ...
