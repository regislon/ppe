import os
import tempfile
import unicodedata

import pandas as pd
from qrbill import QRBill
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from svglib.svglib import svg2rlg

MONTH_NAMES_FR = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}

METER_LABELS_FR = {
    "kwh_building": "Commun (bâtiment)",
    "kwh_0": "Rez inférieur",
    "kwh_1": "Rez supérieur",
    "kwh_2": "1er étage",
    "kwh_fridge": "Congélateur",
}

CONSUMERS = ["kwh_building", "kwh_0", "kwh_1", "kwh_2", "kwh_fridge"]

BLUE_HEADER = colors.HexColor("#4472C4")
LIGHT_BLUE = colors.HexColor("#D9E2F3")


def validate_config(config: dict) -> None:
    """Check shares sum to 100, IBAN present, required fields exist."""
    if not config.get("IBAN"):
        raise ValueError("IBAN is required in config")

    if not config.get("creditor"):
        raise ValueError("creditor is required in config")

    for field in ["name", "street", "house_num", "pcode", "city", "country"]:
        if not config["creditor"].get(field):
            raise ValueError(f"creditor.{field} is required")

    building_total = sum(p["building_share"] for p in config["persons"])
    fridge_total = sum(p["fridge_share"] for p in config["persons"])

    if building_total != 100:
        raise ValueError(f"building_share values sum to {building_total}, expected 100")
    if fridge_total != 100:
        raise ValueError(f"fridge_share values sum to {fridge_total}, expected 100")


def compute_person_bill(person: dict, cost_row: pd.Series) -> dict:
    """Compute flat_cost + building share + fridge share for one person/month."""
    flat_amount = 0.0
    flat_cost_key = person.get("flat_cost")
    if flat_cost_key:
        flat_amount = float(cost_row[flat_cost_key])

    building_amount = float(cost_row["cost_building"]) * person["building_share"] / 100
    fridge_amount = float(cost_row["cost_fridge"]) * person["fridge_share"] / 100

    total = flat_amount + building_amount + fridge_amount

    return {
        "flat_amount": round(flat_amount, 2),
        "building_amount": round(building_amount, 2),
        "fridge_amount": round(fridge_amount, 2),
        "total": round(total, 2),
    }


def format_month_year_fr(month_year: str) -> str:
    """'2026-01' -> 'Janvier 2026'."""
    year, month = month_year.split("-")
    return f"{MONTH_NAMES_FR[int(month)]} {year}"


def generate_bill_filename(person_name: str, month_year: str) -> str:
    """Generate normalized filename like 'facture_2026-01_diane_longchamp.pdf'."""
    name = unicodedata.normalize("NFKD", person_name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().replace(" ", "_").replace("-", "_")
    name = "".join(c for c in name if c.isalnum() or c == "_")
    return f"facture_{month_year}_{name}.pdf"


def generate_qr_bill_drawing(
    config: dict, person: dict, amount: float, month_year_fr: str
):
    """Create QR bill SVG via qrbill, convert to ReportLab drawing via svglib."""
    creditor = config["creditor"]
    creditor_addr = {
        "name": creditor["name"],
        "street": creditor["street"],
        "house_num": creditor["house_num"],
        "pcode": creditor["pcode"],
        "city": creditor["city"],
        "country": creditor["country"],
    }
    debtor_addr = {
        "name": person["name"],
        "street": person["street"],
        "house_num": person["house_num"],
        "pcode": person["pcode"],
        "city": person["city"],
        "country": person["country"],
    }

    bill = QRBill(
        account=config["IBAN"],
        creditor=creditor_addr,
        debtor=debtor_addr,
        amount=f"{amount:.2f}",
        currency="CHF",
        language="fr",
        additional_information=f"Facture electricite {month_year_fr}",
    )

    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
        bill.as_svg(f)
        svg_path = f.name

    try:
        drawing = svg2rlg(svg_path)
    finally:
        os.unlink(svg_path)

    return drawing


def _make_table_style(n_data_rows: int, font_size: int = 8) -> TableStyle:
    """Common table style: blue header, alternating rows, grid."""
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), BLUE_HEADER),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, n_data_rows + 1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, n_data_rows),
                [colors.white, LIGHT_BLUE],
            ),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]
    )


