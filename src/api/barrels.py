from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db


router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """
    print(barrels_delivered)

    red_ml = 0
    cost = 0

    for barrel in barrels_delivered:
        cost += barrel.price
        red_ml += barrel.ml_per_barrel

    with db.engine.begin() as connection:
            tab = connection.execute(sqlalchemy.text(
                "SELECT num_red_ml,gold FROM global_inventory"
            ))
            result = tab.first()
            new_red_ml = result.num_red_ml + red_ml
            new_gold = result.gold - cost
            connection.execute(sqlalchemy.text(
                "UPDATE global_inventory SET num_red_ml = '%s', gold = '%s' WHERE id = 1" % (new_red_ml,new_gold)
            ))
        
    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)


    with db.engine.begin() as connection:
            tab = connection.execute(sqlalchemy.text(
                "SELECT nun_red_ml, gold FROM global_inventory"
            ))
    result = tab.first()
    red_ml_quantity = result.num_red_ml
    cur_gold = result.gold

    # determines if we should buy or not
    #currently only one thing in wholesale catalog and it costs 25

    if red_ml_quantity < 10 and cur_gold > 25:
        to_buy = 1
    else:
        return []

    return [
        {
            "sku": wholesale_catalog[0].sku,
            "quantity": to_buy,
        }
    ]
