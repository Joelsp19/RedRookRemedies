from fastapi import APIRouter
import sqlalchemy
from src import database as db
from src import utils

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    catalog = []

    #catalog now considers previous info when showcasing catalog items
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """
            SELECT potion_quantity,sku,name,price,potion_type
            FROM(
            SELECT COALESCE(SUM(pl.quantity),0) AS potion_quantity,sku,name,price,potion_type, 1 as priority
            FROM potion_inventory as pi
            LEFT JOIN potion_ledger AS pl ON pi.id = pl.potion_id
            JOIN cart_items AS ci ON ci.potion_inventory_id = pi.id
            JOIN carts ON carts.id = ci.cart_id
            WHERE carts.tick = :tick and account_id = :own
            GROUP BY pi.id,sku,name,price,potion_type

            UNION
            
            SELECT COALESCE(SUM(pl.quantity),0) AS potion_quantity,sku,name,price,potion_type, 0 as priority
            FROM potion_ledger as pl
            JOIN potion_inventory ON potion_id = potion_inventory.id
            WHERE account_id = :own
            GROUP BY potion_id, sku,name,price,potion_type
            )as subquery

            ORDER BY priority DESC, potion_quantity DESC
            LIMIT 6
      
            """
        ),[{"tick":utils.getCurTick(), "own":utils.OWNER_ID}])

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

    ### CATALOG LOGGING ###

    with db.engine.begin() as connection:
        id = connection.execute(sqlalchemy.text(
            """
            INSERT INTO catalog_transactions DEFAULT VALUES
            RETURNING id
            """
        ))

        bt_id = id.scalar_one()
        for potion in catalog:
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO log_catalog
                (potion_sku,quantity,price,ct_id)
                VALUES
                (:p_sku,:q,:p,:ct_id)
                """ 
            ),[{"p_sku":potion["sku"],"q":potion["quantity"],"p":potion["price"],"ct_id": bt_id}])


    print(catalog)
    return catalog

