import os

def get_file_path(filename: str) -> str:
    return os.path.join(os.getcwd(), filename)

with open(get_file_path("texts/topics.txt"), "r", encoding="utf-8") as file:
    topics = file.read()
    print(topics)