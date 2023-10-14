from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db



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

    with db.engine.begin() as connection:
        uid = connection.execute(sqlalchemy.text(
            """INSERT INTO carts
            (customer_name)
            VALUES
            (:customer)
            RETURNING id"""
            ),
        [{"customer" : new_cart.customer}]
        )
    return {"cart_id": uid}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """SELECT *
            FROM carts
            JOIN cart_items ON carts_items.cart_id = carts.id
            WHERE id = :id"""
            ),
        [{"id": cart_id}]
        )

    return tab


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """ 

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO cart_items 
            (potion_inventory_id, quantity, cart_id)
            SELECT potion_inventory.id, :potion_id, :quant
            FROM potion_inventory
            WHERE sku = :sku
            """
            ),
        [{"potion_id": id, "cart_id": cart_id, "sku": item_sku, "quant": cart_item.quantity}]
        )

    return {"success": "ok"}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    print(cart_checkout)


    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            UPDATE potion_inventory
            SET quantity = potion_inventory.quantity - cart_items.quantity
            FROM cart_items
            WHERE potion_inventory.id = cart_items.potion_id and cart_items.cart_id = :cart_id
            """
            ),
        [{"cart_id" : cart_id}]
        )

    #selects the total number of potions and calculates earnings
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(quantity) AS potions_bought, SUM(quantity * price) AS earnings
            FROM cart_items
            WHERE cart_id == :card_id
            """
        ), 
        [{"cart_id" : cart_id}]
        )

        potions_bought = tab.scalar_one.potions_bought
        earnings = tab.scalar_one.earnings

    return {"total_potions_bought": potions_bought, "total_gold_paid": earnings}


