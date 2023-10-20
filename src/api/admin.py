from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        transaction_id = connection.execute(sqlalchemy.text(
            """
            TRUNCATE gold_ledger, potion_ledger, ml_ledger, transactions;
            INSERT INTO transactions
            (description)
            VALUES
            ('Bank gives 100 gold to Joel')
            RETURNING transactions.id
            """

        ))
        connection.execute(sqlalchemy.text(
            """
            INSERT INTO gold_ledger
            (account_id,transaction_id,quantity)
            VALUES
            (1,:t_id,100);
            """
        ),[{"t_id" : transaction_id.scalar_one()}])

    return "OK"


@router.get("/shop_info/")
def get_shop_info():
    """ """

    # TODO: Change me!
    return {
        "shop_name": "Red Rook Remedies",
        "shop_owner": "Joel Puthankalam",
    }

