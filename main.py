import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageIn(BaseModel):
    room: str = "global"
    username: str
    text: str
    avatar: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "8-Bit Chat Backend Running"}


@app.get("/api/messages")
def list_messages(room: str = Query("global"), limit: int = Query(50, ge=1, le=200)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = get_documents("chatmessage", {"room": room}, limit=limit)
    # Sort by created_at ascending for chat ordering
    docs = sorted(docs, key=lambda d: d.get("created_at"))

    def serialize(doc):
        doc["id"] = str(doc.get("_id")) if doc.get("_id") else None
        # Remove internal _id for cleanliness
        if "_id" in doc:
            del doc["_id"]
        return doc

    return [serialize(d) for d in docs]


@app.post("/api/messages", status_code=201)
def create_message(payload: MessageIn):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Message text cannot be empty")

    inserted_id = create_document("chatmessage", payload)
    # Return the created document minimal info
    return {"id": inserted_id}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
