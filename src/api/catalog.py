from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    # Can return a max of 20 items.
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT num_red_potions FROM global_inventory LIMIT 20"
        ))
        result = tab.first()
        red_quantity = result.num_red_potions


    return [
            {
                "sku": "RED_POTION_0",
                "name": "red potion",
                "quantity": red_quantity,
                "price": 50,
                "potion_type": [100, 0, 0, 0],
            }
        ]
