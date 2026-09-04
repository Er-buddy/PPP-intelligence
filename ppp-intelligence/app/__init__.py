import logging

root = logging.getLogger()
for handler in list(root.handlers):
    root.removeHandler(handler)

root.setLevel(logging.INFO)

file_handler = logging.FileHandler("log.txt", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
root.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
root.addHandler(console_handler)
