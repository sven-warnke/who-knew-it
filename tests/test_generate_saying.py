from who_knew_it import saying_generation


def test_generate_saying():
    language = "Mexican"
    saying = saying_generation.generate_saying(language)
    assert isinstance(saying, str)

    print("Saying: ", saying)

    check = saying_generation.extract_saying_if_possible(saying, language=language)
    print("Check: ", check)


class TestSayingQuestionGenerator:
    def test_generate_question_and_correct_answer(self):
        question_generator = saying_generation.SayingQuestionGenerator()
        saying_question = question_generator.generate_question_and_correct_answer()
        print("Question: ", saying_question)

        fake_answers = question_generator.write_fake_answers(
            question=saying_question.question_text(),
            correct_answer=saying_question.correct_answer,
            n_fake_answers=2,
        )

        print("Correct answer: ", saying_question.correct_answer)
        print("Fake answers: ")
        for answer in fake_answers:
            print(answer)