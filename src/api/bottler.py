from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
import math
from src import database as db
from src import utils


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
    potion_count = 0
    num_ml_by_type = [0,0,0,0]
    for i in range(4):
        num_ml_by_type[i] = sum(potion.potion_type[i]*potion.quantity for potion in potions_delivered)
    tot_ml = sum(num_ml_by_type)
    potion_count = math.floor(tot_ml/100)


    with db.engine.begin() as connection:
        t_id = connection.execute(sqlalchemy.text(
            """
            INSERT INTO transactions
            (description)
            SELECT b.name || ' bottles :tot_ml ml into :tot_potions potions for ' || a.name 
            FROM accounts AS a
            JOIN accounts AS b ON a.id = :own AND b.id = :bot
            RETURNING transactions.id
            """

        ), [{"tot_ml" : tot_ml, "tot_potions": potion_count, "own": utils.OWNER_ID, "bot" : utils.BOTTLER_ID}]
        )

        t_id = t_id.scalar_one()

        connection.execute(sqlalchemy.text(
            """
            INSERT INTO ml_ledger
            (red_quantity,green_quantity,blue_quantity,dark_quantity,transaction_id,account_id)
            VALUES
            (-:rml,-:gml,-:bml,-:dml,:t_id,:own),
            (:rml,:gml,:bml,:dml,:t_id,:bot);

            """
        ), [{"t_id": t_id, "rml" : num_ml_by_type[0],"gml": num_ml_by_type[1],"bml": num_ml_by_type[2], "dml": num_ml_by_type[3],  "own": utils.OWNER_ID, "bot" : utils.BOTTLER_ID}]
        )

        for potion in potions_delivered:
            connection.execute(sqlalchemy.text(
            """
            INSERT INTO potion_ledger
            (potion_id,quantity,transaction_id,account_id)
            SELECT potion_inventory.id,:delivered,:t_id,:own
            FROM potion_inventory
            WHERE potion_type = :potion_type;
            
            INSERT INTO potion_ledger
            (potion_id,quantity,transaction_id,account_id)
            SELECT potion_inventory.id,-:delivered,:t_id,:bot
            FROM potion_inventory
            WHERE potion_type = :potion_type

            """
            ),
        [{"delivered": potion.quantity, "potion_type": potion.potion_type, "t_id": t_id, "own": utils.OWNER_ID, "bot" : utils.BOTTLER_ID}]
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
        tab =  connection.execute(sqlalchemy.text(
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

        stock_tab  = connection.execute(sqlalchemy.text(
        """
        WITH PotionSum AS (
        SELECT pi.id,SUM(pl.quantity) AS total_quantity
        FROM potion_inventory AS pi
        LEFT JOIN potion_ledger AS pl ON pi.id = pl.potion_id
        WHERE pi.id = pi.id or account_id = :own
        GROUP BY pi.id
        ),
        CartSum As (
        SELECT SUM(ci.quantity)/COUNT(*) AS total_quantity, ci.potion_inventory_id
        FROM cart_items AS ci
        JOIN carts AS c on c.id = ci.cart_id
        WHERE c.tick = :tick + 1 or c.tick = :tick + 2
        GROUP BY ci.potion_inventory_id
        )

        SELECT COALESCE(ps.total_quantity, 0) as quantity, pi.potion_type,
        (pi.max_potion - COALESCE(ps.total_quantity, 0)) as potion_needed,
        CASE
            WHEN pi.potion_type IN (
            select
                pi.potion_type
            from
                potion_inventory as pi
                join CartSum as cs on cs.potion_inventory_id = pi.id
            where
                pi.potion_type is not null
            ) THEN 1
            ELSE 0
        END AS priority
        FROM potion_inventory AS pi
        JOIN PotionSum AS ps ON pi.id = ps.id
        WHERE COALESCE(ps.total_quantity, 0) < pi.max_potion
        GROUP BY quantity,potion_needed,pi.potion_type
        ORDER BY priority desc,potion_needed desc,quantity desc

        """
        ),[{"own": utils.OWNER_ID, "tick": utils.getCurTick()}])

    
    res = tab.first()
    cur_ml_list = [res.rml,res.gml, res.bml, res.dml]

    #we have a stock table... ordered based on priority, potion_needed, quantity (just looking at stocking up to max)
    stock_list = stock_tab.all()
    #stock_list.sort(key= lambda x : (x[0],-x[2])) #sorts based on quantity then potion_needed(descending order)
    print(stock_list)


    i=0
    p1_finished = False
    while len(stock_list) > 0:
        row = stock_list[i%len(stock_list)]
        #essentially skips the rows with priority 0 till we've bottled priority 1
        if not p1_finished:
            if row.priority == 0 and i!=0:
                i=0
                continue
            elif row.priority == 0 and i==0:
                p1_finished = True

        #if we can bottle it...
        if can_bottle(row.potion_type,cur_ml_list):
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
                #checks if we already have enough potions...if so remove from stock list
                if cur.get("quantity") < row.potion_needed:
                    cur["quantity"] = cur.get("quantity") + 1
                else:
                    stock_list.remove(row)
            i+=1
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

    return process()

   