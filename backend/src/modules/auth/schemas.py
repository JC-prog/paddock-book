from typing import Literal

from pydantic import BaseModel

Department = Literal["sporting", "technical", "financial"]


class RegisterRequest(BaseModel):
    email: str
    password: str
    department: Department


class LoginRequest(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    id: str
    email: str
    department: Department


class AuthResponse(BaseModel):
    access_token: str
    user: UserPublic
