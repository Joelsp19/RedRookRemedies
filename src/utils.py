import sqlalchemy
from src import database as db


##CONSTANTS

RED = 0
GREEN = 1
BLUE = 2
DARK = 3

OWNER_ID = 1
BARRELER_ID = 2
BOTTLER_ID = 3

##functions

#input:none
#output: the current tick
def getCurTick():
    with db.engine.begin() as connection:
        time = connection.execute(sqlalchemy.text(
            """
            SELECT FLOOR((EXTRACT(HOUR FROM now())+2)/2) + (EXTRACT(ISODOW FROM now())-1)*12 AS tick
            """
        ))
    if time.closed:
        return 0
    else:
        return time.scalar()