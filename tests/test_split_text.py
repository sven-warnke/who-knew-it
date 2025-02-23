from who_knew_it import streamlit_app


def test_abbreviate_text():
    assert streamlit_app.abbreviate_text("Hello World", 5) == "Hello"
    assert streamlit_app.abbreviate_text("Hello World", 6) == "Hello "
    assert streamlit_app.abbreviate_text("Hello World", 8) == "Hello "
    assert streamlit_app.abbreviate_text("Hello World, you all", 15) == "Hello World, "
