import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    auth,
    bookings,
    reports,
    tour_images,
    tour_slots,
    tours,
    webhooks,
)
from app.services.booking_ttl import ttl_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    task = asyncio.create_task(ttl_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await task


app = FastAPI(title="Lolo Tours API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(tours.router, prefix="/api/tours", tags=["tours"])
app.include_router(tour_images.router, prefix="/api/tours", tags=["tour-images"])
app.include_router(tour_slots.router, prefix="/api/tour-slots", tags=["tour-slots"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])

# Dev-only static serving for uploaded images. In production nginx serves these
# directly out of /var/lib/lolo-tours/uploads/tour-images/.
_tour_images_dir = Path(settings.upload_dir) / "tour-images"
_tour_images_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    settings.image_url_prefix,
    StaticFiles(directory=_tour_images_dir),
    name="tour-images",
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
