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

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT num_red_ml,num_green_ml,num_blue_ml FROM global_inventory"
        ))
        result = tab.first()
        num_ml_by_type = [result.num_red_ml, result.num_green_ml, result.num_blue_ml]
        for potion in potions_delivered:
            p_type = potion.potion_type
            p_quantity = potion.quantity
            #updates the total ml after selling the potion
            for i in range(len(p_type)-1):
                num_ml_by_type[i] -= p_type[i]*p_quantity
            #find the id of potion_type in the potion inventory and the cur quant of potions
            p_tab = connection.execute(sqlalchemy.text(
                "SELECT id,quantity FROM potion_inventory WHERE potion_type = ARRAY%s" % (str(p_type))  
            ))
            p_res= p_tab.first()
            p_quant_new = p_res.quantity + p_quantity
            connection.execute(sqlalchemy.text(
            "UPDATE potion_inventory SET quantity = '%s' WHERE id = '%s'" % (p_quant_new,p_res.id)
            ))
        
        connection.execute(sqlalchemy.text(
            "UPDATE global_inventory SET num_red_ml = '%s', num_green_ml = '%s', num_blue_ml = '%s' WHERE id = 1" % (num_ml_by_type[0],num_ml_by_type[1],num_ml_by_type[2])
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

    # Initial logic: bottle all barrels into strictly red,blue,green potions.For now only these three potions...

    MAX_POTION = 20

    plan_list = []

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT num_red_ml, num_blue_ml, num_green_ml FROM global_inventory"
        ))
        p_tab = connection.execute(sqlalchemy.text(
            "SELECT quantity,potion_type FROM potion_inventory WHERE quantity < '%s'" % (MAX_POTION)
        ))
    result = tab.first()
    cur_ml_by_type = [result.num_red_ml, result.num_green_ml, result.num_blue_ml]
    #currently order is random based on what the query returns... we can change to give priority to some potions
    for row in p_tab:
        print(row)
        max_quant = [0,0,0]
        for i in range(len(row.potion_type)-1):
            if row.potion_type[i] > 0:
                max_quant[i] = cur_ml_by_type[i] // row.potion_type[i]
            else:
                max_quant[i] = MAX_POTION+1 #essentially infinity b/c we don't need any resources to make
        quantity = min(max_quant[0], max_quant[1],max_quant[2],MAX_POTION-row.quantity)
        print(cur_ml_by_type)
        print(max_quant)
        print(quantity)
        for i in range(len(cur_ml_by_type)):
            cur_ml_by_type[i] -= quantity * row.potion_type[i]
        if quantity > 0:
            plan_list.append(
                {
                "potion_type": row.potion_type,
                "quantity": quantity,
                }
            )
                    
    return plan_list
