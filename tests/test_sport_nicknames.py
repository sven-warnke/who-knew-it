
from who_knew_it import nickname_question


def test_sport_question():
    question = nickname_question.NicknameQuestionGenerator().generate_question_and_correct_answer()
    assert question.question_text()
    assert question.get_correct_answer()
    print(question.question_text())
    print(question.get_correct_answer())