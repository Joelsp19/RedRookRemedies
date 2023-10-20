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
            "SELECT COALESCE(SUM(quantity)) FROM potion_ledger"
        ))
        tab2 = connection.execute(sqlalchemy.text(
            "SELECT COALESCE(SUM(quantity)) FROM gold_ledger"
        ))
        tab3 = connection.execute(sqlalchemy.text(
            "SELECT COALESCE(SUM(quantity)) FROM ml_ledger"
        ))
        num_potions = tab.scalar_one()
        num_gold = tab2.scalar_one()
        num_ml =  tab3.scalar_one() 
        
        #in the case where no rows are returned...
        num_ml = 0 if num_ml == None else num_ml
        num_gold = 0 if num_gold == None else num_gold
        num_potions = 0 if num_potions == None else num_potions         
        
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
