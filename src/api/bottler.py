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

    num_ml_by_type = [0,0,0,0]
    for i in range(4):
        num_ml_by_type[i] = sum(potion.potion_type[i]*potion.quantity for potion in potions_delivered)

    for potion in potions_delivered:
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(
            """UPDATE potion_inventory SET 
            quantity = quantity + :delivered 
            WHERE potion_type = :potion_type"""
            ),
        [{"delivered": potion.quantity, "potion_type": potion.potion_type}]
        )

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """UPDATE global_inventory SET 
            num_red_ml = num_red_ml - :rml,
            num_green_ml = num_green_ml - :gml,
            num_blue_ml = num_blue_ml - :bml,
            num_dark_ml = num_dark_ml - :dml
            WHERE id = 1"""
            ),
        [{"rml": num_ml_by_type[0], "gml": num_ml_by_type[1],"bml": num_ml_by_type[2],"dml": num_ml_by_type[3]}]
        )
    return "OK"

    
#input: potion type to bottle and current ml
#output: returns true if we have enough ml to bottle one potion
def can_bottle(potion_type,cur_ml_list):
        for type,val in enumerate(cur_ml_list):
            if potion_type[type] > val:
                return False
        return True

def process():
    #step 1: select all the potions that need to be stocked
    #step 2: go through potion and check if can bottle
    #step 3: if we can't bottle then remove from table
    #step 4: if we can bottle then we add to json return list, update current_ml_levels
    #step 4: stop if the list is empty
    
    cur_ml_list = [0,0,0,0]
    plan_list= []

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT num_red_ml,num_green_ml,num_blue_ml,num_dark_ml FROM global_inventory WHERE id = 1"
        ))
        stock_tab = connection.execute(sqlalchemy.text(
            "SELECT quantity,potion_type,(max_potion-quantity) AS potion_needed FROM potion_inventory WHERE quantity < max_potion"
        ))
    
    res = tab.first()
    cur_ml_list = [res.num_red_ml,res.num_green_ml, res.num_blue_ml, res.num_dark_ml]

    #we have a stock table... later we can order based on info 
    stock_list = stock_tab.all()
    stock_list.sort(key= lambda x : (x[0],-x[2])) #sorts based on quantity then potion_needed(descending order)
    print(stock_list)

    i=0
    while len(stock_list) > 0:
        row = stock_list[i%len(stock_list)]
        #if we need more potions and we can bottle it...then add or update potion_count
        if row.potion_needed > 0 and can_bottle(row.potion_type,cur_ml_list):
            cur_ml_list = [cur_ml_list[i] - row.potion_type[i] for i in range(4)]
            #finds the element in the list, empty dict if not in the list
            cur = {}
            for elem in plan_list:
                if elem.get("potion_type") == row.potion_type:
                    cur = elem
            if cur == {}:
                plan_list.append(
                    {
                    "potion_type": row.potion_type,
                    "quantity": 1,
                    }
                )
            else:
                quant = cur.get("quantity") + 1
                cur["quantity"] = quant
            i+=1
            row.potion_needed -= 1
        else:
            stock_list.remove(row)
    return plan_list
        
            
            


# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into strictly red,blue,green potions.For now only these three potions...

    MAX_POTION = 20

    return process()

   