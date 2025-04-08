import arxiv  # type: ignore

from who_knew_it import arxiv_question


class TestArxivQuestionGenerator:
    def test_generate_candidates(self):
        generator = arxiv_question.ArxivQuestionGenerator()
        candidates = generator.generate_candidates()
        assert len(candidates) == 10
        for candidate in candidates:
            assert isinstance(candidate, arxiv.Result)
        print("Candidates: ", candidates)

    def test_generate_question_and_correct_answer(self):
        question = arxiv_question.ArxivQuestionGenerator().generate_question_and_correct_answer()
        assert isinstance(question, arxiv_question.ArxivQuestion)
        assert isinstance(question.get_correct_answer(), str)
        assert isinstance(question.question_text(), str)

        print("Question: ", question.question_text())
        print("Correct answer: ", question.get_correct_answer())
