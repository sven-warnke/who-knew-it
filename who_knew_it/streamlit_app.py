import streamlit as st

from who_knew_it import fake_answer
from who_knew_it import answers
import random
from who_knew_it import movie_suggestion
import duckdb


VAR_RETRIEVED = "retrieved"
VAR_ANSWER_LIST = "answer_list"

VAR_POINTS = "points"
VAR_IS_ANSWERED = "is_answered"

DEFAULT_N_FAKE_ANSWERS = 2
MAX_N_FAKE_ANSWERS = 4

DB_FILE = "file.db"


@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DB_FILE)


def get_cursor() -> duckdb.DuckDBPyConnection:
    return get_db_connection().cursor()


def create_tables():
    pass


def get_alphabet_letter(n: int) -> str:
    if n < 0:
        raise ValueError("Input cannot be negative.")
    elif n > 25:  # For a 0-based index
        raise ValueError("Input is too large. Must be between 0 and 25.")

    return chr(65 + n)  # 65 is the ASCII value for 'A'


def get_button_labels(length_of_labels: int) -> list[str]:
    if length_of_labels <= 0:
        raise ValueError(f"Length must be positive, found {length_of_labels}")

    return [get_alphabet_letter(i) for i in range(length_of_labels)]


def all_in_state_and_not_none(var_list: list[str]) -> bool:
    for var in var_list:
        if not var in st.session_state or st.session_state[var] is None:
            return False
    return True


def reset_question_state() -> None:
    for var in [VAR_RETRIEVED, VAR_ANSWER_LIST]:
        st.session_state[var] = None


def initialize_points_if_not_exist() -> None:
    if not all_in_state_and_not_none([VAR_POINTS]):
        st.session_state[VAR_POINTS] = 0


def increase_points() -> None:
    initialize_points_if_not_exist()
    st.session_state[VAR_POINTS] += 1


def is_is_answered() -> None:
    st.session_state[VAR_IS_ANSWERED] = True


def main():
    st.title("Welcome to 'Who knew it?' without Matt Stewart")

    n_fake_answers = st.number_input(
        "Number of wrong answers",
        min_value=0,
        max_value=MAX_N_FAKE_ANSWERS,
        value=DEFAULT_N_FAKE_ANSWERS,
    )

    if not all_in_state_and_not_none([VAR_RETRIEVED, VAR_ANSWER_LIST]):
        with st.spinner("Generating Question..."):
            retrieved_title, combined_synopsis = (
                movie_suggestion.select_film_and_generate_synopsis()
            )

        with st.spinner("Writing the wrong answers..."):
            answer_list = [answers.Answer(combined_synopsis, correct=True)]
            for i in range(n_fake_answers):
                fake_answer_text = fake_answer.create_fake_movie_synopsis(
                    info_about_film=retrieved_title,
                    avoid_examples=[a.text for a in answer_list],
                )
                answer_list.append(answers.Answer(text=fake_answer_text, correct=False))

        random.shuffle(answer_list)

        st.session_state[VAR_RETRIEVED] = (retrieved_title, combined_synopsis)
        st.session_state[VAR_ANSWER_LIST] = answer_list
        st.session_state[VAR_IS_ANSWERED] = False

    else:
        retrieved_title, combined_synopsis = st.session_state[VAR_RETRIEVED]
        answer_list = st.session_state[VAR_ANSWER_LIST]

    is_answered = st.session_state[VAR_IS_ANSWERED]
    st.header(f"What's the plot of the film {retrieved_title}?")

    button_labels = get_button_labels(len(answer_list))

    button_outputs = []
    for i, an_answer in zip(button_labels, answer_list, strict=True):
        letter_col, text_col = st.columns([0.2, 0.8], border=True)
        with letter_col:
            b_output = st.button(
                label=f"{i}", disabled=is_answered, on_click=is_is_answered
            )
            button_outputs.append(b_output)
        with text_col:
            st.text(an_answer.text)

    initialize_points_if_not_exist()

    if any(button_outputs):
        [choice] = [i for i, b in enumerate(button_outputs) if b]

        [correct_answer] = [i for i, a in enumerate(answer_list) if a.correct]

        if choice == correct_answer:
            st.text("Correct")
            increase_points()
        else:
            st.text("False!")
            st.text(f"The correct answer was {button_labels[correct_answer]}.")

    st.metric(label="Points", value=st.session_state[VAR_POINTS])
    st.button("Next", on_click=reset_question_state)


if __name__ == "__main__":
    main()
