from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = "mongodb+srv://manojmahato08779:hdR6wNEzmITKtgOX@cluster0.rvx2snj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = AsyncIOMotorClient(MONGO_URL)
db = client["blog_db"]
blog_collection = db["blogs"]
