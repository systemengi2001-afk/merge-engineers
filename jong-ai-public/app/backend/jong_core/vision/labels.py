CANONICAL = [
    *[f"{n}m" for n in range(1,10)], "0m",
    *[f"{n}p" for n in range(1,10)], "0p",
    *[f"{n}s" for n in range(1,10)], "0s",
    *[f"{n}z" for n in range(1,8)],
    "UNKNOWN",
]

ALIASES = {
    "east": "1z", "south": "2z", "west": "3z", "north": "4z",
    "white": "5z", "green": "6z", "red": "7z",
    "haku": "5z", "hatsu": "6z", "chun": "7z",
}

def normalize_label(label: str) -> str:
    raw = label.strip().lower().replace(" ", "")
    if raw in ALIASES:
        return ALIASES[raw]
    valid = {x.lower(): x for x in CANONICAL}
    if raw in valid:
        return valid[raw]
    for suit in "mps":
        if raw in {f"red5{suit}", f"5{suit}r", f"aka5{suit}", f"red_{suit}"}:
            return f"0{suit}"
    return "UNKNOWN"
