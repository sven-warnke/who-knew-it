import time
import streamlit as st
import enum
from who_knew_it import fake_answer
from who_knew_it import answers
import random
from who_knew_it import movie_suggestion
import duckdb
import uuid
from pathlib import Path
from functools import partial

DEFAULT_N_FAKE_ANSWERS = 2
MAX_N_FAKE_ANSWERS = 4
N_MAX_PLAYERS = 5

DB_FILE = Path(__file__).parent.parent / "database" / "file.db"

HOUSE_PLAYER_ID_PREFIX = "house"
CORRECT_ANSWER = "correct_answer"


class Tables(enum.StrEnum):
    players = "players"
    games = "games"
    game_player = "game_player"
    questions = "questions"
    player_answers = "player_answers"


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


class GameStage(enum.IntEnum):
    no_game_selected = 0
    game_open = 1
    answer_writing = 2
    guessing = 3
    finished = 4


def get_house_player_id(i: int) -> str:
    return f"{HOUSE_PLAYER_ID_PREFIX}_{i}"


@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(DB_FILE)


def get_cursor() -> duckdb.DuckDBPyConnection:
    return get_db_connection().cursor()


@st.cache_resource
def create_tables_if_not_exist() -> None:
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
                ('{get_house_player_id(0)}', '{get_house_player_id(0)}', TRUE),
                ('{get_house_player_id(1)}', '{get_house_player_id(1)}', TRUE),
                ('{get_house_player_id(2)}', '{get_house_player_id(2)}', TRUE),
                ('{get_house_player_id(3)}', '{get_house_player_id(3)}', TRUE),
                ('{get_house_player_id(4)}', '{get_house_player_id(4)}', TRUE),
                ('{get_house_player_id(5)}', '{get_house_player_id(5)}', TRUE)
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
            PRIMARY KEY ({Var.game_id}, {Var.question_number}, {Var.player_id}),
            FOREIGN KEY ({Var.game_id}) REFERENCES {Tables.games}({Var.game_id}),
            FOREIGN KEY ({Var.player_id}) REFERENCES {Tables.players}({Var.player_id}),
        );
        """,
        f"""
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


def get_all_opened_games() -> list[int]:
    query = f"""
    SELECT {Var.game_id} FROM {Tables.games}
    WHERE {Var.game_stage} = {GameStage.game_open};
    """

    with get_cursor() as con:
        result = con.execute(query).fetchall()

    return [res[0] for res in result]


