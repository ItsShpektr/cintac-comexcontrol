from io import BytesIO
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tariff_service import EXPECTED_COLUMNS, SHEET_NAME, parse_tariff_excel


def build_excel_bytes(rows: list[dict], sheet_name: str = SHEET_NAME, drop_cols: list[str] | None = None) -> bytes:
    df = pd.DataFrame(rows)
    if drop_cols:
        df = df.drop(columns=drop_cols)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buf.getvalue()


def sample_row(**overrides) -> dict:
    base = {
        "Clave": "Qingdao|San Antonio",
        "Puerto Origen": "Qingdao",
        "Pais Origen": "China",
        "Puerto Destino": "San Antonio",
        "Tipo de Ruta": "Directo",
        "Tarifa 20' Min (US$)": 4100,
        "Tarifa 20' Max (US$)": 4300,
        "Tarifa 40' Min (US$)": 5500,
        "Tarifa 40' Max (US$)": 5700,
        "Transito Min (dias)": 35,
        "Transito Max (dias)": 45,
        "Fuente": "Tarifario Validado",
    }
    base.update(overrides)
    return base


# UT-08
def test_ut08_excel_valido_acepta_todas_las_filas():
    content = build_excel_bytes([
        sample_row(),
        sample_row(
            **{
                "Clave": "San Antonio|Callao (Peru)",
                "Puerto Origen": "San Antonio",
                "Pais Origen": "Chile",
                "Puerto Destino": "Callao (Peru)",
                "Tarifa 20' Min (US$)": 900,
                "Tarifa 20' Max (US$)": 900,
                "Tarifa 40' Min (US$)": 970,
                "Tarifa 40' Max (US$)": 970,
                "Transito Min (dias)": 3,
                "Transito Max (dias)": 5,
            }
        ),
    ])
    valid, errors, total = parse_tariff_excel(content)
    assert total == 2
    assert len(valid) == 2
    assert errors == []


# UT-09
def test_ut09_archivo_no_xlsx_rechazo_con_mensaje():
    with pytest.raises(ValueError, match="no es un .xlsx válido"):
        parse_tariff_excel(b"contenido plano que no es excel")


# UT-10
def test_ut10_falta_hoja_tarifas_referencia():
    content = build_excel_bytes([sample_row()], sheet_name="OtraHoja")
    with pytest.raises(ValueError, match="Tarifas Referencia"):
        parse_tariff_excel(content)


# UT-11
def test_ut11_faltan_columnas_reporta_lista():
    content = build_excel_bytes([sample_row()], drop_cols=["Fuente", "Tipo de Ruta"])
    with pytest.raises(ValueError, match="Faltan columnas obligatorias: Tipo de Ruta, Fuente"):
        parse_tariff_excel(content)


# UT-12
def test_ut12_clave_inconsistente_reportada_por_fila():
    content = build_excel_bytes([sample_row(Clave="OrigenMalo|DestinoMalo")])
    valid, errors, _ = parse_tariff_excel(content)
    assert valid == []
    assert len(errors) == 1
    assert errors[0]["fila"] == 2
    assert "Clave inconsistente" in errors[0]["error"]


# UT-13 y CP-16
def test_ut13_y_cp16_tarifa_o_transito_min_mayor_que_max():
    content = build_excel_bytes([
        sample_row(**{"Tarifa 20' Min (US$)": 5000, "Tarifa 20' Max (US$)": 4000}),
        sample_row(**{"Transito Min (dias)": 5, "Transito Max (dias)": 3}),
    ])
    valid, errors, _ = parse_tariff_excel(content)
    assert valid == []
    assert len(errors) == 2
    assert errors[0]["fila"] == 2
    assert "tarifa mínima" in errors[0]["error"].lower()
    assert errors[1]["fila"] == 3
    assert "tránsito mínimo" in errors[1]["error"].lower()


# UT-14
def test_ut14_valores_negativos_y_duplicados():
    content = build_excel_bytes([
        sample_row(**{"Tarifa 40' Min (US$)": -100}),
        sample_row(),
        sample_row(),
    ])
    valid, errors, _ = parse_tariff_excel(content)
    assert len(valid) == 1
    assert len(errors) == 2
    assert errors[0]["fila"] == 2
    assert "negativos" in errors[0]["error"].lower()
    assert errors[1]["fila"] == 4
    assert "duplicado" in errors[1]["error"].lower()
