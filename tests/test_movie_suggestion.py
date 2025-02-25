import pathlib
import random
import time

import imdb  # type: ignore


def test_get_year():
    ia = imdb.Cinemagoer()

    film_suggestion = "The Matrix"
    search_movie = ia.search_movie(film_suggestion)
    movie = ia.get_movie(search_movie[0].movieID)
    year = movie.data["year"]
    breakpoint()
    assert isinstance(year, int)

def test_get_bottom():
    ia = imdb.Cinemagoer()

    bottom_movies = ia.get_top250_movies()
    infos = []
    for movie in bottom_movies:
        infos.append(
            {
                "title": movie.data["title"],
                "year": movie.data["year"],
                "plot": movie.data["plot"],
            }
        )

    assert len(bottom_movies) == 100
    breakpoint()


def test_try_random_id():
    ia = imdb.Cinemagoer()
    movies = []
    for _ in range(10):
        while True:
            random_id = "0" + "".join((str(random.randint(0, 9)) for _ in range(6)))
            try:
                movie = ia.get_movie(random_id)
            except imdb.IMDbError:
                print("didn't find: ", random_id)
                continue
            if movie is not None:
                print("found: ", random_id)
                if (
                    "plot" in movie.data 
                    and movie.data["plot"]
                    and movie.data.get("votes", 0) < 10000
                    and movie.data["year"]
                    and not "episode" in movie.data["title"].lower()
                    and movie.data.get("kind") == "movie"
                    ):
                    break
                else:
                    print("skipped: ", random_id)

        movies.append(movie)

    assert len(movies) == 10
    for movie in movies:
        print(movie.data["title"], movie.data["year"])
    
    breakpoint()


def get_random_word():
    word_file = pathlib.Path(__file__).parent.parent / "who_knew_it" / "words.txt"

    with open(word_file) as f:
        words = f.read().splitlines()

    return random.choice(words)


def test_try_random_via_search():
    start =time.time()
    ia = imdb.Cinemagoer()

    limit = 1
    movies = []


    while len(movies) < limit:
        random_word = get_random_word()
        print("random word: ", random_word)
        try:
            searched_movie_list = ia.search_movie(random_word, results=10)
        except imdb.IMDbError:
            continue

        print("searched took: ", time.time() - start)

        for searched_movie in searched_movie_list:
            movie = ia.get_movie(searched_movie.movieID)
            if not movie.data.get("plot"):
                print("unsuitable: ", movie.data["title"], "no plot")

            elif not movie.data.get("votes", 0) < 100000:
                print("unsuitable: ", movie.data["title"], "too many votes")
                
            elif not movie.data["year"]:
                print("unsuitable: ", movie.data["title"], "no year")
                
            elif "episode" in movie.data["title"].lower():
                print("unsuitable: ", movie.data["title"], "episode")

            elif not movie.data.get("kind") == "movie":
                print("unsuitable: ", movie.data["title"], "not a movie")
                
            else:
                movies.append(movie)
                if len(movies) == limit:
                    break
    print("time: ", time.time() - start)
    for m in movies:
        print(m.data["title"], m.data["year"])
