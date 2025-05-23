import dataclasses
import enum
import textwrap
import time
import uuid
from functools import partial
from pathlib import Path

import duckdb
import extra_streamlit_components as stx  # type: ignore
import streamlit as st

from who_knew_it import (
    animal_question,
    arxiv_question,
    authenticator,
    movie_suggestion,
    name_generation,
    podcast_question,
    pokemon_question,
    questions,
    word_definition_question,
)

DEFAULT_N_FAKE_ANSWERS = 2
MAX_N_FAKE_ANSWERS = 4
N_MAX_PLAYERS = 5
N_QUESTIONS = 6
MAX_NAME_LENGTH = 20
DISPLAY_LENGTH_LIMIT_TO_EXPANDER = 30

DB_FILE = Path(__file__).parent.parent / "database" / "file.db"

HOUSE_PLAYER_ID_PREFIX = "house"
CORRECT_ANSWER_ID = "correct_answer"
HOUSE_NAME = "The House"
CORRECT_ANSWER_NAME = "Correct Answer"


class Tables(enum.StrEnum):
    players = "players"
    games = "games"
    game_player = "game_player"
    questions = "questions"
    player_answers = "player_answers"
    points = "points"


class Var(enum.StrEnum):
    player_id = "player_id"
    player_name = "player_name"
    game_id = "game_id"
    retrieved = "retrieved"
    answer_list = "answer_list"
    points = "points"
    is_answered = "is_answered"
    game_stage = "game_stage"
    is_host = "is_host"
    question_number = "question_number"
    question = "question"
    correct_answer = "correct_answer"
    answer_text = "answer_text"
    is_house = "is_house"
    answer_order = "answer_order"
    correct_answer_rank = "correct_answer_rank"
    player_id_of_chosen_answer = "player_id_of_chosen_answer"
    fooled_players = "fooled_players"
    dummy_cookie = "dummy_cookie"
    has_accepted_cookies = "has_accepted_cookies"
    name = "name"  # used by streamlit authenticator


class GameStage(enum.IntEnum):
    no_game_selected = 0
    game_open = 1
    answer_writing = 2
    guessing = 3
    reveal = 4
    finished = 5


def get_house_player_id(i: int) -> str:
    return f"{HOUSE_PLAYER_ID_PREFIX}_{i}"


@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DB_FILE)


def get_cursor() -> duckdb.DuckDBPyConnection:
    return get_db_connection().cursor()


