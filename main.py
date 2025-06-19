from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from bson import ObjectId
import os

from database import blog_collection, db
from models import BlogCreate, BlogResponse, UserCreate, TokenResponse
from models import LoginRequest

from utils import save_image
from auth import (
    hash_password, authenticate_user, create_access_token,
    get_current_user, users_collection
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/signup", response_model=TokenResponse)
async def signup(user: UserCreate):
    if await users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(user.password)
    await users_collection.insert_one({"name": user.name, "email": user.email, "password": hashed})
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token}

@app.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    user = await authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(data={"sub": user["email"]})
    return {"access_token": token}

@app.post("/blogs", response_model=BlogResponse)
async def create_blog(
    title: str = Form(...),
    content: str = Form(...),
    tags: Optional[str] = Form(""),
    feature_image: UploadFile = File(...),
    images: Optional[List[UploadFile]] = File(None),
    current_user: dict = Depends(get_current_user)
):
    feature_path = await save_image(feature_image)
    image_paths = []
    if images:
        for img in images[:3]:
            path = await save_image(img)
            image_paths.append(path)

    blog = {
        "title": title,
        "content": content,
        "tags": tags.split(",") if tags else [],
        "feature_image": feature_path,
        "images": image_paths,
        "author_email": current_user["email"]
    }
    result = await blog_collection.insert_one(blog)
    blog["id"] = str(result.inserted_id)
    return blog

@app.get("/blogs", response_model=List[BlogResponse])
async def get_blogs():
    blogs = []
    async for doc in blog_collection.find():
        doc["id"] = str(doc["_id"])
        blogs.append(doc)
    return blogs

@app.put("/blogs/{blog_id}", response_model=BlogResponse)
async def update_blog(blog_id: str, data: BlogCreate, current_user: dict = Depends(get_current_user)):
    # REMOVE THIS CHECK TEMPORARILY (for dev only)
    # blog = await blog_collection.find_one({"_id": ObjectId(blog_id)})
    # if not blog or blog["author_email"] != current_user["email"]:
    #     raise HTTPException(status_code=403, detail="Not authorized to update this blog")

    await blog_collection.update_one(
        {"_id": ObjectId(blog_id)},
        {"$set": data.dict()}
    )
    updated = await blog_collection.find_one({"_id": ObjectId(blog_id)})
    updated["id"] = str(updated["_id"])
    return updated


@app.delete("/blogs/{blog_id}")
async def delete_blog(blog_id: str, current_user: dict = Depends(get_current_user)):
    blog = await blog_collection.find_one({"_id": ObjectId(blog_id)})
    if not blog or blog.get("author_email") != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this blog")
    await blog_collection.delete_one({"_id": ObjectId(blog_id)})
    return {"message": "Blog deleted"}

@app.get("/uploads/{filename}")
async def serve_image(filename: str):
    path = os.path.join("uploads", filename)

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path)
