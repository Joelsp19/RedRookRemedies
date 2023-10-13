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

for r in range(len(101)):
    for g in range(len(101)):
        for b in range(len(101)):
            for d in rante(len(101)):
                /*
                Insert a row of this potion type
                */ 
