import streamlit as st
import enum
from who_knew_it import fake_answer
from who_knew_it import answers
import random
from who_knew_it import movie_suggestion
import duckdb
import uuid
from pathlib import Path

DEFAULT_N_FAKE_ANSWERS = 2
MAX_N_FAKE_ANSWERS = 4

DB_FILE = Path(__file__).parent.parent / "database" / "file.db"


class Tables(enum.StrEnum):
    players = "players"
    games = "games"
    game_player = "game_player"


class Var(enum.StrEnum):
    player_id = "player_id"
    player_name = "player_name"
    game_id = "game_id"
    retrieved = "retrieved"
    answer_list = "answer_list"
    points = "points"
    is_answered = "is_answered"
    game_stage = "game_stage"


class GameStage(enum.IntEnum):
    no_game_selected = 0
    game_open = 1
    answer_writing = 2
    guessing = 3
    finished = 4


@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DB_FILE)


def get_cursor() -> duckdb.DuckDBPyConnection:
    return get_db_connection().cursor()


def create_tables_if_not_exist():
    queries = [
        """
                CREATE SEQUENCE IF NOT EXISTS seq_game_id START 1;
                """,
        f"""
                CREATE TABLE IF NOT EXISTS {Tables.games} (
                    {Var.game_id} INT PRIMARY KEY DEFAULT NEXTVAL('seq_game_id'),
                    {Var.game_stage} INT NOT NULL,
                );
                """,
        f"""
                CREATE TABLE IF NOT EXISTS {Tables.players} (
                    {Var.player_id} VARCHAR(255) PRIMARY KEY,
                    {Var.player_name} VARCHAR(255) NOT NULL
                );
                """,
        f"""
                CREATE TABLE IF NOT EXISTS {Tables.game_player} (
                    {Var.game_id} INT,
                    {Var.player_id} VARCHAR(255),
                    PRIMARY KEY ({Var.game_id}, player_id),
                    FOREIGN KEY ({Var.game_id}) REFERENCES {Tables.games}({Var.game_id}),
                    FOREIGN KEY ({Var.player_id}) REFERENCES {Tables.players}({Var.player_id})
                );
                """,
    ]

    with get_cursor() as con:
        for query in queries:
            con.execute(query)


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
    for var in [Var.retrieved, Var.answer_list]:
        st.session_state[var] = None


def initialize_points_if_not_exist() -> None:
    if not all_in_state_and_not_none([Var.points]):
        st.session_state[Var.points] = 0


def increase_points() -> None:
    initialize_points_if_not_exist()
    st.session_state[Var.points] += 1


def set_is_answered() -> None:
    st.session_state[Var.is_answered] = True


def initialize_new_game_in_db() -> int:
    with get_cursor() as con:
        [game_id] = con.execute(
            f"""
                INSERT INTO {Tables.games} ({Var.game_stage}) VALUES ({GameStage.game_open}) RETURNING {Var.game_id};
                """
        ).fetchall()

    return game_id[0]  # otherwise returns tuple


def set_new_game() -> None:
    game_id = initialize_new_game_in_db()
    st.session_state[Var.game_id] = game_id


def set_game_state(game_id: int, game_stage: GameStage) -> None:
    query = f"""
    UPDATE {Tables.games}
    SET {Var.game_stage} = {game_stage}
    WHERE {Var.game_id} = {game_id}
    """
    with get_cursor() as con:
        con.execute(query)


def get_game_stage_from_db(game_id: int) -> GameStage:
    query = (
        f"SELECT {Var.game_stage} FROM {Tables.games} WHERE {Var.game_id} = {game_id}"
    )

    with get_cursor() as con:
        results = con.execute(query).fetchall()

    if len(results) != 1:
        raise ValueError(
            f"Did not find exactly one entry for game id {game_id}: {results}"
        )
    return results[0][0]  # don't return tuple


def determine_game_stage(game_id: int | None) -> GameStage:
    if game_id is None:
        return GameStage.no_game_selected

    return get_game_stage_from_db(game_id=game_id)


