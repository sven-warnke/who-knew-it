import requests

from who_knew_it import api_call, questions, random_word


class PodcastQuestion(questions.Question):
    def __init__(self, podcast_title: str, genre: str):
        self.podcast_title = podcast_title
        self.genre = genre

    def get_correct_answer(self) -> str:
        return self.podcast_title

    def question_text(self) -> str:
        return f"What's a real title of a {self.genre} podcast?"


class PodcastQuestionGenerator(questions.QuestionGenerator):
    def get_random_podcasts(self) -> list[PodcastQuestion]:
        suitable_podcasts: list[PodcastQuestion] = []

        while len(suitable_podcasts) < 20:

            a_word = random_word.get_random_word()
            itunes_search_url = "https://itunes.apple.com/search?"
            query = f"term={a_word}&limit=30&entity=podcast"
            print(query)

            response = requests.get(itunes_search_url + query)
            json_response = response.json()
            
            for result in json_response["results"]:
                if "collectionName" not in result:
                    print("no collection name")
                    continue

                if "primaryGenreName" not in result:
                    print("no genre name")
                    continue

                suitable_podcasts.append(
                    PodcastQuestion(
                        podcast_title=result["collectionName"],
                        genre=result["primaryGenreName"],
                    )
                )
        return suitable_podcasts[:20]

    def generate_question_and_correct_answer(self) -> PodcastQuestion:

        while True:
            candidate_podcasts = self.get_random_podcasts()

            candidates_str ="\n\n".join([f"{i}:'{result.podcast_title}', {result.genre}" for i, result in enumerate(candidate_podcasts)])

            prompt = f"""
            From the list of the following podcast titles and genres, please choose one that sounds amusing, absurd or funny to a native English speaker.
            Prefer titles that contain puns or jokes. Please only select a title that is in English and not from another language.

            {candidates_str}

            Please answer only with its number as written above and nothing else.
            """

            print(prompt)
            result = api_call.prompt_model(prompt=prompt)

            try:
                result_number = int(result.strip())
                
            except ValueError:
                print("No fitting candidate found for response: ", result_number)
                print("Candidates: ", candidate_podcasts)
                continue

            if 0 <= result_number < len(candidate_podcasts):
                return candidate_podcasts[result_number]


    def write_fake_answers(self, question: str, correct_answer: str, n_fake_answers: int) -> list[str]:
        del correct_answer  # not needed here

        while True:
            starting_letter_clause = f"The first podcast should start with an '{random_word.random_letter()}'."  # to add more randomness
            if n_fake_answers > 1:
                starting_letter_clause += f" The second podcast should start with an '{random_word.random_letter()}'."
            
            for i in range(2, n_fake_answers):
                starting_letter_clause += f" The {i + 1}. podcast should start with an '{random_word.random_letter()}'."

            prompt = f"""
            You are playing a game where you have to write convincing and fun fake answers, that could trick people into picking it. Please invent fitting podcast titles
            that fit the following question: "{question}".
            Please write {n_fake_answers} fake podcast titles and nothing else in a list separated by newlines. Ideally, the podcast title is a bit quirky or funny.
            {starting_letter_clause}
            Please answer only with that list and nothing else.
            """
            print(prompt)
            response = api_call.prompt_model(prompt=prompt)

            split_response = response.split("\n")

            fake_answers = [r.replace("*", "").strip() for r in split_response if r.strip()]

            if len(fake_answers) == n_fake_answers:
                return fake_answers
