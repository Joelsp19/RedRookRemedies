
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
we'll use a csv file to streamline the process... located at tick_table.csv
add id field seperately in supabase...
*/
