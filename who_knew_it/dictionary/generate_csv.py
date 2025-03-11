import pathlib

text_file = pathlib.Path(__file__).parent / "old-english-nouns.txt"


def main():
    with open(text_file) as f:
        lines = f.read().splitlines()

    with open(text_file.parent / "nouns.csv", "w") as f:
        old_english = None
        noun = None
        definition = None
        for line in lines:
            line = line.rstrip()
            if line:
                if old_english is None:
                    if line.startswith("Old English"):
                        old_english = line
                elif noun is None:
                    if "," in line:
                        noun = line.split(",", 1)[0]
                elif definition is None:
                    definition = line
                else:
                    old_english = None
                    noun = None
                    definition = None
            else:
                if old_english and noun and definition:
                    f.write(f"{noun}|{definition}\n")


if __name__ == "__main__":
    main()
