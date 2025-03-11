"""
Authentication and security module for the autonomous agent system.

This module handles user authentication, JWT tokens, and security policies.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Security configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Data stored in a token."""
    username: Optional[str] = None
    user_id: Optional[str] = None
    scopes: list[str] = []


class User(BaseModel):
    """User model for authentication."""
    user_id: str
    username: str
    email: str
    full_name: str
    disabled: bool = False
    hashed_password: str
    created_at: float
    role: str = "user"  # "user", "admin"
    scopes: list[str] = ["agent:read", "agent:write"]


class UserCreate(BaseModel):
    """Model for creating a new user."""
    username: str
    email: str
    password: str
    full_name: str


class UserDB(BaseModel):
    """User model with DB-specific fields."""
    user_id: str
    username: str
    email: str
    full_name: str
    disabled: bool = False
    hashed_password: str
    created_at: float
    role: str = "user"
    scopes: list[str] = ["agent:read", "agent:write"]


class UserInDB(User):
    """User model for database operations."""
    hashed_password: str


class UserOut(BaseModel):
    """User model for API responses."""
    user_id: str
    username: str
    email: str
    full_name: str
    disabled: bool
    role: str
    created_at: float


# Mock user database - in a real system, this would be a DB connection
users_db = {}


def get_user(username: str) -> Optional[UserInDB]:
    """
    Get a user by username.

    Args:
        username: Username to look up.

    Returns:
        User object if found, None otherwise.
    """
    if username in users_db:
        user_dict = users_db[username]
        return UserInDB(**user_dict)
    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password.
        hashed_password: Hashed password.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password.

    Returns:
        Hashed password.
    """
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> Union[User, bool]:
    """
    Authenticate a user with username and password.

    Args:
        username: Username to authenticate.
        password: Password to check.

    Returns:
        User object if authenticated, False otherwise.
    """
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(
    data: Dict,
    secret_key: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token.
        secret_key: Secret key to sign the token.
        expires_delta: Token expiration time delta.

    Returns:
        JWT token string.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), secret_key: str = None) -> User:
    """
    Get the current user from a token.

    Args:
        token: JWT token.
        secret_key: Secret key to verify the token.

    Returns:
        User object if token is valid.

    Raises:
        HTTPException: If the token is invalid or the user doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user.

    Args:
        current_user: User from token.

    Returns:
        User object if active.

    Raises:
        HTTPException: If the user is disabled.
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class UserManager:
    """Manager for user operations."""

    def __init__(self, config: Dict):
        """
        Initialize the user manager.

        Args:
            config: Configuration dict.
        """
        self.config = config
        self.secret_key = config.get("SECRET_KEY", "development_secret_key")
        self.access_token_expire_minutes = int(config.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

        # Initialize with admin user if none exists
        if not users_db:
            self._create_initial_admin()

    def _create_initial_admin(self):
        """Create an initial admin user if none exists."""
        admin_username = self.config.get("ADMIN_USERNAME", "admin")
        admin_password = self.config.get("ADMIN_PASSWORD", "adminpassword")
        admin_email = self.config.get("ADMIN_EMAIL", "admin@example.com")

        # Hash the password
        hashed_password = get_password_hash(admin_password)

        # Create admin user
        import uuid
        admin_user = {
            "user_id": str(uuid.uuid4()),
            "username": admin_username,
            "email": admin_email,
            "full_name": "Administrator",
            "disabled": False,
            "hashed_password": hashed_password,
            "created_at": time.time(),
            "role": "admin",
            "scopes": ["agent:read", "agent:write", "user:read", "user:write", "admin"]
        }

        users_db[admin_username] = admin_user

    async def get_token(self, form_data: OAuth2PasswordRequestForm) -> Token:
        """
        Generate a token for a user.

        Args:
            form_data: OAuth2 password request form.

        Returns:
            Token object.

        Raises:
            HTTPException: If authentication fails.
        """
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=self.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.user_id, "scopes": user.scopes},
            secret_key=self.secret_key,
            expires_delta=access_token_expires
        )

        return Token(access_token=access_token, token_type="bearer")

    async def create_user(self, user_create: UserCreate) -> UserOut:
        """
        Create a new user.

        Args:
            user_create: User creation data.

        Returns:
            Created user.

        Raises:
            HTTPException: If the username already exists.
        """
        if user_create.username in users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        # Hash the password
        hashed_password = get_password_hash(user_create.password)

        # Create user
        import uuid
        user_dict = {
            "user_id": str(uuid.uuid4()),
            "username": user_create.username,
            "email": user_create.email,
            "full_name": user_create.full_name,
            "disabled": False,
            "hashed_password": hashed_password,
            "created_at": time.time(),
            "role": "user",
            "scopes": ["agent:read", "agent:write"]
        }

        users_db[user_create.username] = user_dict

        return UserOut(**user_dict)

    async def get_user_by_id(self, user_id: str) -> Optional[UserOut]:
        """
        Get a user by ID.

        Args:
            user_id: User ID to look up.

        Returns:
            User object if found, None otherwise.
        """
        for username, user_dict in users_db.items():
            if user_dict.get("user_id") == user_id:
                return UserOut(**user_dict)
        return None

    async def list_users(self) -> list[UserOut]:
        """
        List all users.

        Returns:
            List of users.
        """
        return [UserOut(**user_dict) for user_dict in users_db.values()]

    async def update_user(self, user_id: str, user_data: Dict) -> Optional[UserOut]:
        """
        Update a user.

        Args:
            user_id: User ID to update.
            user_data: Updated user data.

        Returns:
            Updated user if found, None otherwise.
        """
        for username, user_dict in users_db.items():
            if user_dict.get("user_id") == user_id:
                # Don't update certain fields
                if "password" in user_data:
                    user_dict["hashed_password"] = get_password_hash(user_data["password"])
                    del user_data["password"]

                # Update user dict
                for key, value in user_data.items():
                    if key not in ["user_id", "hashed_password", "created_at"]:
                        user_dict[key] = value

                return UserOut(**user_dict)
        return None

    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        for username, user_dict in list(users_db.items()):
            if user_dict.get("user_id") == user_id:
                del users_db[username]
                return True
        return False

    async def get_user_dependency(self, token: str = Depends(oauth2_scheme)) -> User:
        """
        Dependency for getting the current user.

        Args:
            token: JWT token.

        Returns:
            User object if token is valid.
        """
        return await get_current_user(token, self.secret_key)

    async def get_active_user_dependency(self, user: User = Depends(get_current_user)) -> User:
        """
        Dependency for getting the current active user.

        Args:
            user: User from token.

        Returns:
            User object if active.
        """
        return await get_current_active_user(user)