def generate_player_id() -> str:
    return str(uuid.uuid4()).replace("-", "")


def register_player_id(player_id: str) -> None:
    query = f"""
            INSERT INTO {Tables.players} ({Var.player_id}, {Var.player_name}) VALUES ('{player_id}', '{player_id}');
            """
    with get_cursor() as con:
        con.execute(query)
        st.session_state[Var.player_id] = player_id


def determine_player_id() -> str:
    player_id = st.session_state.get(Var.player_id, None)
    if not player_id:
        player_id = generate_player_id()
        register_player_id(player_id=player_id)
    return player_id


def determine_game_id() -> int | None:
    return st.session_state.get(Var.game_id, None)


def main():
    create_tables_if_not_exist()

    player_id = determine_player_id()
    game_id = determine_game_id()

    game_stage = determine_game_stage(game_id)

    match game_stage:
        case GameStage.no_game_selected:
            find_game_screen(player_id=player_id)
        case GameStage.game_open:
            open_game_screen(player_id=player_id, game_id=game_id)
        case GameStage.answer_writing:
            answer_writing_screen(player_id=player_id, game_id=game_id)
        case GameStage.guessing:
            guessing_screen(player_id=player_id, game_id=game_id)
        case GameStage.finished:
            finished_screen(player_id=player_id, game_id=game_id)
        case unreachable:
            raise ValueError(f"Found {unreachable}")


def find_game_screen(player_id: str) -> None:
    st.title("Welcome to 'Who knew it?' without Matt Stewart")
    st.text(f"Hello {player_id}")
    st.button("Find Game", on_click=set_new_game)


def open_game_screen(player_id: str, game_id: int) -> None:
    st.title(f"This is your game. {game_id}")
    st.text(f"Hello {player_id}")
    st.button(
        "Start Game",
        on_click=lambda: set_game_state(
            game_id=game_id, game_stage=GameStage.answer_writing
        ),
    )


def answer_writing_screen(player_id: str, game_id: int) -> None:
    st.title("Write your answers!")
    st.button(
        "Next",
        on_click=lambda: set_game_state(game_id=game_id, game_stage=GameStage.guessing),
    )


def guessing_screen(player_id: str, game_id: int) -> None:
    n_fake_answers = st.number_input(
        "Number of wrong answers",
        min_value=0,
        max_value=MAX_N_FAKE_ANSWERS,
        value=DEFAULT_N_FAKE_ANSWERS,
    )

    if not all_in_state_and_not_none([Var.retrieved, Var.answer_list]):
        with st.spinner("Generating Question..."):
            retrieved_title, combined_synopsis = (
                movie_suggestion.select_film_and_generate_synopsis()
            )

        with st.spinner("Writing the wrong answers..."):
            answer_list = [answers.Answer(combined_synopsis, correct=True)]
            for _ in range(n_fake_answers):
                fake_answer_text = fake_answer.create_fake_movie_synopsis(
                    info_about_film=retrieved_title,
                    avoid_examples=[a.text for a in answer_list],
                )
                answer_list.append(answers.Answer(text=fake_answer_text, correct=False))

        random.shuffle(answer_list)

        st.session_state[Var.retrieved] = (retrieved_title, combined_synopsis)
        st.session_state[Var.answer_list] = answer_list
        st.session_state[Var.is_answered] = False

    else:
        retrieved_title, combined_synopsis = st.session_state[Var.retrieved]
        answer_list = st.session_state[Var.answer_list]

    st.header(f"What's the plot of the film {retrieved_title}?")

    is_answered = st.session_state[Var.is_answered]

    button_labels = get_button_labels(len(answer_list))

    button_outputs = []
    for label, an_answer in zip(button_labels, answer_list, strict=True):
        letter_col, text_col = st.columns([0.2, 0.8], border=True)
        with letter_col:
            b_output = st.button(
                label=f"{label}", disabled=is_answered, on_click=set_is_answered
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

    st.metric(label="Points", value=st.session_state[Var.points])
    st.button("Next", on_click=reset_question_state)


if __name__ == "__main__":
    main()
