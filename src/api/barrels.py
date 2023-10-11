from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
import math
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

    num_ml_per_type = [0,0,0,0]
    cost = 0

    for barrel in barrels_delivered:
        cost += (barrel.price*barrel.quantity)
        type = barrel.potion_type.index(1) #type is 0 for red, 1 for blue, 2 for green, 3 for dark
        num_ml_per_type[type] += (barrel.ml_per_barrel * barrel.quantity)

    with db.engine.begin() as connection:
            tab = connection.execute(sqlalchemy.text(
                "SELECT * FROM global_inventory"
            ))
            result = tab.first()
            new_red_ml = result.num_red_ml + num_ml_per_type[0]
            new_green_ml = result.num_green_ml + num_ml_per_type[1]
            new_blue_ml = result.num_blue_ml + num_ml_per_type[2]
            new_gold = result.gold - cost
            connection.execute(sqlalchemy.text(
                "UPDATE global_inventory SET num_red_ml = '%s', num_green_ml = '%s', num_blue_ml = '%s', gold = '%s' WHERE id = 1" % (new_red_ml,new_green_ml,new_blue_ml,new_gold)
            ))
        
    return "OK"

temp_count = 0

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    #temp solution to ensure blue and green ml is bought...
    global temp_count
    temp_count+=1
    index_to_buy = temp_count%3
    print(index_to_buy)
    
    barrels_to_buy = []

    with db.engine.begin() as connection:
            tab = connection.execute(sqlalchemy.text(
                "SELECT * FROM global_inventory"
            ))
    result = tab.first()
    cur_gold = result.gold
    
    budget = math.floor(1*cur_gold)
    #num_ml_list = [result.num_red_ml, result.num_green_ml, result.num_blue_ml, result.num_dark_ml]
    budget_per_type_list = [0,0,0,0]
    budget_per_type_list[index_to_buy] = budget

    #logic to buy what potions we need the most... 
    '''
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT quantity,potion_type FROM potion_inventory WHERE quantity = (SELECT MIN(quantity) FROM potion_inventory)"
        ))
    amt_needed = [-1,-1,-1,-1]
    for row in tab:
        for i in range(len(row.potion_type)-1):
            amt_needed[i] += row.potion_type[i]
    max_needed = max(amt_needed) #gives us what we need the most
    if max_needed > 0:
        type = amt_needed.index(max(amt_needed)) #will be the first instance so default order is RGB
        if type < 0 or type > 2:
            type = 2 # if dark is the max amt that we need 
        budget_per_type_list[type] = budget
    else: #we are all stocked up don't update our budget...we can return an empty list
        return [] 
    '''          
    best_per_type_list = [[-1,budget_per_type_list[0]],[-1,budget_per_type_list[1]],[-1,budget_per_type_list[2]],[-1,budget_per_type_list[3]]]

    #for now we just buy the best *affordable value of each type of barrel from catalog
    #3 types of barrels
    for index, barrel in enumerate(wholesale_catalog):
        unit_price = barrel.price/barrel.ml_per_barrel
        type = barrel.potion_type.index(1) #type is 0 for red, 1 for blue, 2 for green, 3 for dark
        if type < 0 or type > 2:
            continue
        #if its a better unit price and at least one barrel is in the budget...
        if unit_price <= best_per_type_list[type][1] and barrel.price <= budget_per_type_list[type]:
            best_per_type_list[type] = [index,unit_price] 

    #creates the json purchase plan
    for index,val in enumerate(best_per_type_list):
        b_index = val[0]
        if b_index != -1:
            barrel = wholesale_catalog[b_index]
            want = budget_per_type_list[index] // barrel.price
            quant_buy = min(want,barrel.quantity)
            item = {"sku": barrel.sku,
                    "ml_per_barrel" : barrel.ml_per_barrel,
                    "potion_type": barrel.potion_type,
                    "price": barrel.price,
                    "quantity": quant_buy,}
            barrels_to_buy.append(item)

    return barrels_to_buy
