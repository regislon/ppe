# PPE Project Overview

## Purpose
Electricity billing system for a multi-unit building. Downloads meter readings from Google Sheets, computes per-flat costs, and generates PDF bills with QR payment slips.

## Tech Stack
- Python 3.12+, managed with `uv`
- reportlab for PDF generation
- qrbill + svglib for QR payment slips
- gspread + google-auth for Google Sheets access
- pandas for data processing
- ruff for formatting/linting, mypy for type checking

## Key Files
- `main.py` - Entry point, orchestrates download → compute → billing
- `billing.py` - PDF bill generation (build_bill_pdf, generate_all_bills)
- `monthly_building_electricity.py` - Computes building-level monthly costs
- `monthly_flats_electricity.py` - Computes per-flat monthly consumption
- `monthly_electricity_cost.py` - Computes cost distribution across meters
- `download_google_sheet.py` - Downloads data from Google Sheets
- `config.json` - Creditor, persons, IBAN, sheet URL

## Commands
- Run: `uv run python main.py`
- Format: `uv run ruff format <files>`
- Lint: `uv run ruff check --fix <files>`
- Type check: `uv run mypy --ignore-missing-imports --follow-imports=silent --disable-error-code=import-untyped --disable-error-code=attr-defined --disable-error-code=arg-type --disable-error-code=return-value --disable-error-code=assignment <files>`

## Style
- French language in UI/PDF output
- Type hints used but not enforced strictly
- No docstring convention enforced beyond what exists
