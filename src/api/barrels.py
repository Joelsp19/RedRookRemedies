from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
import math
from src import database as db
from src import utils

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
    num_barrels = 0

    for barrel in barrels_delivered:
        cost += (barrel.price*barrel.quantity)
        type = barrel.potion_type.index(1) #type is 0 for red, 1 for green, 2 for blue, 3 for dark
        if type not in range(4):
            raise Exception("Not a valid barrel")
        num_ml_per_type[type] += (barrel.ml_per_barrel * barrel.quantity)
        num_barrels += barrel.quantity

    #create new transaction
    #add to ml_ledger and subtract from gold_ledger

    with db.engine.begin() as connection:
            t_id = connection.execute(sqlalchemy.text(
                """
                INSERT INTO transactions
                (description)
                SELECT a.name || ' buys :tot_barrels barrels from ' || b.name || ' for :cost gold'
                FROM accounts AS a
                JOIN accounts AS b ON a.id = :own AND b.id = :bar
                RETURNING transactions.id
                """

            ), [{"tot_barrels" : num_barrels, "cost": cost, "own": utils.OWNER_ID, "bar" : utils.BARRELER_ID}]
            )
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO ml_ledger
                (red_quantity,green_quantity,blue_quantity,dark_quantity,transaction_id,account_id)
                VALUES
                (:rml,:gml,:bml,:dml,:t_id,:own),
                (-:rml,-:gml,-:bml,-:dml,:t_id,:bar);

                INSERT INTO gold_ledger
                (quantity,transaction_id,account_id)
                VALUES
                (-:cost,:t_id,:own),
                (:cost,:t_id,:bar);

                """
            ), [{"t_id": t_id.scalar_one(), "rml" : num_ml_per_type[0],"gml": num_ml_per_type[1],"bml": num_ml_per_type[2], "dml": num_ml_per_type[3], "cost": cost, "own": utils.OWNER_ID, "bar" : utils.BARRELER_ID}]
            )
             
        
    print(f"rml: {num_ml_per_type[0]} gml: {num_ml_per_type[1]} bml: {num_ml_per_type[2]} dml: {num_ml_per_type[3]} gold_cost: {cost}")
    return "OK"


#input: priority list: uses past experience to determine, amt_needed --> [r_need,g_need,...]
#output: a list of amt_needed in the order of what we should buy first --> [(2,b_need),(0,r_need),...]
def det_type_priority(priority,amt_needed,tick):

    #default [3,2,1,0]
    #since red= 0 index, it has the greatest priority
    #dark = 3 index, it has the least priority
    default = [3,2,1,0]
    hour = tick%24
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



#determines the priority using past experience selling at this tick... if no past experience priority based off other priority 
#input: current amount of ml in inventory --> [r_ml,g_ml,b_ml,d_ml] (will be negative values since this represents amt we want to buy)
#output: the amount of ml we need for each type (will be used as a priority list) --> [r,g,b,d]
def det_potion_priority(amt_list,res):

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

    ### BARREL LOGGING ###

    with db.engine.begin() as connection:
        id = connection.execute(sqlalchemy.text(
            """
            INSERT INTO barrel_transactions DEFAULT VALUES
            RETURNING id
            """
        ))

        bt_id = id.scalar_one()
        for barrel in wholesale_catalog:
            connection.execute(sqlalchemy.text(
                """
                INSERT INTO log_barrels
                (barrel_sku,quantity,price,ml_per_barrel,bt_id)
                VALUES
                (:s,:q,:p,:m,:bt_id)
                """ 
            ),[{"s":barrel.sku,"q":barrel.quantity,"p":barrel.price,"m":barrel.ml_per_barrel,"bt_id": bt_id}])


    ### DATA RETRIVAL ###


    tick = utils.getCurTick()
    tot_barrel_list = []

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(gold_ledger.quantity) AS gold
            FROM gold_ledger 
            WHERE account_id = :own
            
            """
        ),[{"own": utils.OWNER_ID}])

        #from tab
        tot_budget = tab.scalar_one()
        if tot_budget == None:
            tot_budget = 0 

        tab1 =  connection.execute(sqlalchemy.text(
            """
            SELECT 
            COALESCE(SUM(ml_ledger.red_quantity),0) AS rml,
            COALESCE(SUM(ml_ledger.green_quantity),0) AS gml,
            COALESCE(SUM(ml_ledger.blue_quantity),0) AS bml,
            COALESCE(SUM(ml_ledger.dark_quantity),0) AS dml
            FROM ml_ledger 
            WHERE account_id = :own
            """
        ),[{"own": utils.OWNER_ID}])

        #from tab1
        result = tab1.first()
        if result == []:
            cur_amt = [0,0,0,0]
        else:
            cur_amt = [-result.rml,-result.gml,-result.bml,-result.dml] #will store how much ml we need to fully restock our store
   
        tab2 = connection.execute(sqlalchemy.text(
        """
        WITH PotionSum AS (
            SELECT pi.id,SUM(pl.quantity) AS total_quantity
            FROM potion_inventory AS pi
            JOIN potion_ledger AS pl ON pi.id = pl.potion_id
            WHERE account_id = :own
            GROUP BY pi.id
        )

        SELECT pi.potion_type, (pi.max_potion - COALESCE(ps.total_quantity,0)) as quant_needed
        FROM potion_inventory AS pi 
        LEFT JOIN PotionSum AS ps ON pi.id = ps.id
        WHERE COALESCE(ps.total_quantity,0) < pi.max_potion 

        """
        ),[{"own": utils.OWNER_ID}])

              
        amt_needed_list = cur_amt.copy()
        #from tab2
        #updates the amt needed per type
        for row in tab2:
            for i in range(len(row.potion_type)):
                amt_needed_list[i] += row.potion_type[i]*row.quant_needed
    
        tab3 = connection.execute(sqlalchemy.text(
        """
        WITH PotionSum AS (
            SELECT pi.id,SUM(pl.quantity) AS total_quantity
            FROM potion_inventory AS pi
            JOIN potion_ledger AS pl ON pi.id = pl.potion_id
            WHERE account_id = :own
            GROUP BY pi.id
        )

        SELECT pi.potion_type, (ci.quantity - COALESCE(ps.total_quantity,0)) as quant_needed
        FROM potion_inventory AS pi 
        LEFT JOIN PotionSum AS ps ON pi.id = ps.id
        JOIN cart_items AS ci ON ci.potion_inventory_id = pi.id
        WHERE COALESCE(ps.total_quantity,0) < ci.quantity 
        AND 
        pi.id IN  (
            SELECT cart_items.potion_inventory_id
            FROM carts
            JOIN cart_items ON carts.id = cart_items.cart_id
            WHERE carts.tick = :cur_tick + 2 or carts.tick = :cur_tick + 3
        )
        
        """
        ),[{"cur_tick" : tick, "own": utils.OWNER_ID}]
        )

        #from tab3
        prev_info = tab3.all() #returns empty list on no entries in tab3

    ## DATA ANALYSIS ##

    print(cur_amt)
    priority = det_potion_priority(cur_amt,prev_info) #a priority list
    priority_list = det_type_priority(priority,amt_needed_list,tick) #sorted amt_needed list 
    print(f"amt_needed: {amt_needed_list} priority: {priority} priority_list = {priority_list}") 

    if tot_budget > 1000:
        budget = math.floor(tot_budget * 0.9) #ensures we have 100 gold at all times
    else:
        budget = tot_budget
    #goes through priority list in order
    for i,val in enumerate(priority_list):
        type = [0,0,0,0]
        type_index = val[0]
        type[type_index] = 1 #this represents the array repr of type -->  [1,0,0,0] represents red
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

    