@st.cache_resource
def create_tables_if_not_exist() -> None:

    DB_FILE.parent.mkdir(exist_ok=True, parents=True)

    for f in DB_FILE.parent.glob("*"):
        f.unlink()

    queries = [
        """
                BEGIN TRANSACTION;
        """,
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
                    {Var.player_name} VARCHAR(255) NOT NULL,
                    {Var.is_house} BOOLEAN DEFAULT FALSE
                );
                """,
        f"""
                INSERT INTO {Tables.players} ({Var.player_id}, {Var.player_name}, {Var.is_house}) 
                VALUES 
                ('{get_house_player_id(0)}', '{HOUSE_NAME}', TRUE),
                ('{get_house_player_id(1)}', '{HOUSE_NAME}', TRUE),
                ('{get_house_player_id(2)}', '{HOUSE_NAME}', TRUE),
                ('{get_house_player_id(3)}', '{HOUSE_NAME}', TRUE),
                ('{get_house_player_id(4)}', '{HOUSE_NAME}', TRUE),
                ('{get_house_player_id(5)}', '{HOUSE_NAME}', TRUE)
                ;
        """,
        f"""
                CREATE TABLE IF NOT EXISTS {Tables.game_player} (
                    {Var.game_id} INT,
                    {Var.player_id} VARCHAR(255),
                    {Var.is_host} BOOLEAN,
                    PRIMARY KEY ({Var.game_id}, {Var.player_id}),
                    FOREIGN KEY ({Var.game_id}) REFERENCES {Tables.games}({Var.game_id}),
                    FOREIGN KEY ({Var.player_id}) REFERENCES {Tables.players}({Var.player_id})
                );
                """,
        f"""
        CREATE TABLE IF NOT EXISTS {Tables.questions} (
            {Var.game_id} INT,
            {Var.question_number} INT NOT NULL,
            {Var.question} VARCHAR,
            {Var.correct_answer} VARCHAR,
            {Var.is_answered} BOOLEAN DEFAULT FALSE,
            {Var.correct_answer_rank} FLOAT DEFAULT random(),
            PRIMARY KEY ({Var.game_id}, {Var.question_number}),
            FOREIGN KEY ({Var.game_id}) REFERENCES {Tables.games}({Var.game_id}),
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {Tables.player_answers} (
            {Var.game_id} INT,
            {Var.question_number} INT,
            {Var.player_id} VARCHAR(255),
            {Var.answer_text} VARCHAR,
            {Var.answer_order} FLOAT DEFAULT random(),
            {Var.player_id_of_chosen_answer} VARCHAR(255),
            PRIMARY KEY ({Var.game_id}, {Var.question_number}, {Var.player_id}),
            FOREIGN KEY ({Var.game_id}) REFERENCES {Tables.games}({Var.game_id}),
            FOREIGN KEY ({Var.player_id}) REFERENCES {Tables.players}({Var.player_id}),
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {Tables.points} (
            {Var.game_id} INT,
            {Var.question_number} INT,
            {Var.player_id} VARCHAR(255),
            {Var.points} INT,
            PRIMARY KEY ({Var.game_id}, {Var.question_number}, {Var.player_id}),
            FOREIGN KEY ({Var.game_id}) REFERENCES {Tables.games}({Var.game_id}),
            FOREIGN KEY ({Var.player_id}) REFERENCES {Tables.players}({Var.player_id}),
        );
        """,
        """
        COMMIT;
        """,
    ]

    with get_cursor() as con:
        for query in queries:
            try:
                con.execute(query)
            except duckdb.TransactionException as e:
                print(f"{e}")


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


def set_is_answered(game_id: int, question_number: int) -> None:
    query = f"""
    UPDATE {Tables.questions} SET {Var.is_answered} = TRUE
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number};
    """
    print("set_is_answered: ", query)
    with get_cursor() as con:
        con.execute(query)


def initialize_new_game_in_db() -> int:
    with get_cursor() as con:
        [game_id] = con.execute(
            f"""
                INSERT INTO {Tables.games} ({Var.game_stage}) VALUES ({GameStage.game_open}) RETURNING {Var.game_id};
                """
        ).fetchall()

    return game_id[0]  # otherwise returns tuple


def get_all_opened_games() -> list[int]:
    query = f"""
    SELECT {Var.game_id} FROM {Tables.games}
    WHERE {Var.game_stage} = {GameStage.game_open};
    """

    with get_cursor() as con:
        result = con.execute(query).fetchall()

    return [res[0] for res in result]


def get_all_players_in_game(game_id: int) -> dict[str, str]:
    query = f"""
    SELECT {Tables.players}.{Var.player_id}, {Tables.players}.{Var.player_name} FROM {Tables.game_player}
    JOIN {Tables.players} ON  {Tables.players}.{Var.player_id} = {Tables.game_player}.{Var.player_id}
    WHERE {Tables.game_player}.{Var.game_id} = {game_id};
    """
    print("get_all_players_in_game: ", query)
    with get_cursor() as con:
        result = con.execute(query).fetchall()

    return {res[0]: res[1] for res in result}


def create_and_join_new_game(player_id: str) -> None:
    game_id = initialize_new_game_in_db()
    join_game(player_id=player_id, game_id=game_id, is_host=True)


def set_game_state(game_id: int, game_stage: GameStage) -> None:
    query = f"""
    UPDATE {Tables.games}
    SET {Var.game_stage} = {game_stage}
    WHERE {Var.game_id} = {game_id};
    """
    with get_cursor() as con:
        con.execute(query)


def get_game_stage_from_db(game_id: int) -> GameStage | None:
    query = (
        f"SELECT {Var.game_stage} FROM {Tables.games} WHERE {Var.game_id} = {game_id}"
    )

    with get_cursor() as con:
        results = con.execute(query).fetchall()

    if len(results) != 1:
        return None
    return results[0][0]  # don't return tuple


def determine_game_stage(game_id: int | None) -> GameStage | None:
    if game_id is None:
        return GameStage.no_game_selected

    return get_game_stage_from_db(game_id=game_id)


def generate_player_id() -> str:
    return str(uuid.uuid4()).replace("-", "")


def register_player_id_and_name(player_id: str, player_name: str) -> None:
    query = f"""
            INSERT INTO {Tables.players} ({Var.player_id}, {Var.player_name}) VALUES ('{player_id}', '{player_name}');
            """
    with get_cursor() as con:
        con.execute(query)


def set_player_name(player_id: str, player_name: str) -> None:
    if not player_name:
        st.error("Player name cannot be empty.")
        return

    if player_name == "empty":
        st.error("Player name cannot be empty.")
        return

    if player_name.lower() == HOUSE_NAME.lower():
        st.error(f"Player name cannot be '{HOUSE_NAME}'.")
        return

    if player_name.lower() == CORRECT_ANSWER_NAME.lower():
        st.error(f"Player name cannot be '{CORRECT_ANSWER_NAME}'.")
        return

    _set_player_name(player_id=player_id, player_name=player_name)
    st.success("Player name changed.")


def _set_player_name(player_id: str, player_name: str) -> None:
    if not player_name:
        raise ValueError("Player name cannot be empty.")

    query = f"""
    UPDATE {Tables.players} SET {Var.player_name} = '{player_name}'
    WHERE {Var.player_id} = '{player_id}';
    """

    print("set_player_name: ", query)
    with get_cursor() as con:
        con.execute(query)


def get_player_name(player_id: str) -> str:
    query = f"""
    SELECT {Var.player_name} FROM {Tables.players} WHERE {Var.player_id} = '{player_id}'
    """
    print("get_player_name: ", query)
    with get_cursor() as con:
        result = con.execute(query).fetchall()

    if len(result) != 1:
        raise ValueError(f"Expected result of length 1, found {result}")

    return result[0][0]


def player_id_is_in_db(player_id: str) -> bool:
    query = f"""
    SELECT {Var.player_id} FROM {Tables.players} WHERE {Var.player_id} = '{player_id}'
    """
    print("player_id_is_in_db: ", query)
    with get_cursor() as con:
        result = con.execute(query).fetchall()

    if len(result) > 1:
        raise ValueError(f"Expected result of length 1, found {result}")

    return len(result) == 1


def determine_player_id() -> str:
    cookie_controller = stx.CookieManager(key="player_id_manager")  # key needs to be different from the one authenticator uses
    player_id = st.session_state.get(str(Var.player_id))

    if not player_id:
        player_id = cookie_controller.get(str(Var.player_id))
        print("found player_id in cookie", player_id)

    if not player_id:
        time.sleep(1)
        player_id = cookie_controller.get(str(Var.player_id))  # cookie manager needs time to find cookies initially
        print("found player_id after sleeping", player_id)

    if player_id and not player_id_is_in_db(player_id=player_id):
        print("Not in db deleting player_id")
        player_id = None
        cookie_controller.delete(str(Var.player_id))
        st.session_state[str(Var.player_id)] = None

    if not player_id:
        player_id = generate_player_id()
        player_name = name_generation.generate_player_name()
        register_player_id_and_name(player_id=player_id, player_name=player_name)

    st.session_state[str(Var.player_id)] = player_id
    cookie_controller.set(str(Var.player_id), player_id)

    return player_id


def determine_game_id() -> int | None:
    game_id = st.query_params.get(str(Var.game_id), None)
    if game_id is None or not game_id.isdigit():
        return None

    return int(game_id)


def _n_players_in_game_query(game_id: int) -> str:
    return f"""
    SELECT COUNT(*) FROM {Tables.game_player} WHERE {Var.game_id} = {game_id}
    """


def add_points(
    game_id: int, question_number: int, points_per_player_id: dict[str, int]
) -> None:
    item_rows = ", ".join(
        f"({game_id}, {question_number}, '{player_id}', {point})"
        for player_id, point in points_per_player_id.items()
    )
    query = f"""
    INSERT INTO {Tables.points} ({Var.game_id}, {Var.question_number}, {Var.player_id}, {Var.points}) VALUES
    {item_rows}
    ON CONFLICT ({Var.game_id}, {Var.question_number}, {Var.player_id}) 
    DO UPDATE SET {Var.points} = EXCLUDED.{Var.points};
    """
    print("add_points: ", query)
    with get_cursor() as con:
        con.execute(query)


def join_game(player_id: str, game_id: int, is_host: bool) -> None:
    print(f"{player_id} tries to join game {game_id}.")

    joined_succesfully = player_id in get_all_players_in_game(game_id=game_id)

    if not joined_succesfully:
        subquery = _n_players_in_game_query(game_id=game_id)
        query = f"""
        INSERT INTO {Tables.game_player} ({Var.player_id}, {Var.game_id}, {Var.is_host}) 
        SELECT '{player_id}', {game_id}, {is_host}
        WHERE ({subquery}) < {N_MAX_PLAYERS};
        """
        print("join_game: query: ", query)
        with get_cursor() as con:
            con.execute(query)
        joined_succesfully = player_id in get_all_players_in_game(game_id=game_id)

    if joined_succesfully:
        st.query_params[Var.game_id] = str(game_id)
        print(f"{player_id} joined game {game_id}.")


def remove_from_game(player_id: str, game_id: int) -> None:
    query = f"""
    BEGIN TRANSACTION;
    DELETE FROM {Tables.game_player} WHERE {Var.player_id} = '{player_id}' AND {Var.game_id} = {game_id};
    DELETE FROM {Tables.points} WHERE {Var.player_id} = '{player_id}' AND {Var.game_id} = {game_id};
    DELETE FROM {Tables.player_answers} WHERE {Var.player_id} = '{player_id}' AND {Var.game_id} = {game_id};
    COMMIT;
    """
    print("remove_from_game: ", query)
    with get_cursor() as con:
        con.execute(query)
    
    close_game_if_no_host(game_id=game_id)


def close_game_if_no_host(game_id: int) -> None:
    query = f"""
    SELECT {Var.player_id} FROM {Tables.game_player} WHERE {Var.game_id} = {game_id} AND {Var.is_host} = TRUE;
    """
    print("close_game_if_no_host: ", query)
    with get_cursor() as con:
        hosts = con.execute(query).fetchall()
    if len(hosts) == 0:
        close_game(game_id=game_id)


def close_game(game_id: int) -> None:
    
    query = f"""
    DELETE FROM {Tables.game_player} WHERE {Var.game_id} = {game_id};
    """
    print("close_game_if_no_host: ", query)
    with get_cursor() as con:
        con.execute(query)

    query = f"""
    DELETE FROM {Tables.points} WHERE {Var.game_id} = {game_id};
    """
    print("close_game_if_no_host: ", query)
    with get_cursor() as con:
        con.execute(query)

    query = f"""
    DELETE FROM {Tables.questions} WHERE {Var.game_id} = {game_id};
    """
    print("close_game_if_no_host: ", query)
    with get_cursor() as con:
        con.execute(query)

    query = f"""
    DELETE FROM {Tables.player_answers} WHERE {Var.game_id} = {game_id};
    """
    print("close_game_if_no_host: ", query)
    with get_cursor() as con:
        con.execute(query)

    query = f"""
    DELETE FROM {Tables.games} WHERE {Var.game_id} = {game_id};
    """
    print("close_game_if_no_host: ", query)
    with get_cursor() as con:
        con.execute(query)


def kick_from_game(player_id: str, game_id: int) -> None:
    remove_from_game(player_id=player_id, game_id=game_id)
    st.info(f"Player was kicked from game {game_id}.")


def leave_game(player_id: str, game_id: int) -> None:
    remove_from_game(player_id=player_id, game_id=game_id)
    try:
        del st.query_params[Var.game_id]
    except KeyError:
        pass


def is_player_host(player_id: str, game_id: int) -> bool:
    query = f"""
    SELECT {Var.is_host} FROM {Tables.game_player} 
    WHERE {Var.player_id} = '{player_id}' AND {Var.game_id} = {game_id}; 
    """
    with get_cursor() as con:
        con.execute(query)
        result = con.fetchall()

    if len(result) > 1:
        raise ValueError(f"Found multiple entries, expected at most 1: {result}.")
    if not result:
        return False
    return bool(result[0][0])


def initialize_questions(game_id: int, n_questions: int) -> None:
    if n_questions < 1:
        raise ValueError(
            f"Number of questions must be at least 1, received {n_questions}."
        )

    item_rows = ",\n".join([f"({game_id}, {i})" for i in range(1, n_questions + 1)])
    query = f"""
    INSERT INTO {Tables.questions} ({Var.game_id}, {Var.question_number}) VALUES
    {item_rows}
    ON CONFLICT ({Var.game_id}, {Var.question_number}) DO NOTHING;
    """
    print("initialize_questions: ", query)
    with get_cursor() as con:
        con.execute(query)


def initialize_answers(game_id: int) -> None:
    query = f"""
    INSERT INTO {Tables.player_answers} ({Var.game_id}, {Var.question_number}, {Var.player_id}) 
    SELECT {Tables.questions}.{Var.game_id}, {Tables.questions}.{Var.question_number}, {Tables.game_player}.{Var.player_id}
    FROM {Tables.questions} 
    JOIN {Tables.game_player}
    ON {Tables.questions}.{Var.game_id} = {Tables.game_player}.{Var.game_id}
    WHERE {Tables.questions}.{Var.game_id} = {game_id};
    """
    print("initialize_answers: ", query)
    with get_cursor() as con:
        con.execute(query)


def get_all_fake_answers(game_id: int, question_number: int) -> list[str | None]:
    query = f"""
    SELECT {Var.answer_text} FROM {Tables.player_answers}
    JOIN {Tables.players} ON {Tables.player_answers}.{Var.player_id} = {Tables.players}.{Var.player_id}
    WHERE {Tables.player_answers}.{Var.game_id} = {game_id} 
    AND {Tables.player_answers}.{Var.question_number} = {question_number}
    AND {Tables.players}.{Var.is_house} = TRUE;
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()
    return [res[0] for res in result]


def start_game(game_id: int, n_questions: int) -> None:
    for i in range(DEFAULT_N_FAKE_ANSWERS):
        join_game(player_id=get_house_player_id(i), game_id=game_id, is_host=False)

    initialize_questions(game_id=game_id, n_questions=n_questions)
    initialize_answers(game_id=game_id)

    set_game_state(game_id=game_id, game_stage=GameStage.answer_writing)


def determine_first_unanswered_question_number(game_id: int) -> int | None:
    query = f"""
    SELECT MIN({Var.question_number}) FROM {Tables.questions}
    WHERE {Var.is_answered} = FALSE AND {Var.game_id} = {game_id};
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()

    if len(result) != 1:
        raise ValueError(f"Expected result of length 1, found {result}")
    return result[0][0]


def get_question(game_id: int, question_number: int) -> str | None:
    query = f"""
    SELECT ({Var.question}) FROM {Tables.questions}
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number};
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()

    if len(result) != 1:
        raise ValueError(f"Expected result of length 1, found {result}")
    return result[0][0]


