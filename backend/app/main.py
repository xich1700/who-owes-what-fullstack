from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import Base, engine
from .routers import auth, groups, expenses, share

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Who owes what? API", version="1.0.0")

# In production, replace "*" with your actual frontend's URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(expenses.router)
app.include_router(share.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "who-owes-what-api"}
