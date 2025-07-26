# app/dependencies/auth.py

from fastapi import Request, HTTPException

def get_current_user(request: Request) -> str:
    user_email = request.session.get("user")
    if not user_email:
        raise HTTPException(status_code=401, detail="User not logged in")
    return user_email