def get_correct_answer(game_id: int, question_number: int) -> str | None:
    query = f"""
    SELECT ({Var.correct_answer}) FROM {Tables.questions}
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number};
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()

    if len(result) != 1:
        raise ValueError(f"Expected result of length 1, found {result}")
    return result[0][0]


def add_question_and_correct_answer(
    game_id: int, question_number: int, question: str, correct_answer: str
) -> None:
    query = f"""
    UPDATE {Tables.questions}
    SET {Var.question} = ${Var.question},
    {Var.correct_answer} = ${Var.correct_answer}
    WHERE {Var.game_id} = ${Var.game_id} AND {Var.question_number} = ${Var.question_number};
    """

    variables = {
        str(Var.question): question,
        str(Var.correct_answer): correct_answer,
        str(Var.game_id): game_id,
        str(Var.question_number): question_number,
    }
    print("Query: ", query)
    print("Variables: ", variables)

    with get_cursor() as con:
        con.execute(query, variables)


def determine_n_human_players(game_id: int) -> int:
    query = f"""
    SELECT COUNT(*) FROM {Tables.game_player} 
    JOIN {Tables.players}
    ON {Tables.game_player}.{Var.player_id} = {Tables.players}.{Var.player_id}
    WHERE {Tables.game_player}.{Var.game_id} = {game_id} 
    AND {Tables.players}.{Var.is_house} = FALSE;
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()

    if len(result) != 1:
        raise ValueError(f"Expected result of length 1, found {result}")
    return result[0][0]


