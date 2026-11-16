from math import ceil
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def calcular_contenedores(peso_toneladas: float, tipo_contenedor: str = "40'") -> int:
    if peso_toneladas <= 0:
        raise ValueError("El peso debe ser mayor a 0")
    if tipo_contenedor not in ("20'", "40'"):
        raise ValueError("Tipo de contenedor inválido")
    capacidad = 23.0 if tipo_contenedor == "20'" else 25.0
    return max(1, ceil(peso_toneladas / capacidad))


def calcular_flete(tarifa_unitaria: float, cantidad_contenedores: int) -> float:
    return round(tarifa_unitaria * cantidad_contenedores, 2)


# UT-01 a UT-07
def test_ut01_peso_10t_un_contenedor():
    assert calcular_contenedores(10, "40'") == 1


def test_ut02_peso_25t_limite_exacto_40():
    assert calcular_contenedores(25, "40'") == 1


def test_ut03_peso_26t_dos_contenedores():
    assert calcular_contenedores(26, "40'") == 2


def test_ut04_tarifa_1600_por_2():
    assert calcular_flete(1600, 2) == 3200.0


def test_ut05_peso_cero_o_negativo_rechaza_value_error():
    with pytest.raises(ValueError):
        calcular_contenedores(0, "40'")
    with pytest.raises(ValueError):
        calcular_contenedores(-5, "40'")


def test_ut06_casos_varios_40():
    assert calcular_contenedores(25.01, "40'") == 2
    assert calcular_contenedores(100, "40'") == 4
    assert calcular_contenedores(0.1, "40'") == 1


def test_ut07_redondeo_dos_decimales():
    assert calcular_flete(100.555, 3) == 301.67


# CP-05 a CP-11 (capacidades 23 t para 20' y 25 t para 40')
def test_cp05_20_pies_23t_limite_exacto():
    assert calcular_contenedores(23, "20'") == 1


def test_cp06_20_pies_23_1t_borde_superior():
    assert calcular_contenedores(23.1, "20'") == 2


def test_cp07_40_pies_23_1t_cabe_en_uno():
    assert calcular_contenedores(23.1, "40'") == 1


def test_cp08_20_pies_24t():
    assert calcular_contenedores(24, "20'") == 2


def test_cp09_40_pies_24t():
    assert calcular_contenedores(24, "40'") == 1


def test_cp10_40_pies_25t_y_25_1t():
    assert calcular_contenedores(25, "40'") == 1
    assert calcular_contenedores(25.1, "40'") == 2


def test_cp11_20_pies_46t_y_46_1t():
    assert calcular_contenedores(46, "20'") == 2
    assert calcular_contenedores(46.1, "20'") == 3
