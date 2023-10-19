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


#input: amt needed with current values [r,g,b,d]
#output: a list of amt_needed with indices(used later) -->  [rnew,gnew,...]
def det_amt_needed(amt_list):
    amt_needed_list = amt_list.copy()

    #selects the potions that need to be restocked
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT (max_potion- quantity) AS quant_needed,potion_type FROM potion_inventory WHERE quantity < max_potion"
        ))
 
    #updates the amt needed per type
    for row in tab:
        for i in range(len(row.potion_type)):
            amt_needed_list[i] += row.potion_type[i]*row.quant_needed

    return amt_needed_list        

#input: priority list: uses past experience to determine, amt_needed --> [r_need,g_need,...]
#output: a list of amt_needed in the order of what we should buy first --> [(2,b_need),(0,r_need),...]
def det_type_priority(priority,amt_needed):

    #default [3,2,1,0]
    #since red= 0 index, it has the greatest priority
    #dark = 3 index, it has the least priority
    default = [3,2,1,0]
    hour = getCurTick()%24
    if hour > 0 and hour < 12:
        default[3] = 4 #changes to highest priority

    #now amt_needed represents the ml needed per transaction
    #next we'll sort this list based on our priorities
    #1.greatest to least
    #1b.prioritize based on previous transactions(2 ticks from now)
    #1c.prioritize by default
    
    #changing the order of priorities can help the shop do better at diff times...
    # if we prioritize previous transactions, then we are reliably making the potions that we know will sell 
    # if we prioritize stocking the shop, then we focus on making sure we have enough resources
    # if we prioritize the default, then we can manually choose what potions to buy at the next tick

    sorted_list = [[0,amt_needed[0]],[1,amt_needed[1]],[2,amt_needed[2]],[3,amt_needed[3]]] #will store how much ml we need to fully restock our store
    sorted_list.sort(key = lambda x: (priority[x[0]],x[1],default[x[0]]), reverse=True) 
    return sorted_list

#input: the remaining budget, the index of the type, amt needed per type, catalog, a list of indices of types we already bought
#output: the budget for the given type 
def det_type_budget(type_index,budget,amt_needed,catalog,priority_list):

    ### LOGIC 2: Ensure enough to buy the "least" of every type we need to buy
    #Pros: good for when we starting out and not that much gold... buys multiple barrels
    #Cons: we need to find the least of each type... lots of computation ... may not fully capitalize
    #still are cases where won't be fully capitalized 

    cheap_list = find_cheap_barrel(catalog)
    sub_sum = 0
    for val in priority_list:
        index = val[0]
        #subtracts from the budget only if we need this type(amt_needed > 0) 
        #and we can still afford a barrel of our current type
        if amt_needed > 0 and budget - (sub_sum + cheap_list[index]) > cheap_list[type_index]:
            sub_sum += cheap_list[index]
    return budget - sub_sum

    """
    ### LOGIC 1: Split based on need 
    #*** params are different so need to refactor to reimplement
    #Pros: ensures each barrel gets consideration
    #Cons: if we broke, then won't end up buying anything
    tot_amt_needed = sum(amt_needed[i] for i in range(4)) 
    for i in range(len(amt_needed)):
        if amt_needed[i] <= 0:
            amt = 0
        else:
            amt = amt_needed[i]
        budget_list[i] = math.floor(budget * amt/tot_amt_needed)
    return budget_list
    """

#input: finds the cheapest barrels that are needed
#output: an integer representing the cheapest barrel of a type
def find_cheap_barrel(catalog):

    cheap_list = [-1,-1,-1,-1] # assume that no barrel price will be negative
    for barrel in catalog:
        #get the index corresponding to the type
        type = barrel.potion_type.index(1) #type is 0 for red, 1 for green, 2 for blue, 3 for dark
        if cheap_list[type] == -1:
            cheap_list[type] = barrel.price
        else:
            cheap_list[type] = min(cheap_list[type],barrel.price)
    return cheap_list

#input:none
#output: the current tick
def getCurTick():
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """
            SELECT FLOOR((EXTRACT(HOUR FROM now())+2)/2) + (EXTRACT(ISODOW FROM now())-1)*12 AS tick
            """
        ))
    return tab.scalar_one()

#determines the priority using past experience selling at this tick... if no past experience priority based off other priority 
#input: current amount of ml in inventory --> [r_ml,g_ml,b_ml,d_ml] (will be negative values since this represents amt we want to buy)
#output: the amount of ml we need for each type (will be used as a priority list) --> [r,g,b,d]
def det_potion_priority(amt_list):

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """SELECT (cart_items.quantity - potion_inventory.quantity ) AS quant_needed,potion_type
            FROM cart_items
            JOIN potion_inventory ON cart_items.potion_inventory_id = potion_inventory.id
            WHERE potion_inventory.id IN  (
                SELECT cart_items.potion_inventory_id
                FROM carts
                JOIN cart_items ON carts.id = cart_items.cart_id
                WHERE carts.tick = :cur_tick +2
            )
            AND potion_inventory.quantity  < cart_items.quantity
            
            """
        ),[{"cur_tick" : getCurTick()}]
        )
    

    res = tab.all()
    print(getCurTick())
    print(res)
    if res != []:
        for row in res:
            for i in range(len(row.potion_type)): 
                amt_list[i] += row.potion_type[i]*row.quant_needed  
        return amt_list
    else:
        return [0,0,0,0]

#input: type --> [1,0,0,0] for red, budget for a type, amount needed for a type, entire wholesale catalog
#output: a list of json objects with barrels to buy of this type and quantity to buy of each one and the budget
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
        print(f"max: {quantity_max},bar : {barrel.quantity},aff: {quantity_afford}")
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
    #step 1: get info from global inventory
    #step 2: get the amt needed to stock up
    #step 2b: get the priority based on previous info (won't matter if none)
    #step 2c: get the priority list to determine order of buying barrels
    #step 2d: find the budget for each typ
    #step 3: for all values in the priority list, buy the barrel, and get barrel list
    #step 4: add all the barrel lists

    tot_barrel_list = []

    with db.engine.begin() as connection:
            tab = connection.execute(sqlalchemy.text(
                "SELECT * FROM global_inventory"
            ))
    result = tab.first()
    tot_budget = result.gold
    cur_amt = [-result.num_red_ml,-result.num_green_ml,-result.num_blue_ml,-result.num_dark_ml] #will store how much ml we need to fully restock our store

    print(cur_amt)
    amt_needed_list = det_amt_needed(cur_amt) #amt needed to stock up each type
    priority = det_potion_priority(cur_amt) #a priority list
    priority_list = det_type_priority(priority,amt_needed_list) #sorted amt_needed list 
    print(f"amt_needed: {amt_needed_list} priority: {priority} priority_list = {priority_list}") 

    budget = tot_budget

    #goes through priority list in order
    for i,val in enumerate(priority_list):
        type = [0,0,0,0]
        type_index = val[0]
        type[type_index ] = 1 #this represents the array repr of type -->  [1,0,0,0] represents red
        amt_needed = val[1]
        tmp = budget
        budget = det_type_budget(type_index,budget,amt_needed,wholesale_catalog,priority_list[i+1:]) #grabs the budget corresponding with type 
        extra = tmp - budget
        result = buy_barrel(type,budget,amt_needed,wholesale_catalog)
        tot_barrel_list += result[0] #updates the list of barrels to buy
        budget = result[1]+ extra #updates the budget
    
    return tot_barrel_list


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    #can move process into here once its confirmed to work...
    print(wholesale_catalog)
    print("-----")
    return process(wholesale_catalog)

    