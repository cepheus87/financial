from typing import List, Optional
import pandas as pd

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


def process_financial_gain_loss_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    #TODO: trzeba te z % przerobic na %, inne na float
    #Kwartał, Okres -> str
    #Data publikacji -> datetime

    df["Rok"] = df["Rok"].astype(int)

    return df

