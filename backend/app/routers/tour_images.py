import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models import Tour, TourImage
from app.schemas.tour import TourImageRead, TourImageUpdate
from app.services.image_service import (
    delete_image_file,
    public_url,
    validate_and_store_image,
)

router = APIRouter()


def _serialize(image: TourImage) -> dict:
    return {
        "id": image.id,
        "tour_id": image.tour_id,
        "image_url": public_url(image.image_url),
        "image_alt": image.image_alt,
        "sort_order": image.sort_order,
        "use_as_thumbnail": image.use_as_thumbnail,
    }


@router.get(
    "/{tour_id}/images",
    response_model=list[TourImageRead],
)
async def list_images(
    tour_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(TourImage)
            .where(TourImage.tour_id == tour_id)
            .order_by(TourImage.sort_order, TourImage.id)
        )
    ).scalars().all()
    return [_serialize(r) for r in rows]


@router.post(
    "/{tour_id}/images",
    response_model=TourImageRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tour-image:edit"))],
)
async def upload_image(
    tour_id: uuid.UUID,
    file: UploadFile = File(...),
    image_alt: str = Form(..., min_length=1, max_length=255),
    sort_order: int = Form(0, ge=0),
    use_as_thumbnail: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    tour = (
        await db.execute(select(Tour).where(Tour.id == tour_id))
    ).scalar_one_or_none()
    if tour is None:
        raise HTTPException(status_code=404, detail="Tour not found")

    filename = await validate_and_store_image(file)

    image = TourImage(
        tour_id=tour_id,
        image_url=filename,
        image_alt=image_alt,
        sort_order=sort_order,
        use_as_thumbnail=use_as_thumbnail,
    )
    db.add(image)
    try:
        await db.commit()
    except Exception:
        delete_image_file(filename)
        raise
    await db.refresh(image)
    return _serialize(image)


@router.patch(
    "/{tour_id}/images/{image_id}",
    response_model=TourImageRead,
    dependencies=[Depends(require_permission("tour-image:edit"))],
)
async def update_image(
    tour_id: uuid.UUID,
    image_id: int,
    body: TourImageUpdate,
    db: AsyncSession = Depends(get_db),
):
    image = (
        await db.execute(
            select(TourImage).where(
                TourImage.id == image_id, TourImage.tour_id == tour_id
            )
        )
    ).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(image, field, value)

    await db.commit()
    await db.refresh(image)
    return _serialize(image)


@router.delete(
    "/{tour_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("tour-image:edit"))],
)
async def delete_image(
    tour_id: uuid.UUID,
    image_id: int,
    db: AsyncSession = Depends(get_db),
):
    image = (
        await db.execute(
            select(TourImage).where(
                TourImage.id == image_id, TourImage.tour_id == tour_id
            )
        )
    ).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    filename = image.image_url
    await db.delete(image)
    await db.commit()
    delete_image_file(filename)
    return None
