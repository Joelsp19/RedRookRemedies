from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src.api import catalog
import ctypes

cart_dict = {}
cart_id = 0

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class NewCart(BaseModel):
    customer: str

@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    global cart_id
    cart_id+=1
    
    cart_dict[cart_id] = {"customer" : new_cart}

    return {"cart_id": cart_id}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """
    cart = cart_dict[cart_id]
    return cart


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """ 
    cart_dict[cart_id][item_sku] = cart_item

    return {"success": "ok"}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print(cart_checkout)
    #hard coded for now... later need to check catalog for prices
    #things to work on...
    # need to empty cart
    # what happens if we can't find a correct id...? will this even happen since we have to create a cart...

    earnings = 0
    potion_count = 0
    potion_list = []

    #to select the current amt of gold
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT gold FROM global_inventory WHERE id = 1"
        ))
        result = tab.first()
        cur_gold = result.gold

    #goes through every item in the cart and updates the potion inventory
    #increments earnings based on price * bought and potion count
    #checks against inventory to see if users checkout is possible
    cart = cart_dict[cart_id]
    for p_sku in cart:
        if p_sku != "customer": #note that we can't have a potion sku of customer...
            with db.engine.begin() as connection:
                p_tab = connection.execute(sqlalchemy.text(
                "SELECT id, quantity, price FROM potion_inventory WHERE sku = '%s'" % (p_sku)
            ))
            p_res = p_tab.first()
            #if we can't find it in our catalog (oops big error), should def throw error
            if p_res == None:
                return {"total_potions_bought": 0, "total_gold_paid": 0}
            p_id = p_res.id
            p_quant = p_res.quantity
            p_price = p_res.price
            p_bought = cart[p_sku].quantity

            #if users try to check out more than what is in the inventory, should throw error
            if(p_quant<p_bought):
                return {"total_potions_bought": 0, "total_gold_paid": 0}

            new_quant = p_quant - p_bought
            earnings += p_price * p_bought
            potion_count += p_bought

            #we only want to update all the potions after we check to make sure cart is accurate
            #for now we store the values we need in this array
            potion_list.append([new_quant,p_id])

    for potion in potion_list:
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                "UPDATE potion_inventory SET quantity = '%s' WHERE id = '%s'" % (potion[0],potion[1])
            ))       
    
    new_gold = cur_gold + earnings
    with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                "UPDATE global_inventory SET gold = '%s' WHERE id = 1" % (new_gold)
            ))

    print(potion_count)
    print(earnings)
    return {"total_potions_bought": potion_count, "total_gold_paid": earnings}
