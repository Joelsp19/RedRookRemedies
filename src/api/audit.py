from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT SUM(quantity) AS num_potions FROM potion_inventory"
        ))
        num_potions = tab.first().num_potions
        tab2 = connection.execute(sqlalchemy.text(
            "SELECT * FROM global_inventory WHERE id = 1"
        ))
        res = tab2.first()
        num_gold = res.gold
        tot_ml = res.num_red_ml + res.num_green_ml + res.num_blue_ml

    return {"number_of_potions": num_potions, "ml_in_barrels": tot_ml, "gold": num_gold}

class Result(BaseModel):
    gold_match: bool
    barrels_match: bool
    potions_match: bool

# Gets called once a day
@router.post("/results")
def post_audit_results(audit_explanation: Result):
    """ """
    print(audit_explanation)

    return "OK"
