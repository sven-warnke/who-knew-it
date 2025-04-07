from who_knew_it import animal_question


class TestAnimalQuestionGenerator:
    def test__random_animal_group_and_species(self):
        group, species = animal_question.AnimalQuestionGenerator()._random_animal_group_and_species()
        assert group in ["Mammals", "Reptiles", "Birds", "Fresh Water Fish", "Salt Water Fish", "Amphibians"]
        assert isinstance(species, list)
        assert len(species) == 50
        for answer in species:
            assert isinstance(answer, str)

        print("Group: ", group)
        print("Species: ", species)

    
    def test_generate_question_and_correct_answer(self):
        question = animal_question.AnimalQuestionGenerator().generate_question_and_correct_answer()
        assert isinstance(question, animal_question.AnimalQuestion)
        assert isinstance(question.get_correct_answer(), str)
        assert isinstance(question.question_text(), str)

        print("Question: ", question.question_text())
        print("Correct answer: ", question.get_correct_answer())

    
    def test_write_fake_answers(self):
        question = animal_question.AnimalQuestionGenerator().generate_question_and_correct_answer()
        fake_answers = animal_question.AnimalQuestionGenerator().write_fake_answers(
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

