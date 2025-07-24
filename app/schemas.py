from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    first_name:str
    last_name:str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class Login(BaseModel):
    email: EmailStr
    password: str

class MessageCreate(BaseModel):
    receiver_id: int
    content: str

class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    # is_read:bool
    timestamp: datetime
    class Config:
        orm_mode = True

class MessageRead(BaseModel):
    id: int
    is_read: bool
    detail: Optional[str] = None

    class Config:
        orm_mode = True


class Conversation(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    timestamp: datetime
    is_read:bool

    class Config:
        orm_mode = True


class ActiveUserBase(BaseModel):
    user_id: int

class ActiveUserCreate(ActiveUserBase):
    pass

class ActiveUserResponse(ActiveUserBase):
    connected_at: datetime

    class Config:
        orm_mode = True