def get_all_players_in_game(game_id: int) -> list[str]:
    query = f"""
    SELECT {Var.player_id} FROM {Tables.game_player}
    WHERE {Var.game_id} = {game_id};
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()

    return [res[0] for res in result]


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


def _n_players_in_game_query(game_id: int) -> str:
    return f"""
    SELECT COUNT(*) FROM {Tables.game_player} WHERE {Var.game_id} = {game_id}
    """


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
        st.session_state[Var.game_id] = game_id
        print(f"{player_id} joined game {game_id}.")


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


def get_player_answer_tuples(
    game_id: int, question_number: int
) -> list[tuple[str, str, float]]:
    query = f"""
    SELECT {Var.player_id}, {Var.answer_text}, {Var.answer_order} FROM {Tables.player_answers}
    WHERE {Var.game_id} = {game_id} AND {Var.question_number} = {question_number};
    """
    with get_cursor() as con:
        result = con.execute(query).fetchall()
    return result


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


@st.fragment(run_every=30)
def auto_refresh():
    st.rerun()


def main():
    create_tables_if_not_exist()

    player_id = determine_player_id()
    game_id = determine_game_id()

    game_stage = determine_game_stage(game_id)

    if game_stage == GameStage.no_game_selected:
        find_game_screen(player_id=player_id)

    else:
        is_host = is_player_host(player_id=player_id, game_id=game_id)

        match game_stage:
            case GameStage.game_open:
                open_game_screen(player_id=player_id, game_id=game_id, is_host=is_host)
            case GameStage.answer_writing:
                answer_writing_screen(
                    player_id=player_id, game_id=game_id, is_host=is_host
                )
            case GameStage.guessing:
                guessing_screen(player_id=player_id, game_id=game_id, is_host=is_host)
            case GameStage.finished:
                finished_screen(player_id=player_id, game_id=game_id, is_host=is_host)
            case unreachable:
                raise ValueError(f"Found {unreachable}")


def find_game_screen(player_id: str) -> None:
    st.title("Welcome to 'Who knew it?' with Chat Stewart")
    st.text(f"Hello {player_id}")

    open_game_ids = get_all_opened_games()

    st.header("Select a game!")
    st.button(
        "Create new game",
        on_click=partial(create_and_join_new_game, player_id=player_id),
    )

    if not open_game_ids:
        st.text("There are no open games. But you can create a new one!")
    else:
        for open_game in open_game_ids:
            col_game_name, col_players, col_how_many_free = st.columns([0.2, 0.7, 0.1])
            all_players_in_game = get_all_players_in_game(game_id=open_game)
            with col_game_name:
                st.button(
                    f"{open_game}",
                    on_click=partial(
                        join_game, player_id=player_id, game_id=open_game, is_host=False
                    ),
                    disabled=len(all_players_in_game) >= N_MAX_PLAYERS,
                )
            with col_players:
                for player in all_players_in_game:
                    st.text(player)
            with col_how_many_free:
                color = "green" if len(all_players_in_game) < N_MAX_PLAYERS else "red"
                st.markdown(f":{color}[{len(all_players_in_game)}/{N_MAX_PLAYERS}]")

    st.button("Refresh")
    # auto_refresh()  # Seems to cause reruns between screens


def open_game_screen(player_id: str, game_id: int, is_host: bool) -> None:
    st.title(f"This is your game. {game_id}")
    st.text(f"You are {'not ' if not is_host else ''} the host.")
    st.text(f"Hello {player_id}")
    st.header("Players:")
    all_players = get_all_players_in_game(game_id=game_id)
    if not player_id in all_players:
        st.error(
            "Seems like you are not in the game. How do you see it then? This should not have happened."
        )
    print(all_players)

    for player in all_players:
        st.text(player)

    st.button(
        "Start Game",
        on_click=partial(start_game, game_id=game_id, n_questions=6),
        disabled=not is_host,
    )
    rerun_if_game_stage_or_players_changed(
        game_id=game_id, current_players=all_players, current_stage=GameStage.game_open
    )


def answer_writing_screen(player_id: str, game_id: int, is_host: bool) -> None:
    question_number = determine_first_unanswered_question_number(game_id=game_id)
    print(f"question_number: {question_number}")
    if not question_number:
        print("All questions answered.")
        set_game_state(game_id=game_id, game_stage=GameStage.finished)
        st.rerun()

    question = get_question(game_id=game_id, question_number=question_number)

    if question is None:
        with st.spinner("Generating Question..."):
            if is_host:
                print("Generating Question since I am host")
                retrieved_title, combined_synopsis = (
                    movie_suggestion.select_film_and_generate_synopsis()
                )
                add_question_and_correct_answer(
                    game_id=game_id,
                    question_number=question_number,
                    question=retrieved_title,
                    correct_answer=combined_synopsis,
                )
                question = retrieved_title
            else:
                print("Waiting for host to generate question")
                while question is None:
                    time.sleep(1)
                    question = get_question(
                        game_id=game_id, question_number=question_number
                    )

    st.title(question)
    st.text_area(
        label="Your answer:",
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
        "Next",
        on_click=lambda: set_game_state(game_id=game_id, game_stage=GameStage.guessing),
        disabled=not all_answers_in or not is_host,
    )
    rerun_if_game_stage_changed_or_all_answers_in(
        game_id=game_id,
        current_stage=GameStage.answer_writing,
        question_number=question_number,
        all_answers_in_already_before=all_answers_in,
    )


def guessing_screen(player_id: str, game_id: int, is_host: bool) -> None:
    question_number = determine_first_unanswered_question_number(game_id=game_id)
    if not question_number:
        print("All questions answered.")
        set_game_state(game_id=game_id, game_stage=GameStage.finished)
        st.rerun()

    question = get_question(game_id=game_id, question_number=question_number)

    if question is None:
        raise ValueError(
            "Question is None. This should not have happened. Something is wrong."
        )
    st.title(question)
    st.header("Here are your options. Which one do you think is correct?")

    retrieved_title = question
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
                fake_answers = []
                for _ in range(n_fake_answers):
                    fake_answer_text = fake_answer.create_fake_movie_synopsis(
                        info_about_film=retrieved_title,
                        avoid_examples=[combined_synopsis],
                    )
                    fake_answers.append(fake_answer_text)

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

    player_answer_tuples += [(CORRECT_ANSWER, combined_synopsis, correct_answer_rank)]
    player_answer_tuples = sorted(player_answer_tuples, key=lambda x: x[2])
    st.header(f"What's the plot of the film {retrieved_title}?")

    answer_list = [i[1] for i in player_answer_tuples]

    button_labels = get_button_labels(len(answer_list))

    button_outputs = []
    for label, an_answer in zip(button_labels, answer_list, strict=True):
        letter_col, text_col = st.columns([0.2, 0.8], border=True)
        with letter_col:
            b_output = st.button(
                label=f"{label}", disabled=False, on_click=set_is_answered
            )
            button_outputs.append(b_output)
        with text_col:
            st.text(an_answer)

    # initialize_points_if_not_exist()

    # if any(button_outputs):
    #     [choice] = [i for i, b in enumerate(button_outputs) if b]

    #     [correct_answer] = [i for i, a in enumerate(answer_list) if a.correct]

    #     if choice == correct_answer:
    #         st.text("Correct")
    #         increase_points()
    #     else:
    #         st.text("False!")
    #         st.text(f"The correct answer was {button_labels[correct_answer]}.")

    # st.metric(label="Points", value=st.session_state[Var.points])
    # st.button("Next", on_click=reset_question_state)


def finished_screen(player_id: str, game_id: int, is_host: bool) -> None:
    st.title("Finished!")


if __name__ == "__main__":
    main()