def build_bill_pdf(
    config: dict,
    person: dict,
    cost_row: pd.Series,
    flats_row: pd.Series,
    building_month_rows: pd.DataFrame,
    flats_month_rows: pd.DataFrame,
    output_path: str,
) -> None:
    """Build full PDF: page 1 = bill content, page 2 = QR payment slip."""
    month_year = cost_row["month_year"]
    month_year_fr = format_month_year_fr(month_year)
    bill_data = compute_person_bill(person, cost_row)

    page_w, page_h = A4
    qr_height = 105 * mm
    margin = 20 * mm

    # Generate QR bill drawing (may fail if IBAN is invalid)
    qr_drawing = None
    try:
        qr_drawing = generate_qr_bill_drawing(
            config, person, bill_data["total"], month_year_fr
        )
    except Exception as e:
        print(f"    Warning: QR bill generation failed: {e}")

    if qr_drawing:
        scale_x = page_w / qr_drawing.width
        scale_y = qr_height / qr_drawing.height
        scale = min(scale_x, scale_y)
        qr_drawing.width *= scale
        qr_drawing.height *= scale
        qr_drawing.scale(scale, scale)

    def draw_qr(canvas, doc):
        if qr_drawing:
            renderPDF.draw(qr_drawing, canvas, 0, 0)

    # Page 1: full content frame
    content_frame = Frame(
        margin, margin, page_w - 2 * margin, page_h - 2 * margin, id="content"
    )
    # Page 2: frame above QR slip
    qr_frame = Frame(
        margin,
        qr_height + 5 * mm,
        page_w - 2 * margin,
        page_h - qr_height - 5 * mm - margin,
        id="qr_content",
    )

    doc = BaseDocTemplate(output_path, pagesize=A4)
    doc.addPageTemplates(
        [
            PageTemplate(id="content_page", frames=[content_frame]),
            PageTemplate(id="qr_page", frames=[qr_frame], onPage=draw_qr),
        ]
    )

    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle("BillNormal", parent=styles["Normal"], fontSize=8)
    style_title = ParagraphStyle(
        "BillTitle", parent=styles["Heading1"], fontSize=14, spaceAfter=6
    )
    style_heading = ParagraphStyle(
        "BillHeading",
        parent=styles["Heading2"],
        fontSize=10,
        spaceBefore=8,
        spaceAfter=4,
    )

    story = []

    # --- Header: recipient (left) + creditor (right) ---
    creditor = config["creditor"]
    header_data = [
        [
            Paragraph(
                f"{person['name']}<br/>"
                f"{person['street']} {person['house_num']}<br/>"
                f"{person['pcode']} {person['city']}",
                style_normal,
            ),
            Paragraph(
                f"{creditor['name']}<br/>"
                f"{creditor['street']} {creditor['house_num']}<br/>"
                f"{creditor['pcode']} {creditor['city']}",
                style_normal,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=["50%", "50%"])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 8 * mm))

    # --- Title ---
    story.append(
        Paragraph(
            f"Facture d\u2019\u00e9lectricit\u00e9 \u2014 {month_year_fr}",
            style_title,
        )
    )

    # --- Explanation: source data and methodology ---
    story.append(Paragraph("Origine des donn\u00e9es", style_heading))
    story.append(
        Paragraph(
            "Le co\u00fbt total mensuel provient de la facture Romande Energie "
            "pour le b\u00e2timent. Ce co\u00fbt est r\u00e9parti entre les "
            "compteurs internes au prorata de leur consommation (kWh). "
            "Les p\u00e9riodes de facturation et de relev\u00e9 ne co\u00efncidant "
            "pas toujours avec le mois calendaire, les montants sont calcul\u00e9s "
            "au prorata du nombre de jours.",
            style_normal,
        )
    )
    story.append(Spacer(1, 2 * mm))

    # Building electricity source data
    bld_data = [
        [
            "Facture du",
            "Montant total",
            "Jours mois / total",
            "Prix/kWh",
            "Co\u00fbt mois",
        ]
    ]
    for _, brow in building_month_rows.iterrows():
        bld_data.append(
            [
                str(brow["billing_date"]),
                f"CHF {float(brow['billing_amount']):.2f}",
                f"{int(brow['number_day'])} / {int(brow['total_number_days'])}",
                f"CHF {float(brow['kwh_price']):.2f}",
                f"CHF {float(brow['cost']):.2f}",
            ]
        )
    n_bld_rows = len(building_month_rows)
    bld_table = Table(bld_data, colWidths=[28 * mm, 30 * mm, 35 * mm, 25 * mm, 28 * mm])
    bld_table.setStyle(_make_table_style(n_bld_rows, font_size=7))
    story.append(bld_table)
    story.append(Spacer(1, 2 * mm))

    # Internal readings source data (per-meter kWh detail)
    meter_short_labels = {
        "kwh_building": "B\u00e2timent",
        "kwh_0": "Rez inf.",
        "kwh_1": "Rez sup.",
        "kwh_2": "1er \u00e9t.",
        "kwh_fridge": "Cong\u00e9l.",
    }
    readings_header = ["Relev\u00e9 du", "Jours\nmois/total"]
    readings_header.extend(meter_short_labels[c] for c in CONSUMERS)
    readings_data = [readings_header]
    for _, frow in flats_month_rows.drop_duplicates("reading_date").iterrows():
        row = [
            str(frow["reading_date"]),
            f"{int(frow['number_day_reading_month'])}/{int(frow['total_number_days'])}",
        ]
        row.extend(f"{float(frow[f'{c}_current']):.2f}" for c in CONSUMERS)
        readings_data.append(row)
    n_reading_rows = len(flats_month_rows.drop_duplicates("reading_date"))
    readings_table = Table(
        readings_data,
        colWidths=[22 * mm, 20 * mm, 22 * mm, 20 * mm, 20 * mm, 20 * mm, 20 * mm],
    )
    readings_table.setStyle(_make_table_style(n_reading_rows, font_size=7))
    story.append(readings_table)

    # --- Step 1: Consumption and cost distribution ---
    story.append(
        Paragraph(
            "\u00c9tape 1 : Consommation et r\u00e9partition des co\u00fbts",
            style_heading,
        )
    )

    total_kwh = sum(float(flats_row.get(f"{c}_current", 0)) for c in CONSUMERS)
    total_cost = float(cost_row["total_cost"])
    cost_data = [["Compteur", "kWh", "%", "Co\u00fbt CHF"]]
    for c in CONSUMERS:
        kwh_val = float(flats_row.get(f"{c}_current", 0))
        cost_key = c.replace("kwh_", "cost_")
        cost_val = float(cost_row[cost_key])
        pct = (kwh_val / total_kwh * 100) if total_kwh > 0 else 0
        cost_data.append(
            [
                METER_LABELS_FR[c],
                f"{kwh_val:.2f}",
                f"{pct:.1f}%",
                f"{cost_val:.2f}",
            ]
        )
    cost_data.append(["Total", f"{total_kwh:.2f}", "100%", f"{total_cost:.2f}"])

    cost_table = Table(cost_data, colWidths=[80 * mm, 30 * mm, 25 * mm, 30 * mm])
    cost_table.setStyle(_make_table_style(len(CONSUMERS)))
    story.append(cost_table)

    # --- Step 2: Person's bill breakdown ---
    story.append(
        Paragraph(
            f"\u00c9tape 2 : Votre facture \u2014 {person['name']}",
            style_heading,
        )
    )

    person_rows = []
    flat_cost_key = person.get("flat_cost")
    if flat_cost_key:
        meter_key = flat_cost_key.replace("cost_", "kwh_")
        flat_label = METER_LABELS_FR.get(meter_key, flat_cost_key)
        person_rows.append(
            [
                f"Appartement ({flat_label})",
                f"{bill_data['flat_amount']:.2f} CHF",
                f"{bill_data['flat_amount']:.2f}",
            ]
        )

    building_share = person["building_share"]
    person_rows.append(
        [
            f"Part b\u00e2timent ({building_share}%)",
            f"{building_share}% \u00d7 {float(cost_row['cost_building']):.2f} CHF",
            f"{bill_data['building_amount']:.2f}",
        ]
    )

    fridge_share = person["fridge_share"]
    person_rows.append(
        [
            f"Part cong\u00e9lateur ({fridge_share}%)",
            f"{fridge_share}% \u00d7 {float(cost_row['cost_fridge']):.2f} CHF",
            f"{bill_data['fridge_amount']:.2f}",
        ]
    )

    person_table_data = [["Poste", "D\u00e9tail", "Montant CHF"]]
    person_table_data.extend(person_rows)
    person_table_data.append(["Total", "", f"{bill_data['total']:.2f}"])

    person_table = Table(person_table_data, colWidths=[70 * mm, 55 * mm, 35 * mm])
    person_table.setStyle(_make_table_style(len(person_rows)))
    story.append(person_table)

    # --- Closing ---
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            f"Montant \u00e0 payer : <b>CHF {bill_data['total']:.2f}</b>",
            style_normal,
        )
    )
    story.append(
        Paragraph(
            "Merci de r\u00e9gler ce montant par virement bancaire en utilisant "
            "le bulletin de versement ci-dessous.",
            style_normal,
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Avec nos meilleures salutations,", style_normal))
    story.append(Paragraph(creditor["name"], style_normal))

    # --- Page 2: QR payment slip ---
    if qr_drawing:
        story.append(NextPageTemplate("qr_page"))
        story.append(PageBreak())
        story.append(Spacer(1, 1))

    doc.build(story)


def generate_all_bills(
    config: dict,
    cost_df: pd.DataFrame,
    flats_df: pd.DataFrame,
    building_df: pd.DataFrame,
    output_dir: str = "bills",
) -> None:
    """Generate one PDF bill per person per month. Skip existing files."""
    validate_config(config)

    os.makedirs(output_dir, exist_ok=True)

    current_cols = [f"{c}_current" for c in CONSUMERS]
    flats_agg = flats_df.groupby("month_year")[current_cols].sum()

    for _, cost_row in cost_df.iterrows():
        month_year = cost_row["month_year"]

        if month_year not in flats_agg.index:
            print(f"  Skipping {month_year}: no flats data")
            continue

        flats_row = flats_agg.loc[month_year]
        building_month_rows = building_df[building_df["month_year"] == month_year]
        flats_month_rows = flats_df[flats_df["month_year"] == month_year]

        for person in config["persons"]:
            filename = generate_bill_filename(person["name"], month_year)
            output_path = os.path.join(output_dir, filename)

            if os.path.exists(output_path):
                print(f"  Skipping {filename} (already exists)")
                continue

            bill_data = compute_person_bill(person, cost_row)
            if bill_data["total"] <= 0:
                print(f"  Skipping {person['name']} for {month_year}: amount is 0")
                continue

            print(f"  Generating {filename}...")
            build_bill_pdf(
                config,
                person,
                cost_row,
                flats_row,
                building_month_rows,
                flats_month_rows,
                output_path,
            )

    print(f"  Bills saved to ./{output_dir}/")
