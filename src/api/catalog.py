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

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(potion_ledger.quantity) AS potion_quantity,sku,name,price,potion_type
            FROM potion_ledger
            JOIN potion_inventory ON potion_id = potion_inventory.id
            WHERE account_id = 1
            GROUP BY potion_id, sku,name,price,potion_type
            ORDER BY potion_quantity DESC
            LIMIT 6"""
        ))

    for row in tab:
            quant = row.potion_quantity
            if quant > 0:
                catalog.append( {
                    "sku": row.sku,
                    "name": row.name,
                    "quantity": row.potion_quantity,
                    "price": row.price,
                    "potion_type": row.potion_type
                })     

    print(catalog)
    return catalog