def determine_whether_all_answers_in(game_id: int, question_number: int) -> bool:
    query = f"""
    SELECT 
    COUNT(*) FROM {Tables.player_answers}
    JOIN {Tables.players} ON {Tables.player_answers}.{Var.player_id} = {Tables.players}.{Var.player_id}
    WHERE {Tables.player_answers}.{Var.game_id} = {game_id} 
    AND {Tables.player_answers}.{Var.question_number} = {question_number} 
    AND {Tables.players}.{Var.is_house} = FALSE 
    AND {Tables.player_answers}.{Var.answer_text} IS NULL;
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()

    if len(result) != 1:
        raise ValueError(f"Expected result of length 1, found {result}")

    print("result of determine_whether_all_answers_in: ", result)
    return result[0][0] == 0


def next_question(game_id: int, question_number: int) -> None:
    set_is_answered(game_id=game_id, question_number=question_number)
    set_game_state(game_id=game_id, game_stage=GameStage.answer_writing)


@dataclasses.dataclass
class PlayerAnswerTuple:
    player_id: str
    answer_text: str
    answer_order: float


def get_player_answer_tuples(
    game_id: int, question_number: int
) -> list[PlayerAnswerTuple]:
    query = f"""
    SELECT {Var.player_id}, {Var.answer_text}, {Var.answer_order} FROM {Tables.player_answers}
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number};
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()
    return [PlayerAnswerTuple(*res) for res in result if res[1] is not None]


def set_player_answer(
    game_id: int,
    player_id: str,
    question_number=int,
) -> None:
    player_answer = st.session_state[Var.answer_text]
    if player_answer is None:
        raise ValueError("Player answer is None.")

    if player_answer == "":
        st.error("Answer cannot be empty. Please write your answer.")

    query = f"""
    UPDATE {Tables.player_answers} SET {Var.answer_text} = ${Var.answer_text}
    WHERE {Var.game_id} = ${Var.game_id} AND {Var.player_id} = ${Var.player_id} AND {Var.question_number} = ${Var.question_number};
    """

    variables = {
        str(Var.answer_text): player_answer,
        str(Var.game_id): game_id,
        str(Var.player_id): player_id,
        str(Var.question_number): question_number,
    }

    with get_cursor() as con:
        con.execute(query, variables)


def add_fake_answers(
    game_id: int, question_number: int, fake_answers: list[str | None]
) -> None:
    if any(a is None for a in fake_answers):
        raise ValueError(
            "Fake answers are still None. This should not have happened. Something is wrong."
        )

    variables = {}
    items = []
    for i, f_answer in enumerate(fake_answers):
        variable_name = f"fake_answer_{i}"
        variables[variable_name] = f_answer
        items.append(
            f"({game_id}, {question_number}, '{get_house_player_id(i)}', ${variable_name})"
        )

    item_rows = ",\n".join(items)
    query = f"""
    INSERT INTO {Tables.player_answers} ({Var.game_id}, {Var.question_number}, {Var.player_id}, {Var.answer_text}) VALUES
    {item_rows}
    ON CONFLICT ({Var.game_id}, {Var.question_number}, {Var.player_id}) 
    DO UPDATE SET {Var.answer_text} = EXCLUDED.{Var.answer_text};
    """
    print("add_fake_answers: ", query)
    print("variables: ", variables)
    with get_cursor() as con:
        con.execute(query, variables)


def get_correct_answer_rank(game_id: int, question_number: int) -> float:
    query = f"""
    SELECT {Var.correct_answer_rank} FROM {Tables.questions}
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number};
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()
    if len(result) != 1:
        raise ValueError(f"Expected result of length 1, found {result}")

    return result[0][0]


def get_player_id_who_wrote_chosen_answer(
    game_id: int, question_number: int, player_id: str
) -> str | None:
    query = f"""
    SELECT {Var.player_id_of_chosen_answer} FROM {Tables.player_answers}
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number} AND {Var.player_id} = '{player_id}';
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()
    if len(result) != 1:
        raise ValueError(f"Expected result of length 1, found {result}")

    return result[0][0]


def set_players_chosen_answers_player_id(
    game_id: int, question_number: int, player_id: str, chosen_player_id: str
) -> None:
    """
    We track which answer was chosen by the player's id who wrote the answer.
    """
    if player_id == chosen_player_id:
        st.toast("You cannot choose your own answer.")

    else:
        query = f"""
        UPDATE {Tables.player_answers}
        SET {Var.player_id_of_chosen_answer} = '{chosen_player_id}'
        WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number} AND {Var.player_id} = '{player_id}';
        """
        print("set_players_chosen_answers_player_id: ", query)
        with get_cursor() as con:
            con.execute(query)


@st.fragment(run_every=1)
def rerun_if_game_stage_changed(game_id: int, current_stage: GameStage) -> None:
    actual_stage = determine_game_stage(game_id)
    if actual_stage != current_stage:
        st.rerun()


@st.fragment(run_every=1)
def rerun_if_game_stage_changed_or_all_answers_in(
    game_id: int,
    current_stage: GameStage,
    question_number: int,
    all_answers_in_already_before: bool,
) -> None:
    actual_stage = determine_game_stage(game_id)
    if actual_stage != current_stage:
        st.rerun()

    if not all_answers_in_already_before:
        all_answers_in = determine_whether_all_answers_in(
            game_id=game_id, question_number=question_number
        )
        if all_answers_in:
            st.rerun()


@st.fragment(run_every=1)
def rerun_if_game_stage_or_players_changed(
    game_id: int, current_players: list[str], current_stage: GameStage
) -> None:
    actual_stage = determine_game_stage(game_id)
    if actual_stage != current_stage:
        st.rerun()

    actual_players = get_all_players_in_game(game_id)
    if set(actual_players) != set(current_players):
        st.rerun()


