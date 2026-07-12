"""PDF and Excel export of a city's current weather + forecast."""

import io

from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


def _forecast_rows(forecast):
    daily = forecast.get("daily", {})
    times = daily.get("time", [])
    rows = [["Date", "Max (C)", "Min (C)", "Rain chance (%)", "UV max"]]
    for i, date in enumerate(times):
        rows.append([
            date,
            daily.get("temperature_2m_max", [None])[i],
            daily.get("temperature_2m_min", [None])[i],
            daily.get("precipitation_probability_max", [None])[i],
            daily.get("uv_index_max", [None])[i],
        ])
    return rows


def build_pdf_report(city_name, current, forecast):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Weather Report: {city_name}", styles["Title"]),
        Spacer(1, 0.2 * inch),
        Paragraph("Current Conditions", styles["Heading2"]),
    ]

    cur = current.get("current", {})
    current_rows = [
        ["Temperature (C)", cur.get("temperature_2m")],
        ["Feels like (C)", cur.get("apparent_temperature")],
        ["Humidity (%)", cur.get("relative_humidity_2m")],
        ["Wind (km/h)", cur.get("wind_speed_10m")],
        ["UV Index", cur.get("uv_index")],
    ]
    current_table = Table(current_rows, colWidths=[2.5 * inch, 2.5 * inch])
    current_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
    ]))
    elements.append(current_table)
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("7-Day Forecast", styles["Heading2"]))
    forecast_table = Table(_forecast_rows(forecast))
    forecast_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b6cb0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ]))
    elements.append(forecast_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def build_excel_report(city_name, current, forecast):
    wb = Workbook()

    ws_current = wb.active
    ws_current.title = "Current"
    cur = current.get("current", {})
    ws_current.append(["Metric", "Value"])
    for label, value in [
        ("Temperature (C)", cur.get("temperature_2m")),
        ("Feels like (C)", cur.get("apparent_temperature")),
        ("Humidity (%)", cur.get("relative_humidity_2m")),
        ("Wind (km/h)", cur.get("wind_speed_10m")),
        ("UV Index", cur.get("uv_index")),
    ]:
        ws_current.append([label, value])

    ws_forecast = wb.create_sheet("Forecast")
    for row in _forecast_rows(forecast):
        ws_forecast.append(row)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def pdf_response(city_name, current, forecast):
    buffer = build_pdf_report(city_name, current, forecast)
    response = HttpResponse(buffer.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{city_name}_weather.pdf"'
    return response


def excel_response(city_name, current, forecast):
    buffer = build_excel_report(city_name, current, forecast)
    response = HttpResponse(
        buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{city_name}_weather.xlsx"'
    return response
