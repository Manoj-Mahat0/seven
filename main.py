from datetime import datetime
from fastapi import Body, FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from datetime import datetime, timedelta
import pytz
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from bson import ObjectId
import os

from database import blog_collection, db, contact_collection, message_collection
from email_utils import render_template, send_email
from models import BlogCreate, BlogResponse, BlogUpdate, ContactForm, GeneralMessageForm, UserCreate, TokenResponse
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
    content: str = Form(..., description="Supports Markdown or HTML for rich formatting (headings, bullet points, tables, links, etc.)"),
    tags: Optional[str] = Form(""),
    feature_image: UploadFile = File(...),
    images: Optional[List[UploadFile]] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a blog post.
    - `content` supports Markdown or HTML for subheadings (h2-h5), bullet points, tables, and links to other blogs.
    """
    feature_path = await save_image(feature_image)
    image_paths = []
    if images:
        for img in images[:3]:
            path = await save_image(img)
            image_paths.append(path)

    # Get current time in IST (Indian Standard Time)
    ist = pytz.timezone("Asia/Kolkata")
    created_at = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

    blog = {
        "title": title,
        "content": content,  # Accepts Markdown/HTML for rich formatting
        "tags": tags.split(",") if tags else [],
        "feature_image": feature_path,
        "images": image_paths,
        "author_email": current_user["email"],
        "created_at": created_at  # Indian timestamp
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

@app.get("/blogs/with-images", response_model=List[BlogResponse])
async def get_blogs_with_image_urls(request: Request):
    blogs = []
    base_url = str(request.base_url).rstrip("/")
    async for doc in blog_collection.find():
        doc["id"] = str(doc["_id"])
        # Convert feature_image to full URL
        if doc.get("feature_image"):
            doc["feature_image"] = f"{base_url}/uploads/{os.path.basename(doc['feature_image'])}"
        # Convert all images to full URLs
        if doc.get("images"):
            doc["images"] = [
                f"{base_url}/uploads/{os.path.basename(img)}" for img in doc["images"]
            ]
        blogs.append(doc)
    return blogs

@app.put("/blogs/{blog_id}", response_model=BlogResponse)
async def update_blog(blog_id: str, data: BlogUpdate = Body(...), current_user: dict = Depends(get_current_user)):
    blog = await blog_collection.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    # Uncomment before production
    # if blog["author_email"] != current_user["email"]:
    #     raise HTTPException(status_code=403, detail="Not authorized to update this blog")

    update_data = {k: v for k, v in data.dict(exclude_unset=True).items()}

    if update_data:
        await blog_collection.update_one({"_id": ObjectId(blog_id)}, {"$set": update_data})

    updated = await blog_collection.find_one({"_id": ObjectId(blog_id)})
    updated["id"] = str(updated.pop("_id"))
    return BlogResponse(**updated)


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

@app.post("/contact")
async def submit_contact(data: ContactForm):
    from datetime import datetime

    # ✅ Save to DB
    await contact_collection.insert_one({
        "name": data.name,
        "email": data.email,
        "contact_number": data.contact_number,
        "message": data.message,
        "submitted_at": datetime.utcnow()
    })

    # Context for template
    context = {
        "name": data.name,
        "email": data.email,
        "phone": data.contact_number,
        "message": data.message
    }

    # Load and render templates
    admin_html = render_template("email_templates/contact_admin.html", context)
    user_html = render_template("email_templates/contact_user_reply.html", context)

    # Send to admin
    await send_email(
        to_email="support@sevenfinancials.in",
        subject="📩 New Contact Inquiry",
        text_body=f"Name: {data.name}\nEmail: {data.email}\nPhone: {data.contact_number}\n\nMessage:\n{data.message}",
        html_body=admin_html
    )

    # Auto-reply to user
    await send_email(
        to_email=data.email,
        subject="✅ Thank you for contacting Seven Financials",
        text_body=f"Hi {data.name},\n\nThank you for contacting Seven Financials. We will reply soon.",
        html_body=user_html
    )

    return {"message": "Thank you! Your message has been received."}

@app.post("/message", tags=["General Message"])
async def submit_general_message(data: GeneralMessageForm):
    context = {
        "name": data.name,
        "email": data.email,
        "subject": data.subject,
        "message": data.message,
        "submitted_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

    # ✅ Save to DB
    await message_collection.insert_one({
        **context,
        "created_at": datetime.utcnow()
    })

    # ✅ Render admin notification
    html_admin = render_template("email_templates/general_message.html", context)

    await send_email(
        to_email="support@sevenfinancials.in",
        subject=f"📬 {data.subject}",
        text_body=f"Name: {data.name}\nEmail: {data.email}\nSubject: {data.subject}\n\nMessage:\n{data.message}",
        html_body=html_admin
    )

    # ✅ Auto-reply to user
    html_user = render_template("email_templates/general_autoreply.html", context)

    await send_email(
        to_email=data.email,
        subject="✅ We've received your message",
        text_body=f"Hi {data.name},\n\nThank you for contacting Seven Financials. We will get back to you shortly regarding: {data.subject}",
        html_body=html_user
    )

    return {"message": "Your message has been received and a confirmation has been sent to your email."}