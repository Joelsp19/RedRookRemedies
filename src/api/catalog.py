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
        
        id  = connection.execute(sqlalchemy.text(
        """
        with gr as (
        select sum(potion_type[1]) as r, sum(potion_type[2]) as g,sum(potion_type[3]) as b,sum(potion_type[4]) as d
        FROM potion_inventory AS pi
        LEFT JOIN potion_ledger AS pl ON pi.id = pl.potion_id
        JOIN cart_items AS ci ON ci.potion_inventory_id = pi.id
        JOIN carts ON carts.id = ci.cart_id
        WHERE carts.tick = :tick AND account_id = :own
        )
        select 
        case 
        when r = greatest(r,g,b,d) then 1
        when g = greatest(r,g,b,d) then 2
        when b = greatest(r,g,b,d) then 3
        when d = greatest(r,g,b,d) then 4
        end as index
        from gr;
        """
        ),[{"tick":utils.getCurTick(), "own":utils.OWNER_ID}])

        if id == 0:
            typeid = 1
        else:
            typeid = id.scalar_one()


        tab = connection.execute(sqlalchemy.text(
            """
            SELECT COALESCE(SUM(pl.quantity),0) AS potion_quantity,sku,name,price,potion_type, 
            CASE
            WHEN pl.potion_id IN (
              SELECT pi.id
              FROM potion_inventory as pi
              LEFT JOIN potion_ledger AS pl ON pi.id = pl.potion_id
              JOIN cart_items AS ci ON ci.potion_inventory_id = pi.id
              JOIN carts ON carts.id = ci.cart_id
              WHERE carts.tick = :tick and account_id = :own
            ) THEN 2
            WHEN pi.potion_type[:typeid] != 0 THEN 1
            ELSE 0
            END AS priority
            FROM potion_inventory as pi
            JOIN potion_ledger as pl ON pl.potion_id = pi.id
            WHERE account_id = :own
            GROUP BY potion_id, sku,name,price,potion_type
            HAVING COALESCE(SUM(pl.quantity),0) > 0
            ORDER BY priority DESC, potion_quantity DESC
            LIMIT 6

      
            """
        ),[{"tick":utils.getCurTick(), "own":utils.OWNER_ID, "typeid": typeid}])

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

