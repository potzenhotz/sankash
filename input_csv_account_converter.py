import polars as pl
import typer
from pathlib import Path
from typing_extensions import Annotated
from enum import Enum

app = typer.Typer(
    help="Convert bank CSV exports to Actual Budget format",
    invoke_without_command=True,
    no_args_is_help=True,
)


class BankFormat(str, Enum):
    """Supported bank formats"""

    deutsche_bank = "deutsche-bank"
    ing = "ing"


def convert_deutsche_bank_to_actual(input_file: Path, output_file: Path):
    """
    Converts Deutsche Bank CSV export to Actual Budget format.

    Args:
        input_file: Path to Deutsche Bank CSV file
        output_file: Path for output file
    """

    # Read CSV - Deutsche Bank uses semicolon as separator
    df = pl.read_csv(
        input_file,
        separator=";",
        decimal_comma=True,  # Deutsche Bank uses comma as decimal separator
        encoding="utf-8",
    )

    # Rename columns and select only relevant ones
    df_actual = df.select(
        [
            pl.col("Buchungstag").alias("Date"),
            pl.col("Begünstigter / Auftraggeber").alias("Payee"),
            pl.col("Verwendungszweck").alias("Notes"),
            pl.col("Betrag").alias("Amount"),
        ]
    )

    # Filter out summary rows (like "Kontostand") - keep only rows with valid date format
    # Valid dates match DD.MM.YYYY pattern
    df_actual = df_actual.filter(
        pl.col("Date").str.contains(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
    )

    # Remove empty rows (if any)
    df_actual = df_actual.filter(
        pl.col("Date").is_not_null() & pl.col("Amount").is_not_null()
    )

    # Convert date to ISO format (DD.MM.YYYY -> YYYY-MM-DD)
    df_actual = df_actual.with_columns(
        [pl.col("Date").str.strptime(pl.Date, "%d.%m.%Y").dt.strftime("%Y-%m-%d")]
    )

    # Convert amount to float (Actual Budget expects dot as decimal separator)
    # Polars should have read this correctly with decimal_comma=True, but ensure it's float type
    df_actual = df_actual.with_columns([pl.col("Amount").cast(pl.Float64)])

    # Replace empty payees with "Unknown"
    df_actual = df_actual.with_columns(
        [
            pl.when(pl.col("Payee").is_null() | (pl.col("Payee") == ""))
            .then(pl.lit("Unknown"))
            .otherwise(pl.col("Payee"))
            .alias("Payee")
        ]
    )

    # Notes can be empty, but we replace NULL with empty string
    df_actual = df_actual.with_columns([pl.col("Notes").fill_null("")])

    # Sort by date (oldest first)
    df_actual = df_actual.sort("Date")

    # Export as CSV (with dot as decimal separator for Actual Budget)
    df_actual.write_csv(output_file, separator=",", float_precision=2)

    typer.echo(
        typer.style("✅ Conversion successful!", fg=typer.colors.GREEN, bold=True)
    )
    typer.echo(f"📊 {len(df_actual)} transactions converted")
    typer.echo(f"💾 Saved to: {output_file}")
    typer.echo(f"\n📋 First 5 rows:")
    typer.echo(df_actual.head(5))

    # Statistics
    typer.echo(typer.style("\n📈 Statistics:", fg=typer.colors.CYAN, bold=True))
    typer.echo(f"Date range: {df_actual['Date'].min()} to {df_actual['Date'].max()}")

    income = df_actual.filter(pl.col("Amount") > 0)["Amount"].sum()
    expenses = df_actual.filter(pl.col("Amount") < 0)["Amount"].sum()

    typer.echo(
        f"Total income: {typer.style(f'{income:.2f} EUR', fg=typer.colors.GREEN)}"
    )
    typer.echo(
        f"Total expenses: {typer.style(f'{expenses:.2f} EUR', fg=typer.colors.RED)}"
    )
    typer.echo(
        f"Net: {typer.style(f'{(income + expenses):.2f} EUR', fg=typer.colors.YELLOW)}"
    )

    return df_actual


def convert_ing_to_actual(input_file: Path, output_file: Path):
    """
    Converts ING CSV export to Actual Budget format.

    Args:
        input_file: Path to ING CSV file
        output_file: Path for output file
    """

    # Read CSV - ING uses semicolon as separator and has metadata rows at the top
    # Skip the first 13 rows (metadata and header info)
    # ING exports use ISO-8859-1/Latin-1 encoding
    df = pl.read_csv(
        input_file,
        separator=";",
        skip_rows=13,  # Skip metadata rows
        encoding="iso-8859-1",
    )

    # Rename columns and select only relevant ones
    # ING columns: Buchung, Wertstellungsdatum, Auftraggeber/Empfänger, Buchungstext, Verwendungszweck, Saldo, Währung, Betrag, Währung
    df_actual = df.select(
        [
            pl.col("Buchung").alias("Date"),
            pl.col("Auftraggeber/Empfänger").alias("Payee"),
            # Combine Buchungstext and Verwendungszweck for Notes
            (pl.col("Buchungstext") + " - " + pl.col("Verwendungszweck")).alias("Notes"),
            pl.col("Betrag").alias("Amount"),
        ]
    )

    # Filter out summary rows - keep only rows with valid date format
    # Valid dates match DD.MM.YYYY pattern
    df_actual = df_actual.filter(
        pl.col("Date").str.contains(r"^\d{1,2}\.\d{1,2}\.\d{4}$")
    )

    # Remove empty rows (if any)
    df_actual = df_actual.filter(
        pl.col("Date").is_not_null() & pl.col("Amount").is_not_null()
    )

    # Convert date to ISO format (DD.MM.YYYY -> YYYY-MM-DD)
    df_actual = df_actual.with_columns(
        [pl.col("Date").str.strptime(pl.Date, "%d.%m.%Y").dt.strftime("%Y-%m-%d")]
    )

    # Convert amount to float - handle German number format
    # ING uses comma as decimal separator and dot as thousands separator
    # e.g., "1.234,56" -> "1234.56"
    df_actual = df_actual.with_columns([
        pl.col("Amount")
        .str.replace_all(r"\.", "")  # Remove thousands separator (dots)
        .str.replace(",", ".")  # Replace decimal comma with dot
        .cast(pl.Float64)
    ])

    # Replace empty payees with "Unknown"
    df_actual = df_actual.with_columns(
        [
            pl.when(pl.col("Payee").is_null() | (pl.col("Payee") == ""))
            .then(pl.lit("Unknown"))
            .otherwise(pl.col("Payee"))
            .alias("Payee")
        ]
    )

    # Notes can be empty, but we replace NULL with empty string
    df_actual = df_actual.with_columns([pl.col("Notes").fill_null("")])

    # Sort by date (oldest first)
    df_actual = df_actual.sort("Date")

    # Export as CSV (with dot as decimal separator for Actual Budget)
    df_actual.write_csv(output_file, separator=",", float_precision=2)

    typer.echo(
        typer.style("✅ Conversion successful!", fg=typer.colors.GREEN, bold=True)
    )
    typer.echo(f"📊 {len(df_actual)} transactions converted")
    typer.echo(f"💾 Saved to: {output_file}")
    typer.echo(f"\n📋 First 5 rows:")
    typer.echo(df_actual.head(5))

    # Statistics
    typer.echo(typer.style("\n📈 Statistics:", fg=typer.colors.CYAN, bold=True))
    typer.echo(f"Date range: {df_actual['Date'].min()} to {df_actual['Date'].max()}")

    income = df_actual.filter(pl.col("Amount") > 0)["Amount"].sum()
    expenses = df_actual.filter(pl.col("Amount") < 0)["Amount"].sum()

    typer.echo(
        f"Total income: {typer.style(f'{income:.2f} EUR', fg=typer.colors.GREEN)}"
    )
    typer.echo(
        f"Total expenses: {typer.style(f'{expenses:.2f} EUR', fg=typer.colors.RED)}"
    )
    typer.echo(
        f"Net: {typer.style(f'{(income + expenses):.2f} EUR', fg=typer.colors.YELLOW)}"
    )

    return df_actual


@app.callback()
def convert(
    input_file: Annotated[
        Path,
        typer.Option(
            "-i",
            "--input",
            help="Path to bank CSV export file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    format: Annotated[
        BankFormat,
        typer.Option(
            "-f",
            "--format",
            help="Bank format to convert from",
            case_sensitive=False,
        ),
    ] = BankFormat.deutsche_bank,
    output_file: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output",
            help="Path for output file (defaults to <bank>_<start_date>_to_<end_date>.csv)",
        ),
    ] = None,
):
    """
    Convert bank CSV exports to Actual Budget format.

    Example:
        uv run main.py -i export.csv -f deutsche-bank

        uv run main.py -i export.csv -f deutsche-bank -o my_output.csv
    """

    typer.echo(f"🏦 Converting {format.value} CSV...")
    typer.echo(f"📁 Input: {input_file}")

    try:
        # First, convert the data
        if format == BankFormat.deutsche_bank:
            df_result = convert_deutsche_bank_to_actual(input_file, Path("temp.csv"))
        elif format == BankFormat.ing:
            df_result = convert_ing_to_actual(input_file, Path("temp.csv"))
        else:
            typer.echo(
                typer.style(
                    f"❌ Format '{format.value}' not yet implemented",
                    fg=typer.colors.RED,
                ),
                err=True,
            )
            raise typer.Exit(code=1)

        # Generate default output filename if not provided
        if output_file is None:
            min_date = df_result['Date'].min()
            max_date = df_result['Date'].max()
            bank_name = format.value.replace("-", "_")
            output_file = Path(f"{bank_name}_{min_date}_to_{max_date}.csv")

        typer.echo(f"📁 Output: {output_file}\n")

        # Write to the actual output file
        df_result.write_csv(output_file, separator=",", float_precision=2)

        # Clean up temp file
        Path("temp.csv").unlink(missing_ok=True)

    except Exception as e:
        typer.echo(
            typer.style(f"❌ Error: {str(e)}", fg=typer.colors.RED, bold=True), err=True
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
