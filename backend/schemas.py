from pydantic import BaseModel

# Lo que React nos enviará para crear un usuario
class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    password: str
    rol: str

# Lo que React nos enviará para el Login
class UsuarioLogin(BaseModel):
    email: str
    password: str

# Lo que FastAPI le devolverá a React si el Login es exitoso
class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str