from who_knew_it import pokemon_question


class TestPokemonQuestionGenerator:
    def test__random_animal_group_and_species(self):
        name = pokemon_question.PokemonQuestionGenerator().random_pokemon()
        assert isinstance(name, list)
        assert len(name) == 10
        for answer in name:
            assert isinstance(answer, str)
        print("Pokemon: ", name)

    
    def test_generate_question_and_correct_answer(self):
        question = pokemon_question.PokemonQuestionGenerator().generate_question_and_correct_answer()
        assert isinstance(question, pokemon_question.PokemonQuestion)
        assert isinstance(question.get_correct_answer(), str)
        assert isinstance(question.question_text(), str)

        print("Question: ", question.question_text())
        print("Correct answer: ", question.get_correct_answer())

    
    def test_write_fake_answers(self):
        question = pokemon_question.PokemonQuestionGenerator().generate_question_and_correct_answer()
        fake_answers = pokemon_question.PokemonQuestionGenerator().write_fake_answers(
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

