
/*
Creating the carts table
Fields:
customer_name
payment_string
created at
tick
*/

CREATE OR REPLACE FUNCTION add_tick(t timestamp with time zone)
RETURNS integer
AS
$$
BEGIN
RETURN FLOOR((EXTRACT(HOUR FROM t)+2)/2) + (EXTRACT(ISODOW FROM now())-1)*12;
END;
$$
LANGUAGE plpgsql; 

CREATE TABLE
    carts (
        id int generated always as identity not null PRIMARY KEY,
        customer_name not null text,
        payment_string text,
        created_at timestamp with time zone not null default now(),
        tick integer not null default add_tick(now())     
    );

/*
Creating the cart_items table
Fields:
potion_inventory_id
quantity
cart_id

*/

CREATE TABLE
    cart_items (
        id int generated always as identity not null PRIMARY KEY,
        potion_inventory_id int REFERENCES potion_inventory (id),
        quantity int not null default 0, 
        cart_id int REFERENCES carts (id)
   )

/*ticks table (use as a reference for ticks id)
Fields:(prepopulated with 7*12 rows)
dow: int 1-7
time_initial(hour) : int 0-24 
time_end(hour): int 0-24 
ex: if run at 13(1pm) then initial: 12, end: 14
we'll use a csv file to streamline the process... located at tick_table.csv
add id field seperately in supabase...
*/
