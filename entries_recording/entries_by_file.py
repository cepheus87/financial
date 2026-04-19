# TODO: dorobic wczytywanie pliku, ktory liczy dodatkowy kurs na podstawie full price - uzyc record_entry oraz
#  przerabia deposit na wartosc w price_in_currency

import argparse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

TRANSACTION_COLUMNS = [
    "Konto",
    "Data",
    "Ticker",
    "Waluta",
    "Nazwa",
    "Klasa aktywów",
    "Rodzaj transakcji",
    "Liczba",
    "Cena",
    "Prowizje",
    "Kurs PLN transakcji",
    "Cena nominalna",
    "Total PLN",
    "Klucz",
    "XIRR",
    "Komentarz",
]

TYPE_TO_TRANSACTION = {
    "buy": "Zakup",
    "sell": "Sprzedaż",
    "div": "Dywidenda / Odsetki",
    "dividend": "Dywidenda / Odsetki",
    "deposit": "Wpłata środków",
    "withdraw": "Wypłata środków",
}

CASH_TRANSACTION_TYPES = {"deposit", "withdraw"}

REQUIRED_SINGLE_ENTRY_ARGS = [
    "date",
    "account",
    "type",
    "name",
    "units",
    "price_in_currency",
    "currency",
]

INPUT_REQUIRED_COLUMNS = [
    "date",
    "account",
    "type",
    "name",
    "units",
    "price_in_currency",
    "currency",
]


