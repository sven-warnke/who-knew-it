from who_knew_it import word_definition_question


class TestOldEnglishWordDefinitionQuestionGenerator:
    def test_generate_question_and_correct_answer(self):
        
        question_generator = word_definition_question.OldEnglishWordDefinitionQuestionGenerator()
        question = question_generator.generate_question_and_correct_answer()
        print("Question: ", question.question_text())
        print("Correct answer: ", question.get_correct_answer())

        fake_answers = question_generator.write_fake_answers(
            question=question.question_text(),
            correct_answer=question.get_correct_answer(),
            n_fake_answers=2,
        )

        print("Fake answers: ")
        for answer in fake_answers:
            print(answer)
