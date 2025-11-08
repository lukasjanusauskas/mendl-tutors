## Payment table

```sql
CREATE TABLE payments.tutor_by_student_time ( 
    id uuid,
    tutor_id text,
    student_id text,
    payment decimal,
    payment_group int,
    time_payment timestamp,
    is_complete boolean,
    PRIMARY KEY ( (tutor_id), time_payment, student_id )
) WITH CLUSTERING ORDER BY (time_payment DESC, student_id ASC) ;
```

```sql
CREATE TABLE payments.student_by_tutor_time ( 
    id uuid,
    tutor_id text,
    student_id text,
    payment decimal,
    payment_group int,
    time_payment timestamp,
    is_complete boolean,
    PRIMARY KEY ( (student_id), time_payment, tutor_id )
) WITH CLUSTERING ORDER BY (time_payment DESC, tutor_id ASC) ;
```

```sql
CREATE TABLE payments.by_amount ( 
    id uuid,
    tutor_id text,
    student_id text,
    payment decimal,
    payment_group int,
    time_payment timestamp,
    is_complete boolean,
    PRIMARY KEY ( (payment_group), payment, id )
) ;
```