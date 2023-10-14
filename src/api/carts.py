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
        tab = connection.execute(sqlalchemy.text(
            """INSERT INTO carts
            (customer_name)
            VALUES
            (:customer)
            RETURNING id"""
            ),
        [{"customer" : new_cart.customer}]
        )
        uid = tab.scalar_one()
    return {"cart_id": uid}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """SELECT *, carts.id
            FROM carts
            LEFT JOIN cart_items ON carts.id = cart_items.cart_id
            WHERE carts.id = :id
            

            """
            ),
        [{"id": cart_id}]
        )

    
    print(tab.scalars().all())
    return tab.scalars().all()


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """ 

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO cart_items 
            (cart_id, quantity, potion_inventory_id)
            SELECT :cart_id, :quant, potion_inventory.id
            FROM potion_inventory
            WHERE potion_inventory.sku = :sku
            """
            ),
        [{"cart_id": cart_id, "sku": item_sku, "quant": cart_item.quantity}]
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
            WHERE cart_items.potion_inventory_id = potion_inventory.id and cart_items.cart_id = :cart_id
            """
            ),
        [{"cart_id" : cart_id}]
        )

    #selects the total number of potions and calculates earnings
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(cart_items.quantity) AS potions_bought, SUM(cart_items.quantity * price) AS earnings
            FROM cart_items
            JOIN potion_inventory ON cart_items.potion_inventory_id = potion_inventory.id
            WHERE cart_items.cart_id = :cart_id
            """
        ), 
        [{"cart_id" : cart_id}]
        )

    data = tab.first()
    potions_bought = data.potions_bought
    earnings = data.earnings

    #updates the amt of gold 
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            UPDATE global_inventory
            SET gold = gold + :earnings
            WHERE id = 1
            """
        ), 
        [{"earnings" : earnings}]
        )  

    #updates the payment string
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(
            """
            UPDATE carts
            SET payment_string = :p
            WHERE carts.id = :cart_id
            """
        ), 
        [{"cart_id" : cart_id, "p": cart_checkout.payment}]
        )   

    return {"total_potions_bought": potions_bought, "total_gold_paid": earnings}


