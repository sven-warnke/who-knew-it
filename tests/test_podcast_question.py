from who_knew_it import podcast_question


class TestPodcastQuestionGenerator:
    def test_get_random_podcasts(self):
        generator = podcast_question.PodcastQuestionGenerator()
        candidates = generator.get_random_podcasts()
        assert len(candidates) == 20
        for candidate in candidates:
            assert isinstance(candidate, podcast_question.PodcastQuestion)
        print("Candidates: ", candidates)

    def test_generate_question_and_correct_answer(self):
        question = podcast_question.PodcastQuestionGenerator().generate_question_and_correct_answer()
        assert isinstance(question, podcast_question.PodcastQuestion)
        assert isinstance(question.get_correct_answer(), str)
        assert isinstance(question.question_text(), str)

        print("Question: ", question.question_text())
        print("Correct answer: ", question.get_correct_answer())

    def test_write_fake_answers(self):
        question = podcast_question.PodcastQuestionGenerator().generate_question_and_correct_answer()
        fake_answers = podcast_question.PodcastQuestionGenerator().write_fake_answers(
            question=question.question_text(),
            correct_answer=question.get_correct_answer(),
            n_fake_answers=2,
        )

        assert isinstance(fake_answers, list)
        assert all(isinstance(answer, str) for answer in fake_answers)
        assert len(fake_answers) == 2

        print("Question: ", question.question_text())

        print("Correct answer: ", question.get_correct_answer())

        print("Fake answers: ")
        for answer in fake_answers:
            print(answer)
