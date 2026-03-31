"""
Auth Routes — Registration, Login, Current User.
"""
from fastapi import APIRouter, Depends

from app.core.security import (
    authenticate_user, create_access_token, register_user,
    get_current_user, rate_limiter,
)
from app.models.schemas import (
    LoginRequest, RegisterRequest, TokenResponse, UserResponse, APIResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse)
async def register(req: RegisterRequest, _=Depends(rate_limiter)):
    user = register_user(req.username, req.password, req.role, req.full_name)
    return APIResponse(success=True, message="User registered", data=user)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, _=Depends(rate_limiter)):
    from fastapi import HTTPException
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def current_user(user=Depends(get_current_user)):
    return UserResponse(**user)
