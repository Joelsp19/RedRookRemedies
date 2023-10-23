from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db
from src import utils 

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)
class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


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


    #check if we have enough in inventory, if not then give the customer an error

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


