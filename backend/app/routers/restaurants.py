"""Public browsing: restaurants, their menus and reviews. No login needed."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import MenuItem, Restaurant, Review
from ..schemas import MenuItemOut, Page, RestaurantOut, ReviewOut
from ..services import paginate, review_to_out

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


def rating_info(db: Session, restaurant_ids: list[int]) -> dict[int, tuple[float | None, int]]:
    """Average rating and review count per restaurant, in one GROUP BY query."""
    if not restaurant_ids:
        return {}
    rows = db.execute(
        select(Review.restaurant_id, func.avg(Review.rating), func.count(Review.id))
        .where(Review.restaurant_id.in_(restaurant_ids))
        .group_by(Review.restaurant_id)
    ).all()
    ratings = {}
    for restaurant_id, avg_rating, review_count in rows:
        ratings[restaurant_id] = (round(avg_rating, 1), review_count)
    return ratings


def to_out(restaurant: Restaurant, ratings: dict) -> RestaurantOut:
    """Build a RestaurantOut using precomputed ratings from rating_info()."""
    # Restaurants with no reviews yet get no average and a count of 0
    avg_rating, review_count = ratings.get(restaurant.id, (None, 0))
    return RestaurantOut(
        id=restaurant.id, name=restaurant.name, description=restaurant.description, cuisine=restaurant.cuisine,
        address=restaurant.address, is_open=restaurant.is_open, avg_rating=avg_rating, review_count=review_count,
    )


@router.get("", response_model=Page[RestaurantOut])
def list_restaurants(
    search: str | None = Query(None, description="Matches restaurant name or cuisine"),
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """List restaurants alphabetically, optionally searching by name or cuisine."""
    query = select(Restaurant).order_by(Restaurant.name)
    if search:
        # % matches any text, so this finds the search term anywhere in the name or cuisine
        pattern = f"%{search.strip()}%"
        query = query.where(Restaurant.name.ilike(pattern) | Restaurant.cuisine.ilike(pattern))
    rows, total, pages = paginate(db, query, page, size)
    # Ratings for the whole page in one query, avoiding one query per restaurant
    ratings = rating_info(db, [restaurant.id for restaurant in rows])
    items = [to_out(restaurant, ratings) for restaurant in rows]
    return Page[RestaurantOut](items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    """Show one restaurant with its rating summary."""
    restaurant = db.get(Restaurant, restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return to_out(restaurant, rating_info(db, [restaurant.id]))


@router.get("/{restaurant_id}/menu", response_model=list[MenuItemOut])
def get_menu(
    restaurant_id: int,
    search: str | None = Query(None, description="Search dish names"),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    veg_only: bool = False,
    sort: str = Query("category", pattern="^(category|price_asc|price_desc|name)$"),
    db: Session = Depends(get_db),
):
    """List a restaurant's dishes with optional search, price, veg filters and sorting."""
    if db.get(Restaurant, restaurant_id) is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    query = select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)
    if search:
        query = query.where(MenuItem.name.ilike(f"%{search.strip()}%"))
    if min_price is not None:
        query = query.where(MenuItem.price >= min_price)
    if max_price is not None:
        query = query.where(MenuItem.price <= max_price)
    if veg_only:
        query = query.where(MenuItem.is_veg.is_(True))

    # Turn the sort option into ORDER BY columns (the pattern on `sort` allows only these four)
    if sort == "category":
        query = query.order_by(MenuItem.category, MenuItem.name)
    elif sort == "price_asc":
        query = query.order_by(MenuItem.price)
    elif sort == "price_desc":
        query = query.order_by(MenuItem.price.desc())
    else:  # "name"
        query = query.order_by(MenuItem.name)
    return db.scalars(query).all()


@router.get("/{restaurant_id}/reviews", response_model=Page[ReviewOut])
def get_reviews(
    restaurant_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """List a restaurant's reviews, newest first."""
    query = (
        select(Review)
        .options(selectinload(Review.customer))
        .where(Review.restaurant_id == restaurant_id)
        .order_by(Review.created_at.desc())
    )
    rows, total, pages = paginate(db, query, page, size)
    items = [review_to_out(review) for review in rows]
    return Page[ReviewOut](items=items, total=total, page=page, size=size, pages=pages)
