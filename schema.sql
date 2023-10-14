CREATE TABLE
  potion_inventory_1 (
    id int generated always as identity not null PRIMARY KEY,
    sku text not null,
    name text not null default "", 
    potion_type int ARRAY[4] not null,
    quantity int not null default 0,
    price int not null default 25,
    max_potion int not null default 5
);


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