"""Register, log in, and get the current user."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Restaurant, Role, User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    """Create an account and log it in. Owners also get their restaurant created here."""
    # Emails are stored lowercase so login is case-insensitive
    email = data.email.lower()
    if db.scalars(select(User).where(User.email == email)).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    if data.role == Role.OWNER:
        # A missing name and a name of only spaces are both rejected
        has_restaurant_name = data.restaurant_name is not None and data.restaurant_name.strip() != ""
        if not has_restaurant_name:
            raise HTTPException(status_code=422, detail="Restaurant name is required for restaurant owners")

    user = User(
        name=data.name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        role=data.role,
        phone=data.phone,
        address=data.address,
    )
    db.add(user)
    db.flush()  # gives user.id before commit

    if data.role == Role.OWNER:
        db.add(Restaurant(owner_id=user.id, name=data.restaurant_name.strip(), cuisine=data.cuisine))

    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    """Check email and password and return a JWT."""
    user = db.scalars(select(User).where(User.email == data.email.lower())).first()
    # Same message for unknown email and wrong password, so accounts can't be probed
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    return TokenOut(access_token=create_access_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """Return the logged-in user's profile."""
    return user
