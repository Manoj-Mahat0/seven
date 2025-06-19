from pydantic import BaseModel, EmailStr
from typing import List, Optional

class BlogCreate(BaseModel):
    title: str
    content: str
    tags: List[str] = []

class BlogResponse(BlogCreate):
    id: str
    feature_image: str
    images: List[str]

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str