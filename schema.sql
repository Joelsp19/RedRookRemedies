
/*
Creating the carts table
Fields:
customer_name
payment_string

*/

CREATE TABLE
    carts (
        id int generated always as identity not null PRIMARY KEY,
        customer_name text,
        payment_string text,
        created_at timestamp with time zone null default now()
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

/*tick_time table
Fields:(prepopulated with 7*12 rows)
dow: int 1-7
time_initial(hour) : int 0-24 
time_end(hour): int 0-24 
ex: if run at 13(1pm) then initial: 12, end: 14
*/

COPY tick_time (dow, time_initial, time_final)
FROM 'C:\Users\joelp\OneDrive - Cal Poly\CalPoly\CSC 365\RedRookRemedies\tick_table.csv' DELIMITER ',' CSV HEADER;


CREATE TABLE
    tick_time (
        id int generated always as identity not null PRIMARY KEY,
        dow int not null CHECK (dow>=1 AND dow<=7),
        time_initial int not null CHECK (time_initial>=0 AND time_initial<=24), 
        time_final int not null CHECK (time_final>=0 AND time_final<=24)
   )

/*initialize 7*12 rows*/
DECLARE
    dow integer := 1;
    timei integer := 0;
    timef integer := timei + 2;
BEGIN
    WHILE dow <7 LOOP
        INSERT INTO tick_time
        (dow,time_initial,time_final)
        VALUES
        (dow,timei,timef);
        timei := (timei + 2)%24;
        timef := (timef + 2)%24;
        dow := dow +1;
    END LOOP
END