def _is_blank_or_dash(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text == "-" or text.lower() == "nan"


def _normalize_asset_name(value: str) -> str:
    """Normalize ticker/name for matching (e.g. FRA:ASWC -> ASWC)."""
    if value is None:
        return ""
    raw = str(value).strip().upper()
    return raw.split(":", 1)[1] if ":" in raw else raw


def _to_decimal(value: Any) -> Decimal:
    if value is None:
        raise ValueError("Nie można sparsować wartości liczbowej: None")
    if isinstance(value, str):
        value = value.replace("\xa0", "").replace(" ", "").replace(",", ".")
        if value == "":
            raise ValueError("Nie można sparsować pustej wartości liczbowej.")
    return Decimal(str(value))


def _format_decimal(value: Decimal, places: int) -> str:
    quant = Decimal("1") if places == 0 else Decimal("1." + "0" * places)
    rounded = value.quantize(quant, rounding=ROUND_HALF_UP)
    return f"{rounded:.{places}f}".replace(".", ",")


def _format_pln(value: Decimal) -> str:
    rounded = value.quantize(Decimal("1.00"), rounding=ROUND_HALF_UP)
    formatted = f"{rounded:,.2f}".replace(",", " ").replace(".", ",")
    return f"{formatted} zł"


def _resolve_asset_row(portfolio_df: pd.DataFrame, account: str, name: str) -> pd.Series:
    account_mask = portfolio_df["Konto"].astype(str).str.strip().str.lower() == account.strip().lower()
    account_df = portfolio_df[account_mask].copy()

    if account_df.empty:
        raise ValueError(f"Nie znaleziono konta '{account}' w pliku Portfolio.")

    needle = _normalize_asset_name(name)

    ticker_full = account_df["Ticker"].fillna("").astype(str).str.strip().str.upper()
    ticker_short = ticker_full.map(_normalize_asset_name)
    name_short = account_df["Nazwa"].fillna("").astype(str).map(_normalize_asset_name)

    match_mask = (ticker_full == needle) | (ticker_short == needle) | (name_short == needle)
    matches = account_df[match_mask]

    if matches.empty:
        raise ValueError(
            f"Nie znaleziono aktywa '{name}' dla konta '{account}'. "
            "Dopasowanie odbywa się po tickerze (z/bez prefiksu giełdy) oraz nazwie aktywa."
        )

    if len(matches) > 1:
        tickers = ", ".join(str(ticker) for ticker in matches["Ticker"].fillna("<brak>").tolist())
        raise ValueError(
            f"Niejednoznaczne dopasowanie aktywa '{name}' dla konta '{account}'. "
            f"Pasujące tickery: {tickers}"
        )

    return matches.iloc[0]


def _build_transaction_row(
    portfolio_df: pd.DataFrame,
    date: str,
    account: str,
    transaction_type_raw: str,
    name: str,
    units_raw: Any,
    price_in_currency_raw: Any,
    currency: str,
    fx_rate_raw: Any = 1.0,
    commission_raw: Any = 0.0,
    comment: str = "",
) -> Dict[str, str]:
    normalized_comment = "" if _is_blank_or_dash(comment) else str(comment)

    transaction_type_key = str(transaction_type_raw).strip().lower()
    transaction_type = TYPE_TO_TRANSACTION.get(transaction_type_key)
    if transaction_type is None:
        supported = ", ".join(sorted(TYPE_TO_TRANSACTION))
        raise ValueError(
            f"Nieobsługiwany typ transakcji '{transaction_type_raw}'. Obsługiwane: {supported}"
        )

    requested_currency = str(currency).strip().upper()
    fx_rate = _to_decimal(fx_rate_raw)
    commission = _to_decimal(commission_raw)

    if transaction_type_key in CASH_TRANSACTION_TYPES:
        amount = _to_decimal(price_in_currency_raw)
        total_pln = amount * fx_rate + commission
        xirr_value = -total_pln if transaction_type_key == "deposit" else total_pln

        return {
            "Konto": str(account),
            "Data": str(date),
            "Ticker": "Gotówka",
            "Waluta": requested_currency,
            "Nazwa": "Gotówka",
            "Klasa aktywów": "Gotówka",
            "Rodzaj transakcji": transaction_type,
            "Liczba": "1,0",
            "Cena": "1,0000",
            "Prowizje": _format_decimal(commission, 2),
            "Kurs PLN transakcji": _format_decimal(fx_rate, 2),
            "Cena nominalna": "1,00",
            "Total PLN": _format_pln(total_pln),
            "Klucz": f"{account}##Gotówka##Gotówka##{requested_currency}",
            "XIRR": _format_decimal(xirr_value, 2),
            "Komentarz": normalized_comment,
        }

    asset_row = _resolve_asset_row(portfolio_df, account, name)
    portfolio_currency = str(asset_row["Waluta"]).strip().upper()
    if portfolio_currency != requested_currency:
        raise ValueError(
            f"Waluta z argumentu ('{requested_currency}') nie zgadza się z Portfolio ('{portfolio_currency}') "
            f"dla aktywa '{asset_row['Ticker']}'."
        )

    units = _to_decimal(units_raw)
    price = _to_decimal(price_in_currency_raw)
    total_pln = units * price * fx_rate + commission

    return {
        "Konto": str(account),
        "Data": str(date),
        "Ticker": str(asset_row["Ticker"]),
        "Waluta": requested_currency,
        "Nazwa": str(asset_row["Nazwa"]),
        "Klasa aktywów": str(asset_row["Klasa aktywów"]),
        "Rodzaj transakcji": transaction_type,
        "Liczba": _format_decimal(units, 1),
        "Cena": _format_decimal(price, 4),
        "Prowizje": _format_decimal(commission, 2),
        "Kurs PLN transakcji": _format_decimal(fx_rate, 2),
        "Cena nominalna": "1,00",
        "Total PLN": _format_pln(total_pln),
        "Klucz": f"{account}##{asset_row['Ticker']}##{asset_row['Klasa aktywów']}##{requested_currency}",
        "XIRR": "0",
        "Komentarz": normalized_comment,
    }


def build_transaction_entry(args: argparse.Namespace) -> pd.DataFrame:
    portfolio_df = pd.read_csv(args.portfolio_path)
    entry = _build_transaction_row(
        portfolio_df=portfolio_df,
        date=args.date,
        account=args.account,
        transaction_type_raw=args.type,
        name=args.name,
        units_raw=args.units,
        price_in_currency_raw=args.price_in_currency,
        currency=args.currency,
        fx_rate_raw=args.fx_rate,
        commission_raw=args.commission,
        comment=args.comment,
    )
    return pd.DataFrame([entry], columns=TRANSACTION_COLUMNS)


def build_transaction_entries_from_file(args: argparse.Namespace) -> pd.DataFrame:
    portfolio_df = pd.read_csv(args.portfolio_path)
    input_df = pd.read_csv(args.input_path, dtype=str)

    missing_columns = [col for col in INPUT_REQUIRED_COLUMNS if col not in input_df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Brak wymaganych kolumn w pliku wejściowym: {missing}")

    rows: List[Dict[str, str]] = []
    for line_no, (_, row) in enumerate(input_df.iterrows(), start=2):
        try:
            rows.append(
                _build_transaction_row(
                    portfolio_df=portfolio_df,
                    date=row["date"],
                    account=row["account"],
                    transaction_type_raw=row["type"],
                    name="" if _is_blank_or_dash(row["name"]) else row["name"],
                    units_raw="1" if _is_blank_or_dash(row["units"]) else row["units"],
                    price_in_currency_raw=row["price_in_currency"],
                    currency=row["currency"],
                    fx_rate_raw=row.get("fx_rate", "1,0"),
                    commission_raw=row.get("commission", "0,00"),
                    comment=row.get("comment", ""),
                )
            )
        except Exception as exc:
            raise ValueError(f"Błąd w wierszu {line_no} pliku wejściowego: {exc}") from exc

    return pd.DataFrame(rows, columns=TRANSACTION_COLUMNS)


def write_entries_to_file(entry_df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    entry_df.to_csv(output_path, index=False)


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    portfolio_path = Path(args.portfolio_path)
    if not portfolio_path.exists():
        parser.error(f"Plik Portfolio nie istnieje: {args.portfolio_path}")

    if args.input_path:
        input_path = Path(args.input_path)
        if not input_path.exists():
            parser.error(f"Plik wejściowy nie istnieje: {args.input_path}")
    else:
        transaction_type_key = str(args.type).strip().lower() if args.type else ""
        required_fields = ["date", "account", "type", "price_in_currency", "currency"]
        if transaction_type_key not in CASH_TRANSACTION_TYPES:
            required_fields.extend(["name", "units"])

        missing = [arg for arg in required_fields if _is_blank_or_dash(getattr(args, arg))]
        if missing:
            parser.error(
                "Podaj --input-path albo komplet argumentów CLI: " + ", ".join(missing)
            )

    if args.output_mode == "file" and not args.output_path:
        parser.error("Dla --output-mode file wymagane jest --output-path")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generuje wpis do pliku Transakcje na podstawie Portfolio i parametrów wejściowych."
        )
    )

    parser.add_argument("--portfolio-path", required=True, help="Ścieżka do pliku Portfolio.csv")
    parser.add_argument("--input-path", help="Ścieżka do pliku CSV z wieloma wpisami wejściowymi")

    parser.add_argument("--date", help="Data transakcji, np. 2025-09-01")
    parser.add_argument("--account", help="Nazwa konta, np. ike")
    parser.add_argument("--type", help="Typ transakcji, np. buy")
    parser.add_argument(
        "--name",
        help="Nazwa/ticker aktywa bez prefiksu giełdy, np. ASB albo VWRD",
    )
    parser.add_argument("--units", help="Liczba jednostek")
    parser.add_argument(
        "--price-in-currency",
        dest="price_in_currency",
        help="Cena jednostki w walucie aktywa",
    )
    parser.add_argument("--currency", help="Waluta aktywa, np. PLN/USD/EUR")

    parser.add_argument(
        "--fx-rate",
        default="1,0",
        help="Kurs PLN transakcji (domyślnie 1.0)",
    )
    parser.add_argument(
        "--commission",
        default="0,00",
        help="Prowizja w PLN (domyślnie 0.0)",
    )
    parser.add_argument(
        "--comment",
        default="",
        help="Komentarz do wpisu (opcjonalnie)",
    )
    parser.add_argument(
        "--output-mode",
        choices=["print", "file"],
        default="print",
        help="Czy wynik wypisać na ekran (print), czy zapisać do pliku (file)",
    )
    parser.add_argument(
        "--output-path",
        default="",
        help="Ścieżka do nowego pliku CSV (używana przy --output-mode file).",
    )

    args = parser.parse_args()
    _validate_args(parser, args)
    return args


def main() -> None:
    args = parse_args()
    if args.input_path:
        entry_df = build_transaction_entries_from_file(args)
    else:
        entry_df = build_transaction_entry(args)

    if args.output_mode == "file":
        write_entries_to_file(entry_df, Path(args.output_path))
        print(f"Zapisano {len(entry_df)} wpis(ów) do pliku: {args.output_path}")
        return

    print(entry_df.to_csv(index=False))


if __name__ == "__main__":
    main()

