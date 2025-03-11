from src.server.auth import (OAuth2PasswordRequestForm, UserCreate,
                             UserManager, UserOut)


# Function to create FastAPI app with our routes
def create_api_app(vm_manager: VMManager, session_manager: SessionManager, user_manager: UserManager) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Autonomous Agent API")

    # Authentication routes
    @app.post("/token", response_model=Token)
    async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
        """API endpoint for getting an access token."""
        return await user_manager.get_token(form_data)

    # User routes
    @app.post("/users", response_model=UserOut)
    async def create_user(
        user_create: UserCreate,
        current_user = Depends(user_manager.get_active_user_dependency)
    ):
        """Create a new user."""
        # Check if the current user has admin role
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create users"
            )

        return await user_manager.create_user(user_create)

    @app.get("/users/me", response_model=UserOut)
    async def get_current_user_info(current_user = Depends(user_manager.get_active_user_dependency)):
        """Get information about the current user."""
        # Convert User to UserOut
        return UserOut(
            user_id=current_user.user_id,
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            disabled=current_user.disabled,
            role=current_user.role,
            created_at=current_user.created_at
        )

    @app.get("/users", response_model=List[UserOut])
    async def list_users(current_user = Depends(user_manager.get_active_user_dependency)):
        """List all users."""
        # Check if the current user has admin role
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to list users"
            )

        return await user_manager.list_users()

    # ... existing session routes ...

    # Update session routes to use user authentication
    @app.post("/sessions", response_model=CreateSessionResponse)
    async def create_session(
        request: CreateSessionRequest,
        current_user = Depends(user_manager.get_active_user_dependency)
    ):
        """Create a new agent session."""
        session = await session_manager.create_session(
            user_id=current_user.user_id,
            goal=request.goal
        )

        return CreateSessionResponse(
            session_id=session.session_id,
            status=session.status
        )

    @app.get("/sessions/{session_id}", response_model=SessionStatusResponse)
    async def get_session(
        session_id: str,
        current_user = Depends(user_manager.get_active_user_dependency)
    ):
        """Get status information for a session."""
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.user_id != current_user.user_id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized to access this session")

        # Update last active time
        await session_manager.update_session_activity(session_id)

        # Get VM status if available
        vm_status = None
        if session.vm_id:
            vm_status = await vm_manager.get_vm_status(session.vm_id)

        return SessionStatusResponse(
            session_id=session.session_id,
            status=session.status
        )