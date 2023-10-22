from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from src import utils 




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
            """SELECT carts.customer_name,potion_inventory.sku,cart_items.quantity
            FROM cart_items
            LEFT JOIN carts
            ON carts.id = cart_items.cart_id
            LEFT JOIN potion_inventory
            ON potion_inventory.id = cart_items.potion_inventory_id
            WHERE carts.id = :id

            """
            ),
        [{"id": cart_id}]
        )
        res = str(tab.all())
    return res


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
            ON CONFLICT (cart_id,potion_inventory_id) DO UPDATE
            SET quantity = EXCLUDED.quantity
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


    #selects the total number of potions and calculates earnings
    with db.engine.begin() as connection:
        tab = connection.execute(sqlalchemy.text(
            """
            SELECT SUM(cart_items.quantity) AS potions_bought, SUM(cart_items.quantity * price) AS earnings
            FROM cart_items
            JOIN potion_inventory ON cart_items.potion_inventory_id = potion_inventory.id
            WHERE cart_items.cart_id = :cart_id;


            """
        ), 
        [{"cart_id" : cart_id}]
        )

        connection.execute(sqlalchemy.text(
            """
            UPDATE carts
            SET payment_string = :p
            WHERE carts.id = :cart_id

            """
        ), 
        [{"cart_id" : cart_id, "p": cart_checkout.payment}]
        )


    data = tab.first()
    potions_bought = data.potions_bought
    earnings = data.earnings

    with db.engine.begin() as connection:
        #creates an acct if not one exists
        a_id = connection.execute(sqlalchemy.text(
            """
            WITH inserted AS (
                INSERT INTO accounts (name)
                SELECT carts.customer_name
                FROM carts
                WHERE carts.id = :cart_id
                ON CONFLICT (name) DO NOTHING
                RETURNING id
            )

            SELECT id FROM inserted
            UNION ALL
            SELECT id FROM accounts WHERE name = (SELECT customer_name FROM carts WHERE id = :cart_id);
            """
        ),[{"cart_id" : cart_id}])

        a_id = a_id.scalar_one()

        #creates a transaction
        t_id = connection.execute(sqlalchemy.text(
            """
            INSERT INTO transactions
            (description)
            SELECT b.name || ' buys :tot_potions for :earnings gold from ' || a.name 
            FROM accounts AS a
            JOIN accounts AS b ON a.id = :own AND b.id = :cus
            RETURNING transactions.id
            """

        ), [{"earnings" : earnings, "tot_potions": potions_bought, "own": utils.OWNER_ID, "cus" : a_id}]
        )

        t_id = t_id.scalar_one()

        connection.execute(sqlalchemy.text(
            """
            INSERT INTO potion_ledger
            (potion_id,quantity,transaction_id,account_id)
            SELECT ci.potion_inventory_id, ci.quantity,:t_id,:cus
            FROM cart_items as ci
            WHERE ci.cart_id = :cart_id;

            INSERT INTO potion_ledger
            (potion_id,quantity,transaction_id,account_id)
            SELECT ci.potion_inventory_id, -ci.quantity,:t_id,:own
            FROM cart_items as ci
            WHERE ci.cart_id = :cart_id;
            
            INSERT INTO gold_ledger
            (quantity,transaction_id,account_id)
            VALUES
            (:earnings,:t_id,:own),
            (-:earnings,:t_id,:cus);

            """
            ),
        [{"cart_id" : cart_id, "t_id": t_id,"cus": a_id, "own": utils.OWNER_ID,"earnings": earnings}]
        )


    return {"total_potions_bought": potions_bought, "total_gold_paid": earnings}


