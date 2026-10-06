from ninja import NinjaAPI

from apps.accounts.views import admin_router, auth_router, public_router


api = NinjaAPI(
    title="CampusLab API",
    version="1.0.0",
    description="API de CampusLab.",
)

api.add_router("", public_router)
api.add_router("/auth", auth_router)
api.add_router("/admin", admin_router)


@api.get("/health", auth=None)
def health(request):
    return {"status": "ok"}