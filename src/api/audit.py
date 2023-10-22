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
            "SELECT COALESCE(SUM(quantity),0) FROM potion_ledger WHERE account_id = 1" 
        ))
        tab2 = connection.execute(sqlalchemy.text(
            "SELECT COALESCE(SUM(quantity),0) FROM gold_ledger WHERE account_id = 1"
        ))
        tab3 = connection.execute(sqlalchemy.text(
            "SELECT COALESCE(SUM(red_quantity),0)+COALESCE(SUM(green_quantity))+COALESCE(SUM(blue_quantity))+COALESCE(SUM(dark_quantity)) FROM ml_ledger WHERE account_id = 1"
        ))
        num_potions = tab.scalar_one()
        num_gold = tab2.scalar_one()
        num_ml =  tab3.scalar_one() 

         
    return {"number_of_potions": num_potions, "ml_in_barrels": num_ml, "gold": num_gold}

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
