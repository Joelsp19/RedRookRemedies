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

    # Can return a max of 6 items.
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """SELECT * 
            FROM potion_inventory 
            ORDER BY quantity DESC
            LIMIT 6"""
        ))
        for row in tab:
            quant = row.quantity
            if quant != 0:
                catalog.append( {
                    "sku": row.sku,
                    "name": row.name,
                    "quantity": row.quantity,
                    "price": row.price,
                    "potion_type": row.potion_type
                })     
    print(catalog)
    return catalog