from typing import List, Optional

polish_to_english = str.maketrans(
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
    "acelnoszzACELNOSZZ"
)


def change_column_names(columns: List[str]) -> List[str]:
    changed = list()
    for col in columns:
        col = col.translate(polish_to_english)
        col = col.strip()
        col = col.replace(" ", "_")
        col = col.replace(".", "")
        col = col.lower()
        changed.append(col)

    return changed

