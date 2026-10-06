from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from ninja import Router
from ninja.errors import HttpError

from apps.accounts import selectors, services
from apps.accounts.permissions import admin_only, authenticated
from apps.accounts.schemas import (
    LoginIn,
    RefreshIn,
    TeacherRegisterIn,
    TokenPairOut,
    UserCreateIn,
    UserOut,
    UserUpdateIn,
)
from core.errors import validation_error
from core.jwt import TokenError, create_token_pair, decode_token


public_router = Router(tags=["Autenticacion"])
auth_router = Router(tags=["Autenticacion"], auth=authenticated)
admin_router = Router(tags=["Administracion de usuarios"], auth=admin_only)


@auth_router.post("/login", response=TokenPairOut, auth=None)
def login(request, payload: LoginIn):
    email = payload.email.strip().lower()
    user = authenticate(request, username=email, password=payload.password)
    if user is None:
        raise HttpError(401, "Credenciales invalidas.")
    return create_token_pair(user)


@auth_router.post("/refresh", response=TokenPairOut, auth=None)
def refresh_token(request, payload: RefreshIn):
    try:
        claims = decode_token(payload.refresh, expected_type="refresh")
    except TokenError as exc:
        raise HttpError(401, str(exc)) from exc

    user = selectors.active_user(claims["sub"])
    if user is None:
        raise HttpError(401, "El usuario del token no existe o esta inactivo.")
    return create_token_pair(user)


@public_router.post("/register/teacher", response=UserOut)
def register_teacher(request, payload: TeacherRegisterIn):
    try:
        return services.register_teacher(**payload.model_dump())
    except ValidationError as exc:
        raise validation_error(exc) from exc


@auth_router.get("/me", response=UserOut)
def me(request):
    return request.auth


@admin_router.get("/users", response=list[UserOut])
def list_users(request, buscar: str = None):
    return selectors.users(search=buscar)


@admin_router.post("/users", response=UserOut)
def create_user(request, payload: UserCreateIn):
    try:
        return services.create_user(**payload.model_dump())
    except ValidationError as exc:
        raise validation_error(exc) from exc


@admin_router.patch("/users/{user_id}", response=UserOut)
def update_user(request, user_id: int, payload: UserUpdateIn):
    target = selectors.user(user_id)
    try:
        return services.update_user(target, changes=payload.model_dump(exclude_unset=True))
    except ValidationError as exc:
        raise validation_error(exc) from exc
