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
        type = barrel.potion_type.index(1) #type is 0 for red, 1 for green, 2 for blue, 3 for dark
        if type not in range(4):
            raise Exception("Not a valid barrel")
        num_ml_per_type[type] += (barrel.ml_per_barrel * barrel.quantity)

    with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                """
                UPDATE global_inventory SET 
                num_red_ml = num_red_ml + :rml,
                num_green_ml = num_green_ml + :gml,
                num_blue_ml = num_blue_ml + :bml,
                num_dark_ml = num_dark_ml + :dml,
                gold = gold - :cost
                WHERE id=1
                """),
            [{"rml" :num_ml_per_type[0], "gml" : num_ml_per_type[1], "bml" : num_ml_per_type[2], "dml" : num_ml_per_type[3], "cost" : cost}]
            )
        
    print(f"rml: {num_ml_per_type[0]} gml: {num_ml_per_type[1]} bml: {num_ml_per_type[2]} dml: {num_ml_per_type[3]} gold_cost: {cost}")
    return "OK"


#input: priority list: default- [3,2,1,0] gives priority rgbd
#output: a list of amt_needed in the order of what we should buy first
def det_amt_needed(priority):
    #budget_per_type_list = [0,0,0,0] #keeps track of our budget for each type of ml
    amt_needed = [[0,0],[1,0],[2,0],[3,0]] #will store how much ml we need to fully restock our store

    #selects the potions that need to be restocked
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT quantity,potion_type FROM potion_inventory WHERE quantity < max_potion"
        ))
 
    #updates the amt needed per type
    for row in tab:
        for i in range(len(row.potion_type)):
            amt_needed[i][1] += row.potion_type[i]        

    #now amt_needed represents the ml needed per transaction
    #next we'll sort this list based on our priorities
    #1.greatest to least
    #2.prioritize the potions with the worst max_potion/quantity ratio(need to implement)
    #3.prioritize by rgbd
    sorted_list = amt_needed.copy()
    sorted_list.sort(key = lambda x: (x[1], priority[x[0]]), reverse=True) #greatest to least and then by priority list
    return sorted_list

#input: type(RGBD), budget for a type, amount needed for a type, entire wholesale catalog,
#output: a list of json objects with barrels to buy of this type and quantity to buy of each one
# and a remaining budget 
def buy_barrel(type,budget,amt_needed,catalog):
    #step 1: find the correct type
    #step 2: find the unit price
    #step 3: add to index_list (index in wholesale catalog)
    #step 4: sort the index_list
    #step 5: buy as many as we need/can and then move onto the next one

    barrels_to_buy =[]
    type_list = [] #the indices of all barrels of a type from a catalog
    for i,barrel in enumerate(catalog):
        if barrel.potion_type == type:
            unit_price = barrel.price/barrel.ml_per_barrel
            type_list.append([i,unit_price])
    #now we have all the indices of the barrels of our given type
    type_list.sort(key=lambda x: x[1])
    for b in type_list:
        barrel = catalog[b[0]]
        quantity_max = math.ceil(amt_needed / barrel.ml_per_barrel)
        quantity_afford = budget // barrel.price
        quantity_buy = min(quantity_max, barrel.quantity,quantity_afford)
        print(f"type: {type} b: {b} amt needed: {amt_needed} barrel ml: {barrel.ml_per_barrel} budget: {budget} barrel price {barrel.price}")
        print(f"max: {quantity_max},buy : {quantity_buy},aff: {quantity_afford}")
        amt_needed -= barrel.ml_per_barrel * quantity_buy
        budget -= barrel.price * quantity_buy
        if quantity_buy > 0:
            item = {"sku": barrel.sku,
                    "ml_per_barrel" : barrel.ml_per_barrel,
                    "potion_type": barrel.potion_type,
                    "price": barrel.price,
                    "quantity": quantity_buy,}
            barrels_to_buy.append(item)
        if amt_needed <= 0 or budget <= 0:
            break
    print(f"done with this type")
    return [barrels_to_buy,budget]
        
    
def process(wholesale_catalog):
    #step 1: get the amt of gold from database
    #step 2: get the priority list 
    #step 3: for all values in the priority list, buy the barrel, and get barrel list
    #step 4: add all the barrel lists

    #default [3,2,1,0]
    #since red= 0 index, it has the greatest priority
    #dark = 3 index, it has the least priority
    priority = [2,1,3,0] 
    tot_barrel_list = []

    with db.engine.begin() as connection:
            tab = connection.execute(sqlalchemy.text(
                "SELECT gold FROM global_inventory"
            ))
    result = tab.first()
    budget = result.gold

    priority_list = det_amt_needed(priority)
    for val in priority_list:
        type = [0,0,0,0]
        type[val[0]] = 1 #this creates the array repr type ... [1,0,0,0]
        amt_needed = val[1]
        result = buy_barrel(type,budget,amt_needed,wholesale_catalog)
        tot_barrel_list += result[0] #updates the list of barrels to buy
        budget = result[1] #updates the budget
        
    
    return tot_barrel_list


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    #can move process into here once its confirmed to work...
    print(wholesale_catalog)
    return process(wholesale_catalog)

    