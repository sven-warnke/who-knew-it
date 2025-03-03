from who_knew_it import saying_generation


def test_generate_saying():
    saying = saying_generation.generate_saying("German")
    assert isinstance(saying, str)

    print("Saying: ", saying)