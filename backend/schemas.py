from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


Roles = Literal[
    "Analista COMEX",
    "Jefatura COMEX",
    "Administrador",
]


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=72,
    )


class UsuarioAdminCreate(BaseModel):
    nombre: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=10,
        max_length=72,
    )

    rol: Roles

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, value: str) -> str:
        return " ".join(value.strip().split())


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    rol: str
    nombre: str


class UsuarioPublico(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    rol: str

    model_config = {
        "from_attributes": True
    }


class CotizacionRequest(BaseModel):
    puerto_origen: str = Field(
        min_length=2,
        max_length=120,
    )

    puerto_destino: str = Field(
        min_length=2,
        max_length=120,
    )

    tipo_contenedor: Literal[
        "20'",
        "40'",
    ]

    peso_toneladas: float = Field(
        gt=0,
        le=10000,
    )

    contingencia_dias: int = Field(
        default=0,
        ge=0,
        le=30,
    )

    tipo_cambio_clp_usd: float | None = Field(
        default=None,
        gt=0,
        le=100000,
    )

    @field_validator(
        "puerto_origen",
        "puerto_destino",
    )
    @classmethod
    def limpiar_puerto(cls, value: str) -> str:
        return " ".join(value.strip().split())