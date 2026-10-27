from __future__ import annotations

from io import BytesIO
import hashlib
import math
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import pandas as pd
from sqlalchemy.orm import Session

import models


SHEET_NAME = "Tarifas Referencia"

EXPECTED_COLUMNS = [
    "Clave",
    "Puerto Origen",
    "Pais Origen",
    "Puerto Destino",
    "Tipo de Ruta",
    "Tarifa 20' Min (US$)",
    "Tarifa 20' Max (US$)",
    "Tarifa 40' Min (US$)",
    "Tarifa 40' Max (US$)",
    "Transito Min (dias)",
    "Transito Max (dias)",
    "Fuente",
]


def normalize_text(value) -> str:
    return " ".join(str(value).strip().split())


def parse_tariff_excel(
    content: bytes,
) -> tuple[list[dict], list[dict], int]:

    try:
        with ZipFile(BytesIO(content)) as archive:

            members = archive.infolist()

            if len(members) > 2000:
                raise ValueError(
                    "El archivo contiene demasiados elementos internos"
                )

            uncompressed = sum(
                item.file_size
                for item in members
            )

            if uncompressed > 30 * 1024 * 1024:
                raise ValueError(
                    "El contenido descomprimido del Excel supera 30 MB"
                )

            if (
                len(content)
                and uncompressed > 100 * len(content)
                and uncompressed > 10 * 1024 * 1024
            ):
                raise ValueError(
                    "El archivo presenta una relación de compresión no permitida"
                )

    except BadZipFile as exc:
        raise ValueError(
            "El archivo no es un .xlsx válido"
        ) from exc

    try:
        df = pd.read_excel(
            BytesIO(content),
            sheet_name=SHEET_NAME,
        )

    except ValueError as exc:
        raise ValueError(
            f"El archivo debe contener la hoja '{SHEET_NAME}'"
        ) from exc

    except Exception as exc:
        raise ValueError(
            "No fue posible leer el archivo Excel"
        ) from exc

    missing = [
        column
        for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            "Faltan columnas obligatorias: "
            + ", ".join(missing)
        )

    df = df[EXPECTED_COLUMNS].dropna(
        how="all"
    )

    if len(df) > 5000:
        raise ValueError(
            "El archivo supera el máximo de 5.000 filas permitido"
        )

    valid_rows = []
    errors = []
    seen_routes = set()

    for idx, row in df.iterrows():

        excel_row = int(idx) + 2

        try:
            origin = normalize_text(
                row["Puerto Origen"]
            )

            destination = normalize_text(
                row["Puerto Destino"]
            )

            country = normalize_text(
                row["Pais Origen"]
            )

            route_type = normalize_text(
                row["Tipo de Ruta"]
            )

            source = (
                normalize_text(row["Fuente"])
                if not pd.isna(row["Fuente"])
                else "Sin fuente indicada"
            )

            key = normalize_text(
                row["Clave"]
            )

            if (
                not origin
                or origin.lower() == "nan"
                or not destination
                or destination.lower() == "nan"
            ):
                raise ValueError(
                    "Puerto de origen/destino vacío"
                )

            expected_key = (
                f"{origin}|{destination}"
            )

            if (
                key.casefold()
                != expected_key.casefold()
            ):
                raise ValueError(
                    f"Clave inconsistente: se esperaba '{expected_key}'"
                )

            values = {
                "tarifa_20_min":
                    float(
                        row["Tarifa 20' Min (US$)"]
                    ),

                "tarifa_20_max":
                    float(
                        row["Tarifa 20' Max (US$)"]
                    ),

                "tarifa_40_min":
                    float(
                        row["Tarifa 40' Min (US$)"]
                    ),

                "tarifa_40_max":
                    float(
                        row["Tarifa 40' Max (US$)"]
                    ),

                "transito_min":
                    int(
                        row["Transito Min (dias)"]
                    ),

                "transito_max":
                    int(
                        row["Transito Max (dias)"]
                    ),
            }

            if any(
                not math.isfinite(float(v))
                or float(v) < 0
                for v in values.values()
            ):
                raise ValueError(
                    "Existen valores numéricos inválidos o negativos"
                )

            if (
                values["tarifa_20_min"]
                > values["tarifa_20_max"]
                or
                values["tarifa_40_min"]
                > values["tarifa_40_max"]
            ):
                raise ValueError(
                    "La tarifa mínima no puede ser mayor que la máxima"
                )

            if (
                values["transito_min"]
                > values["transito_max"]
            ):
                raise ValueError(
                    "El tránsito mínimo no puede ser mayor que el máximo"
                )

            duplicate_key = (
                origin.casefold(),
                destination.casefold(),
                route_type.casefold(),
                values["tarifa_20_min"],
                values["tarifa_20_max"],
                values["tarifa_40_min"],
                values["tarifa_40_max"],
                values["transito_min"],
                values["transito_max"],
            )

            if duplicate_key in seen_routes:
                raise ValueError(
                    "Registro duplicado"
                )

            seen_routes.add(
                duplicate_key
            )

            valid_rows.append({
                "puerto_origen": origin,
                "pais_origen": country,
                "puerto_destino": destination,
                "tipo_ruta": route_type,
                "fuente": source,
                **values,
            })

        except (TypeError, ValueError) as exc:

            errors.append({
                "fila": excel_row,
                "error": str(exc),
            })

    return (
        valid_rows,
        errors,
        len(df),
    )


