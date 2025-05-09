import pathlib

folder = pathlib.Path(__file__).parent
for file in folder.iterdir():
    print(file)

    if not file.name.endswith(".txt"):
        continue
    with open(file, "r") as f:
        lines = f.readlines()
    
    with open(file.with_suffix(".csv"), "w") as f:
        for line in lines:
            split_by_equal = line.split("=", 1)
            if len(split_by_equal) != 2:
                continue
            nick_name_part, name_part = split_by_equal
            nick_name = nick_name_part.split(",", 1)[0].strip()
            name = name_part.split(",", 1)[0].strip()

            nick_name = nick_name.replace('"', "").replace("'", "").strip()
            if nick_name and name:
                f.write(f"{nick_name}, {name}\n")
        
    print()