CREATE TABLE
  potion_table (
    id int generated always as identity not null PRIMARY KEY,
    sku text not null,
    name text not null, 
    potion_type bigint,
    quantity bigint,
    price bigint,
    max_potion bigint
);


/*
Creating the carts table
Fields:
customer_name
payment_string

*/

CREATE TABLE
  potion_table (
    id int generated always as identity not null PRIMARY KEY,
    sku text not null,
    name text not null, 
    potion_type bigint,
    quantity bigint,
    price bigint,
    max_potion bigint
);


/*
Creating the cart_items table
Fields:
potion_inventory_id
quantity
cart_id

*/