def create_tariff_version(
    db: Session,
    *,
    filename: str,
    content: bytes,
    created_by_id: int | None,
    allow_partial: bool = False,
) -> models.VersionTarifa:

    valid_rows, errors, total_rows = (
        parse_tariff_excel(content)
    )

    if not valid_rows:
        raise ValueError(
            "El archivo no contiene filas válidas"
        )

    if errors and not allow_partial:

        preview = "; ".join(
            f"fila {e['fila']}: {e['error']}"
            for e in errors[:5]
        )

        raise ValueError(
            f"La carga fue rechazada por {len(errors)} error(es). {preview}"
        )

    file_hash = hashlib.sha256(
        content
    ).hexdigest()

    version = models.VersionTarifa(
        nombre_archivo=filename,
        hash_archivo=file_hash,
        estado="PENDIENTE",
        total_filas=total_rows,
        filas_validas=len(valid_rows),
        filas_invalidas=len(errors),
        resumen_validacion={
            "errores": errors[:100]
        },
        creada_por_id=created_by_id,
    )

    db.add(version)
    db.flush()

    for row in valid_rows:

        db.add(
            models.Tarifa(
                version_id=version.id,
                **row,
            )
        )

    db.commit()
    db.refresh(version)

    return version


def seed_initial_tariffs(
    db: Session,
    excel_path: Path,
) -> None:

    if (
        db.query(
            models.VersionTarifa
        ).count() > 0
        or not excel_path.exists()
    ):
        return

    content = excel_path.read_bytes()

    version = create_tariff_version(
        db,
        filename=excel_path.name,
        content=content,
        created_by_id=None,
        allow_partial=True,
    )

    activate_version(
        db,
        version.id,
    )


def activate_version(
    db: Session,
    version_id: int,
) -> models.VersionTarifa:

    version = (
        db.query(models.VersionTarifa)
        .filter(
            models.VersionTarifa.id
            == version_id
        )
        .first()
    )

    if not version:
        raise ValueError(
            "Versión no encontrada"
        )

    if version.filas_validas <= 0:
        raise ValueError(
            "La versión no contiene tarifas válidas"
        )

    from datetime import datetime, timezone

    (
        db.query(models.VersionTarifa)
        .filter(
            models.VersionTarifa.estado
            == "ACTIVA"
        )
        .update({
            "estado": "INACTIVA"
        })
    )

    version.estado = "ACTIVA"

    version.activated_at = (
        datetime.now(timezone.utc)
    )

    db.commit()
    db.refresh(version)

    return version