## Payment table

```sql
CREATE TABLE payments.by_user_time ( 
    id uuid,
    user_id text,
    for_tutor boolean,
    payment decimal,
    time_payment timestamp,
    pay_timestamp timestamp,
    is_complete boolean,
    PRIMARY KEY ( (id, user_id), pay_timestamp)
) WITH CLUSTERING ORDER BY (pay_timestamp DESC);
```

```sql
CREATE TABLE payments.by_user (
    id uuid,
    user_id text,
    for_tutor boolean,
    payment decimal,
    time_payment timestamp,
    pay_timestamp timestamp,
    is_complete boolean,
PRIMARY KEY (id, user_id) 
);
```

```sql
CREATE TABLE payments.by_id (
    id uuid,
    user_id text,
    for_tutor boolean,
    payment decimal,
    time_payment timestamp,
    pay_timestamp timestamp,
    is_complete boolean,
PRIMARY KEY (id) 
);
```

```sql
CREATE TABLE payments.by_size (
    id uuid,
    user_id text,
    for_tutor boolean,
    payment decimal,
    time_payment timestamp,
    pay_timestamp timestamp,
    is_complete boolean,
PRIMARY KEY (id, payment)
) WITH CLUSTERING ORDER BY (payment DESC);
```