@st.fragment(run_every=1)
def auto_refresh(count_down: list[int] = [10]) -> None:
    if count_down[0] <= 0:
        print("Auto-refreshing...")
        st.rerun()
    else:
        count_down[0] -= 1
        st.caption(f"Auto-refresh in {count_down[0]} seconds.")


@st.fragment(run_every=1)
def rerun_if_all_players_have_chosen_an_answer(
    game_id: int, question_number: int, is_host: bool
) -> None:
    have_chosen = all_players_have_chosen_an_answer(
        game_id=game_id, question_number=question_number
    )
    print("is_answered: ", have_chosen)
    if have_chosen:
        if is_host:
            print("Setting game stage to reveal")
            set_game_state(game_id=game_id, game_stage=GameStage.reveal)

        st.rerun()


def question_is_answered(game_id: int, question_number: int) -> bool:
    query = f"""
    SELECT {Var.is_answered} FROM {Tables.questions}
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number};
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()
    if len(result) != 1:
        raise ValueError(f"Expected result of length 1, found {result}")

    return result[0][0]


@st.fragment(run_every=1)
def rerun_if_question_is_answered(game_id: int, question_number: int) -> None:
    is_answered = question_is_answered(game_id=game_id, question_number=question_number)
    if is_answered:
        st.rerun()


def all_players_have_chosen_an_answer(game_id: int, question_number: int) -> bool:
    query = f"""
    SELECT {Var.player_id_of_chosen_answer} FROM {Tables.player_answers}
    JOIN {Tables.players} ON {Tables.player_answers}.{Var.player_id} = {Tables.players}.{Var.player_id}
    WHERE {Tables.player_answers}.{Var.game_id} = {game_id} AND {Tables.player_answers}.{Var.question_number} = {question_number} 
    AND {Tables.players}.{Var.is_house} = FALSE;
    """
    print("rerun_if_question_is_answered, query:", query)

    with get_cursor() as con:
        result = con.execute(query).fetchall()
    return not any(res[0] is None for res in result)


def change_name_field(player_id: str, player_name: str) -> None:
    st.text_input(
        label="Your name",
        value=player_name,
        max_chars=MAX_NAME_LENGTH,
        help="Choose how other players see you.",
        key=Var.player_name,
        on_change=lambda: set_player_name(
            player_id=player_id, player_name=st.session_state[Var.player_name]
        ),
    )


def player_name_display(player_id: str) -> None:
    player_name = get_player_name(player_id=player_id)
    st.badge(player_name, icon=":material/person:")


def leave_if_not_in_game(player_id: str, game_id: int, all_players: list[str]) -> None:
    if player_id not in all_players:
        leave_game(player_id=player_id, game_id=game_id)
        st.info("You were removed from the game.")
        st.rerun()


def sql_editor_sidebar() -> None:
    with st.sidebar:
        unsafe_sql = st.text_area(
            "SQL",
        )
        execute_sql_button = st.button("Execute SQL")
        print(unsafe_sql)
        if execute_sql_button and unsafe_sql:
            with get_cursor() as con:
                result = con.execute(unsafe_sql).fetchall()
            st.write(result)


def has_accepted_cookies() -> bool:
    has_accepted_cookies = st.session_state.get(Var.has_accepted_cookies, False)
    if not has_accepted_cookies:
        cookie_controller = stx.CookieManager(key="cookie_allow_manager")  # key needs to be different from the one authenticator uses
        has_accepted_cookies = cookie_controller.get(str(Var.has_accepted_cookies))
    return bool(has_accepted_cookies)


def accept_cookies() -> None:
    cookie_controller = stx.CookieManager(key="cookie_allow_manager2")  # key needs to be different from the one authenticator uses
    cookie_controller.set(str(Var.has_accepted_cookies), True)
    st.session_state[Var.has_accepted_cookies] = True


@st.dialog("Please accept cookies")
def show_cookies_consent() -> None:
    st.checkbox(
        "Accept essential cookies", on_change=accept_cookies
    )


def main():
    if not has_accepted_cookies():
        show_cookies_consent()
    
    else:

        if st.session_state.get(Var.name) == "Admin":
            sql_editor_sidebar()

        create_tables_if_not_exist()

        player_id = determine_player_id()
        game_id = determine_game_id()
        if game_id is not None:
            leave_if_not_in_game(
                player_id=player_id,
                game_id=game_id,
                all_players=get_all_players_in_game(game_id=game_id),
            )

        game_stage = determine_game_stage(game_id)
        if game_stage is None:
            st.info("The game was closed by the host.")
            leave_game(player_id=player_id, game_id=game_id)

        if game_stage == GameStage.no_game_selected:
            find_game_screen(player_id=player_id)

        else:
            is_host = is_player_host(player_id=player_id, game_id=game_id)

            if game_stage == GameStage.game_open:
                open_game_screen(player_id=player_id, game_id=game_id, is_host=is_host)

            elif game_stage == GameStage.finished:
                finished_screen(player_id=player_id, game_id=game_id, is_host=is_host)

            else:
                st.button("Leave Game", on_click=lambda: leave_game(player_id=player_id, game_id=game_id))
                question_number = determine_first_unanswered_question_number(
                    game_id=game_id
                )
                print(f"question_number: {question_number}")

                if question_number is None:
                    print("All questions answered.")
                    set_game_state(game_id=game_id, game_stage=GameStage.finished)
                    st.rerun()

                st.text(f"Question number: {question_number}/{N_QUESTIONS}")

                match game_stage:
                    case GameStage.answer_writing:
                        answer_writing_screen(
                            player_id=player_id,
                            game_id=game_id,
                            is_host=is_host,
                            question_number=question_number,
                        )
                    case GameStage.guessing:
                        guessing_screen(
                            player_id=player_id,
                            game_id=game_id,
                            is_host=is_host,
                            question_number=question_number,
                        )

                    case GameStage.reveal:
                        reveal_screen(
                            player_id=player_id,
                            game_id=game_id,
                            is_host=is_host,
                            question_number=question_number,
                        )

                    case unreachable:
                        raise ValueError(f"Found {unreachable}")


def find_game_screen(player_id: str) -> None:
    player_name = get_player_name(player_id=player_id)
    st.title("Welcome to 'Who knew it?' with Chat Stewart")
    change_name_field(player_id=player_id, player_name=player_name)
    open_game_ids = get_all_opened_games()

    st.header("You can")
    st.button(
        "Create new game",
        on_click=partial(create_and_join_new_game, player_id=player_id),
        type="primary",
    )

    st.header("or join an open game.")

    st.divider()

    st.header("Open games:")

    if not open_game_ids:
        st.text("There are no open games. But you can create a new one!")
    else:
        for open_game in open_game_ids:
            col_game_name, col_players, col_how_many_free = st.columns([0.2, 0.7, 0.1])
            all_players_in_game = get_all_players_in_game(game_id=open_game)
            with col_game_name:
                st.button(
                    f"Join game {open_game}",
                    on_click=partial(
                        join_game, player_id=player_id, game_id=open_game, is_host=False
                    ),
                    disabled=len(all_players_in_game) >= N_MAX_PLAYERS,
                    type="primary",
                )
            with col_players:
                player_display_list = [
                    f":blue-badge[:material/person: {player}]"
                    for player in all_players_in_game.values()
                ]
                
                st.markdown(" ".join(player_display_list))
            
            with col_how_many_free:
                color = "green" if len(all_players_in_game) < N_MAX_PLAYERS else "red"
                st.markdown(f":{color}[{len(all_players_in_game)}/{N_MAX_PLAYERS}]")

    st.divider()
    st.button("Refresh")
    auto_refresh()



def player_display_markdown(player_id: str, current_player_id: str, player_name:str) -> str:
    color = get_display_color(some_player_id=player_id, current_player_id=current_player_id)
    badge_icon = get_badge_icon(some_player_id=player_id)
    return f":{color}-badge[{badge_icon} {player_name}]"


def open_game_screen(player_id: str, game_id: int, is_host: bool) -> None:
    player_name = get_player_name(player_id=player_id)
    st.title(f"You have joined game {game_id}")
    change_name_field(player_id=player_id, player_name=player_name)
    st.text(f"You are {'not ' if not is_host else ''}the host.")
    
    all_players = get_all_players_in_game(game_id=game_id)
    leave_if_not_in_game(
        player_id=player_id,
        game_id=game_id,
        all_players=list(all_players.keys()),
    )
    print(all_players)

    st.header(f"Players ({len(all_players)}/{N_MAX_PLAYERS}):")
    for p_id, p_name in all_players.items():
        cols = st.columns(2)
        with cols[0]:
            st.markdown(
                player_display_markdown(
                    player_id=p_id,
                    current_player_id=player_id,
                    player_name=p_name,
                )
            )
        if is_host and p_id != player_id:
            with cols[1]:
                st.button(
                    "Kick",
                    key=f"{p_id}_kick",
                    on_click=partial(kick_from_game, game_id=game_id, player_id=p_id),
                )

    cols = st.columns(3)
    with cols[0]:
        st.button(
            "Leave Game",
            on_click=partial(leave_game, game_id=game_id, player_id=player_id),
        )
    with cols[2]:
        st.button(
            "Start Game" if is_host else "Wait for host to start game",
            on_click=partial(start_game, game_id=game_id, n_questions=N_QUESTIONS),
            disabled=not is_host,
            type="primary",
        )
    rerun_if_game_stage_or_players_changed(
        game_id=game_id,
        current_players=list(all_players.keys()),
        current_stage=GameStage.game_open,
    )



def get_question_generator(question_number: int) -> questions.QuestionGenerator:
    rest = question_number % 6

    if rest == 0:  # question number is 1 indexed so should be last
        return movie_suggestion.MovieQuestionGenerator()
    
    elif rest == 1:
        return animal_question.AnimalQuestionGenerator()
    elif rest == 2:
        return word_definition_question.OldEnglishWordDefinitionQuestionGenerator()
    elif rest == 3:
        return arxiv_question.ArxivQuestionGenerator()
    elif rest == 4:
        return pokemon_question.PokemonQuestionGenerator()

    elif rest == 5:
        return podcast_question.PodcastQuestionGenerator()

    else:
        raise ValueError(f"Found {rest}")



def answer_writing_screen(
    player_id: str, game_id: int, is_host: bool, question_number: int
) -> None:
    player_name_display(player_id=player_id)
    with st.popover("Instructions", icon=":material/help:"):
        st.header("Welcome to 'Who knew it?' with Chat Stewart")
        st.text("The game where the players write the wrong answer.")
        st.text("I am the titular Chat Stewart and I ask a relatively obscure trivia question and the players have to write a convincing fake answer.")
        st.text("I then show the correct answer as well as the fake answers and the players need to guess which one is correct.")

    question = get_question(game_id=game_id, question_number=question_number)


    if question is None:
        with st.spinner("Generating Question..."):
            if is_host:
                print("Generating Question since I am host")
                question_object = (
                    get_question_generator(question_number).generate_question_and_correct_answer()
                )
                add_question_and_correct_answer(
                    game_id=game_id,
                    question_number=question_number,
                    question=question_object.question_text(),
                    correct_answer=question_object.get_correct_answer(),
                )
                question = get_question(
                    game_id=game_id, question_number=question_number
                )
            else:
                print("Waiting for host to generate question")
                while question is None:
                    time.sleep(1)
                    question = get_question(
                        game_id=game_id, question_number=question_number
                    )

    if determine_n_human_players(game_id=game_id) > 1:


        st.header("Please write a convincing fake answer for the following question:")
        st.title(question)
        st.text_area(
            label="Your fake answer:",
            key=Var.answer_text,
            on_change=partial(
                set_player_answer,
                game_id=game_id,
                player_id=player_id,
                question_number=question_number,
            ),
        )

        all_answers_in = determine_whether_all_answers_in(
            game_id=game_id, question_number=question_number
        )

        st.button(
            "Finish writing answers" if is_host else "Wait for host to continue",
            on_click=lambda: set_game_state(game_id=game_id, game_stage=GameStage.guessing),
            disabled=not all_answers_in or not is_host,
            type="primary",
            help="Only the host can finish writing answers if all answers are in.",
        )
        rerun_if_game_stage_changed_or_all_answers_in(
            game_id=game_id,
            current_stage=GameStage.answer_writing,
            question_number=question_number,
            all_answers_in_already_before=all_answers_in,
        )

    else:
        set_game_state(game_id=game_id, game_stage=GameStage.guessing)
        st.rerun()


def guessing_screen(
    player_id: str, game_id: int, is_host: bool, question_number: int
) -> None:
    question = get_question(game_id=game_id, question_number=question_number)

    if question is None:
        raise ValueError(
            "Question is None. This should not have happened. Something is wrong."
        )
    player_name_display(player_id=player_id)

    with st.popover("Instructions", icon=":material/help:"):
        st.header("Now you need to choose which answer is correct.")
        st.text("Each player gets one point if they choose the correct answer and another for each player that chooses their fake answer.")
        st.text("By the way I am also playing as 'The House' and I have put in 2 fake answers with the help of a Large Language Model. I will score one point for each player that chooses my fake answer.")
        st.text("So we can all score one point per player in the game. Seems fair, but the probability actually favors me, 'The House', and 'The House' always wins.")
    
    st.title(question)
    st.header("Here are your options. Which one do you think is correct?")

    combined_synopsis = get_correct_answer(
        game_id=game_id, question_number=question_number
    )
    if combined_synopsis is None:
        raise ValueError(
            "combined_synopsis is None. This should not have happened. Something is wrong."
        )

    fake_answers = get_all_fake_answers(
        game_id=game_id, question_number=question_number
    )

    if any(a is None for a in fake_answers):
        n_fake_answers = len(fake_answers)

        with st.spinner("Writing the wrong answers..."):
            if is_host:
                fake_answers = get_question_generator(question_number).write_fake_answers(  # type: ignore
                    question=question,
                    correct_answer=combined_synopsis,
                    n_fake_answers=n_fake_answers,
                )

                add_fake_answers(
                    game_id=game_id,
                    question_number=question_number,
                    fake_answers=fake_answers,
                )
            else:
                while any(a is None for a in fake_answers):
                    time.sleep(1)
                    fake_answers = get_all_fake_answers(
                        game_id=game_id, question_number=question_number
                    )

    player_answer_tuples = get_player_answer_tuples(
        game_id=game_id, question_number=question_number
    )
    correct_answer_rank = get_correct_answer_rank(
        game_id=game_id, question_number=question_number
    )

    player_answer_tuples += [
        PlayerAnswerTuple(CORRECT_ANSWER_ID, combined_synopsis, correct_answer_rank)
    ]
    player_answer_tuples = sorted(player_answer_tuples, key=lambda x: x.answer_order)

    button_labels = get_button_labels(len(player_answer_tuples))

    player_answer = get_player_id_who_wrote_chosen_answer(
        player_id=player_id, game_id=game_id, question_number=question_number
    )
    player_has_chosen = player_answer is not None

    st.divider()
    for label, answer_tuple in zip(button_labels, player_answer_tuples, strict=True):
        letter_col, text_col = st.columns([0.2, 0.8])
        if player_answer == answer_tuple.player_id:
            icon = ":material/radio_button_checked:"
        else:
            icon = ":material/radio_button_unchecked:"

        with letter_col:
            st.button(
                label=f"{label}",
                icon=icon,
                disabled=player_has_chosen,
                on_click=partial(
                    set_players_chosen_answers_player_id,
                    game_id=game_id,
                    player_id=player_id,
                    question_number=question_number,
                    chosen_player_id=answer_tuple.player_id,
                ),
            )
        with text_col:
            st.text(answer_tuple.answer_text)

    rerun_if_all_players_have_chosen_an_answer(
        game_id=game_id, question_number=question_number, is_host=is_host
    )


def get_players_who_chose_answers(
    game_id: int, question_number: int
) -> dict[str, list[str]]:
    query = f"""
    SELECT {Var.player_id_of_chosen_answer}, LIST({Var.player_id}) AS {Var.fooled_players} FROM {Tables.player_answers}
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number} AND {Var.player_id_of_chosen_answer} IS NOT NULL
    GROUP BY {Var.player_id_of_chosen_answer}
    """
    print("get_reveal_info_from_player_answers: ", query)
    with get_cursor() as con:
        result = con.execute(query).fetchall()
    print("get_reveal_info_from_player_answers: ", result)
    return {res[0]: res[1] for res in result}


@dataclasses.dataclass
class RevealInfo:
    player_id_of_author: str
    answer_text: str
    player_ids_who_chose: list[str]


def is_house_player_id(player_id: str) -> bool:
    return player_id.startswith(HOUSE_PLAYER_ID_PREFIX)


def aggregate_house_points(player_points: dict[str, int]) -> dict[str, int]:
    player_points = player_points.copy()
    house_ids = [
        player_id
        for player_id in player_points.keys()
        if is_house_player_id(player_id)
    ]
    if not house_ids:
        return player_points

    if not get_house_player_id(0) in player_points:
        raise ValueError("House player 0 is not in player_points")

    house_sum = sum(player_points[h_id] for h_id in house_ids)
    for h_id in house_ids:
        del player_points[h_id]

    player_points[get_house_player_id(0)] = house_sum
    return player_points


def calculate_player_points(reveal_infos: list[RevealInfo], triple_points: bool) -> dict[str, int]:

    players_who_participated = {
        *{ri.player_id_of_author for ri in reveal_infos},
        *{player_id for ri in reveal_infos for player_id in ri.player_ids_who_chose},
    }

    player_points = {
        player_id: 0 for player_id in players_who_participated if player_id != CORRECT_ANSWER_ID
    }

    for ri in reveal_infos:
        if ri.player_id_of_author != CORRECT_ANSWER_ID:
            player_points[ri.player_id_of_author] += len(ri.player_ids_who_chose)

    [correct_answer_info] = [
        ri for ri in reveal_infos if ri.player_id_of_author == CORRECT_ANSWER_ID
    ]
    for player_id in correct_answer_info.player_ids_who_chose:
        player_points[player_id] += 1

    if triple_points:
        house_ids = [
            player_id
            for player_id in player_points.keys()
            if is_house_player_id(player_id)
        ]
        for player_id in player_points.keys():
            if player_id not in house_ids:
                player_points[player_id] *= 3

    return player_points


def get_total_points(game_id: int) -> dict[str, int]:
    query = f"""
    SELECT {Var.player_id}, SUM({Var.points}) FROM {Tables.points}
    WHERE {Var.game_id} = {game_id}
    GROUP BY {Var.player_id};
    """
    print("get_total_points: ", query)
    with get_cursor() as con:
        result = con.execute(query).fetchall()
    return {res[0]: res[1] for res in result}


def points_entered(game_id: int, question_number: int) -> bool:
    query = f"""
    SELECT COUNT(*) FROM {Tables.points}
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number};
    """
    print("points_entered: ", query)
    with get_cursor() as con:
        result = con.execute(query).fetchall()
    return result[0][0] > 0


def get_display_color(some_player_id: str, current_player_id: str) -> str:
    if some_player_id == current_player_id:
        return "blue"
    elif some_player_id == CORRECT_ANSWER_ID:
        return "green"
    elif is_house_player_id(some_player_id):
        return "orange"
    else:
        return "violet"


def get_badge_icon(some_player_id: str) -> str:
    if some_player_id == CORRECT_ANSWER_ID:
        return ":material/check:"
    elif is_house_player_id(some_player_id):
        return ":material/house:"
    else:
        return ":material/person:"



def reveal_screen(
    player_id: str, game_id: int, is_host: bool, question_number: int
) -> None:
    player_name_display(player_id=player_id)

    players_who_chose_answers = get_players_who_chose_answers(
        game_id=game_id, question_number=question_number
    )

    question = get_question(game_id=game_id, question_number=question_number)

    if question is None:
        raise ValueError(
            "Question is None. This should not have happened. Something is wrong."
        )
    with st.popover("Instructions", icon=":material/help:"):
        st.header("The answers are in for this question.")
        st.text("Now I will reveal who wrote the answers and which one is correct.")
        st.text("Each player gets one point if they choose the correct answer and another for each player that chooses their fake answer.")
        st.text("By the way I am also playing as 'The House' and I have put in 2 fake answers with the help of a Large Language Model. I will score one point for each player that chooses my fake answer.")
    
    st.title(f"Reveal for question {question_number}")
    if question_number == N_QUESTIONS:
        st.header("This round is worth triple points for the players!")
    st.header(f"What's the correct answer for: {question}")

    st.divider()

    player_answer_tuples = get_player_answer_tuples(
        game_id=game_id, question_number=question_number
    )
    correct_answer = get_correct_answer(
        game_id=game_id, question_number=question_number
    )
    if correct_answer is None:
        raise ValueError(
            "Correct answer is None. This should not have happened. Something is wrong."
        )
    reveal_infos = [
        RevealInfo(
            player_id_of_author=answer_tuple.player_id,
            answer_text=answer_tuple.answer_text,
            player_ids_who_chose=players_who_chose_answers.get(
                answer_tuple.player_id, []
            ),
        )
        for answer_tuple in player_answer_tuples
    ]
    reveal_infos = sorted(reveal_infos, key=lambda x: len(x.player_ids_who_chose))

    reveal_infos += [
        RevealInfo(
            player_id_of_author=CORRECT_ANSWER_ID,
            answer_text=correct_answer,
            player_ids_who_chose=players_who_chose_answers.get(CORRECT_ANSWER_ID, []),
        )
    ]
    player_id_to_name = get_all_players_in_game(game_id=game_id)
    player_id_to_name[CORRECT_ANSWER_ID] = CORRECT_ANSWER_NAME

    for r_info in reveal_infos:

        fooled_players = r_info.player_ids_who_chose
        
        if fooled_players:
            player_display_list = []
            for player in fooled_players:

                color = get_display_color(some_player_id=player, current_player_id=player_id)
                badge_icon = get_badge_icon(some_player_id=player)
                player_display_list.append(
                    f":{color}-badge[{badge_icon} {player_id_to_name[player]}]"
                )
            above_answer_text = " ".join(player_display_list) + " guessed"
        else:
            above_answer_text = ":gray-badge[Noone] guessed"
        st.markdown(
            above_answer_text
        )
        expander_visible = abbreviate_text(
                    r_info.answer_text, DISPLAY_LENGTH_LIMIT_TO_EXPANDER
                )
        with st.expander(label=expander_visible):
            st.text(r_info.answer_text)
        
        color = get_display_color(r_info.player_id_of_author, current_player_id=player_id)
        badge_icon = get_badge_icon(some_player_id=r_info.player_id_of_author)

        is_correct_answer = r_info.player_id_of_author == CORRECT_ANSWER_ID

        verb = "is the" if is_correct_answer else "was written by"
        st.markdown(f"which {verb} :{color}-badge[{badge_icon} {player_id_to_name[r_info.player_id_of_author]}]")

        st.divider()

    player_points = calculate_player_points(reveal_infos=reveal_infos, triple_points=question_number == N_QUESTIONS)
    if is_host:
        add_points(
            game_id=game_id,
            question_number=question_number,
            points_per_player_id=player_points,
        )
    else:
        while not points_entered(game_id=game_id, question_number=question_number):
            time.sleep(1)
    total_points = get_total_points(game_id=game_id)
    player_points = aggregate_house_points(player_points=player_points)
    total_points = aggregate_house_points(player_points=total_points)
    
    st.header("Points:")
    cols = st.columns(len(player_points))
    sorted_player_points_tuples = sorted(
        player_points.items(), key=lambda x: x[1], reverse=True
    )
    
    for col, (player, points) in zip(cols, sorted_player_points_tuples, strict=True):
        with col:
            st.metric(
                label=player_id_to_name[player],
                value=total_points[player],
                delta=points,
            )


    if is_host:
        button_text = "Next question" if question_number < N_QUESTIONS else "Finish game"
    else:
        button_text = "wait for host to continue"

    st.button(
        button_text,
        type="primary",
        on_click=partial(
            next_question, game_id=game_id, question_number=question_number
        ),
        disabled=not is_host,
    )
    rerun_if_game_stage_changed(game_id=game_id, current_stage=GameStage.reveal)


def abbreviate_text(text: str, width: int) -> str:
    wrapped_chunks = textwrap.wrap(
        text,
        width=width,
        expand_tabs=False,
        replace_whitespace=False,
        drop_whitespace=False,
    )
    abbreviated = wrapped_chunks[0]
    if len(wrapped_chunks) > 1:
        abbreviated += "..."
    return abbreviated


def get_winner_s(total_points: dict[str, int]) -> list[str]:
    max_points = max(total_points.values())
    return [player for player, points in total_points.items() if points == max_points]


def finished_screen(player_id: str, game_id: int, is_host: bool) -> None:
    st.title("Finished!")
    player_id_to_name = get_all_players_in_game(game_id=game_id)
    total_points = aggregate_house_points(get_total_points(game_id=game_id))
    cols = st.columns(len(total_points))
    sorted_player_points_tuples = sorted(
        total_points.items(), key=lambda x: x[1], reverse=True
    )

    for col, (player, points) in zip(cols, sorted_player_points_tuples, strict=True):
        with col:
            st.metric(label=player_id_to_name[player], value=points)
    player_name = get_player_name(player_id=player_id)
    winners = get_winner_s(total_points=total_points)

    if player_id in winners:
        st.balloons()
        qualifier = (
            f" together with {' '.join(player_id_to_name[w] for w in winners)}"
            if len(winners) > 1
            else ""
        )

        st.header(f"Congratulations {player_name}! You won the game{qualifier}!")
    else:
        verb = "has" if len(winners) == 1 else "have"
        st.header(
            f"{' '.join(player_id_to_name[w] for w in winners)} {verb} won the game."
        )

    st.button(
        "Next game",
        type="primary",
        on_click=partial(leave_game, game_id=game_id, player_id=player_id),
    )


if __name__ == "__main__":
    auth = authenticator.get_authenticator()
    if st.session_state.get('authentication_status'):
        with st.sidebar:
            auth.logout()
        main()
    else:
        auth.login()
        if st.session_state.get('authentication_status') is False:
            st.error('Username/password is incorrect')
        elif st.session_state.get('authentication_status') is None:
            st.warning('Please enter your username and password')
