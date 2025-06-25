from pydantic import BaseModel, Field
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

class BlogUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    feature_image: Optional[str] = None 

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

class ContactForm(BaseModel):
    name: str = Field(...)
    contact_number: str = Field(...)
    email: EmailStr = Field(...)
    message: str = Field(...)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "contact_number": "9876543210",
                "email": "john@example.com",
                "message": "I would like to inquire about your services."
            }
        }