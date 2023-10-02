from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db


router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print(potions_delivered)

    num_potions = 0
    
    for potion in potions_delivered:
        num_potions += potion.quantity

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT num_red_potions, num_red_ml FROM global_inventory"
        ))
        result = tab.first()
        new_potions = result.num_red_potions + num_potions
        new_red_ml = result.num_red_ml- (num_potions*100)
        connection.execute(sqlalchemy.text(
            "UPDATE global_inventory SET num_red_ml = '%s', num_red_potions = '%s' WHERE id = 1" % (new_red_ml,new_potions)
            ))

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT num_red_ml FROM global_inventory"
        ))
        result = tab.first()
        quantity = result.num_red_ml // 100
    return [
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": quantity,
            }
        ]
