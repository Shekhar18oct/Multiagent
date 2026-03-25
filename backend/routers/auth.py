# Authentication and user management
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import os

SECRET_KEY = os.getenv("SECRET_KEY", "test-secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory user store (replace with DB in production)
# Admin password hashed lazily to avoid import-time issues with bcrypt
_users_db: dict = {}

def _get_users_db() -> dict:
    if not _users_db:
        _users_db["admin@example.com"] = {
            "username": "admin@example.com",
            "hashed_password": pwd_context.hash("adminpass"),
            "role": "admin",
        }
    return _users_db

class User(BaseModel):
    username: str
    password: str
    role: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

@router.post("/signup", response_model=Token)
def signup(user: User):
    db = _get_users_db()
    if user.username in db:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_password = pwd_context.hash(user.password)
    role = user.role if user.role else "user"
    db[user.username] = {"username": str(user.username), "hashed_password": str(hashed_password), "role": role}
    access_token = create_access_token(data={"sub": user.username, "role": role})
    return {"access_token": access_token, "token_type": "bearer", "role": role}

@router.post("/login", response_model=Token)
def login(user: User):
    db = _get_users_db()
    db_user = db.get(user.username)
    if not db_user or not pwd_context.verify(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.username, "role": db_user["role"]})
    return {"access_token": access_token, "token_type": "bearer", "role": db_user["role"]}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
