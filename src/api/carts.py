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
    cart_dict[cart_id][item_sku] = cart_item.quantity

    return {"success": "ok"}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    RED_PRICE = 50
    #hard coded for now... later need to check catalog for prices
    #things to work on...
    # need to empty cart
    # what happens if we can't find a correct id...?

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            "SELECT num_red_potions,gold FROM global_inventory LIMIT 20"
        ))
        result = tab.first()
        red_quantity = result.num_red_potions
        cur_gold = result.gold

    red_bought = cart_dict[cart_id]["RED_POTION_0"]
    gold_paid = red_bought * RED_PRICE
    if red_bought > red_quantity:
        red_bought = 0
        gold_paid = 0
    else:
        new_red_potion = red_quantity - red_bought
        new_gold = cur_gold + gold_paid
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                "UPDATE global_inventory SET num_red_potions = '%s', gold = '%s' WHERE id = 1" % (new_red_potion,new_gold)
            ))
    

    return {"total_potions_bought": red_bought, "total_gold_paid": gold_paid}
