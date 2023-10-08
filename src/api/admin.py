from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            "UPDATE global_inventory SET num_red_ml = '%s', num_green_ml = '%s',  num_blue_ml = '%s', gold = '%s' WHERE id = 1" % (0,0,0,100)
        ))

        connection.execute(sqlalchemy.text(
            "UPDATE potion_inventory SET quantity = '%s' " % (0)
        ))

    return "OK"


@router.get("/shop_info/")
def get_shop_info():
    """ """

    # TODO: Change me!
    return {
        "shop_name": "Red Rook Remedies",
        "shop_owner": "Joel Puthankalam",
    }

