from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    catalog = []

    # Can return a max of 20 items.
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT * FROM potion_inventory LIMIT 20"
        ))
        for row in tab:
            quant = row.quantity
            if quant != 0:
                catalog.append( {
                    "sku": row.sku,
                    "name": row.name,
                    "quantity": row.quantity,
                    "price": row.price,
                    "potion_type": row.type
                })     

    return catalog