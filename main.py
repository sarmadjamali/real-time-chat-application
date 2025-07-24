from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, APIRouter,WebSocketDisconnect
from sqlalchemy import func,or_,and_
from sqlalchemy.orm import Session
from . import models, schemas, utils, auth, database
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import List
from .websocket_manager import manager
import asyncio

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

@app.post("/signup", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(auth.get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = utils.hash_password(user.password)
    new_user = models.User(first_name = user.first_name,last_name = user.last_name,email=user.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/sign-in", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(auth.get_db)):
    # print("step 1")
    
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    # print(user)
    if not user or not utils.verify_password(form_data.password, str(user.hashed_password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials")
    token = utils.create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=60))
    return {"access_token": token, "token_type": "bearer"}

@app.get("/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.post("/messages", response_model=schemas.MessageOut)
async def send_message(message: schemas.MessageCreate, db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    recipient = db.query(models.User).filter(models.User.id == message.receiver_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    new_message = models.Message(
        sender_id=current_user.id,
        receiver_id=message.receiver_id,
        content=message.content,
        is_read = 0
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    #  Notify receiver if online
    try:
        import json
        content = json.dumps({
            "type": "new_message",
            "from": current_user.id,
            "content": new_message.content,
            "message_id": new_message.id
        })
        await manager.send_personal_message(content, new_message.receiver_id)
    
    except Exception as e:
        print("WebSocket error:", e)

    return new_message

@app.get("/conversations", response_model=List[schemas.Conversation])
def get_conversations(db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Get distinct conversation partners with the latest message
    subquery = (
        db.query(
            func.greatest(models.Message.sender_id, models.Message.receiver_id).label("user1"),
            func.least(models.Message.sender_id, models.Message.receiver_id).label("user2"),
            func.max(models.Message.timestamp).label("last_message_time")
        )
        .filter(or_(models.Message.sender_id == current_user.id, models.Message.receiver_id == current_user.id))
        .group_by("user1", "user2")
        .subquery()
    )

    results = (
        db.query(models.Message)
        .join(subquery, and_(
            func.greatest(models.Message.sender_id, models.Message.receiver_id) == subquery.c.user1,
            func.least(models.Message.sender_id, models.Message.receiver_id) == subquery.c.user2,
            models.Message.timestamp == subquery.c.last_message_time
        ))
        .order_by(models.Message.timestamp.desc())
        .all()
    )

    return results


@app.post("/mark-as-read", response_model=schemas.MessageRead)
def markAsRead(id: int, db: Session = Depends(auth.get_db), current_user: models.User = Depends(auth.get_current_user)):
    message = db.query(models.Message).filter(models.Message.id == id).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message and current_user.id !=  message.receiver_id:
            raise HTTPException(status_code=403, detail="Not Authorized to update this message")

    if message.is_read:
        return {"detail": "Message already marked as read"}

    message.is_read = 1
    db.commit()

    return {"detail": "Message marked as read"}


router = APIRouter()

# adding websocket routes
@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    db: Session = Depends(auth.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    await manager.connect(current_user.id, websocket)

    # Add to active_users table if not exists
    existing = db.query(models.ActiveUser).filter_by(user_id=current_user.id).first()
    if not existing:
        db.add(models.ActiveUser(user_id=current_user.id))
        db.commit()

    try:
        while True:
            data = await websocket.receive_text()
            # Here you'd receive chat messages
            print(f"Received: {data}")
            # Echo back or process message
            await manager.send_personal_message(f"You said: {data}", current_user.id)

    except Exception as e:
        print(f"Disconnecting user {current_user.id}: {e}")
    finally:
        manager.disconnect(current_user.id)
        db.query(models.ActiveUser).filter_by(user_id=current_user.id).delete()
        db.commit()





# @app.websocket("/ws/chat")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         while True:
#             data = await websocket.receive_text()
#             print("Received:", data)
#             await websocket.send_text(f"Message received: {data}")
#     except WebSocketDisconnect:
#         print("Client disconnected")