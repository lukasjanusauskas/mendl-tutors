# API for Mendl-tutors

## API iškvietimų pavyzdžiai:

### Su JSON

Iškviečiant, endpointus `tutor/`, `tutor/assign_student/`, `student/`.

1. Per Postman eiti į Body
2. Pasirinkti "raw"
3. Surašyti viską į json

**Pavyzdžiai:**

```
# Pridėti korepetitorę per tutor endpointą
{
    "first_name": "Barbora",
    "last_name": "Barboraitė",
    "date_of_birth": "2003-02-09",
    "subjects": [{"subject": "MAT", "max_class": 5}, {"subject": "MUZ"}],
    "password": "kasskaitystasgaidys",
    "email": "barbora.barboraite@mendltutor.lt"
}
```

```
# Sukurti mokini
{    
    "first_name": "Petras",
    "last_name": "Petraitis",
    "date_of_birth": "2013-02-09",
    "subjects": ["MAT", "MUZ"],
    "password": "0987",
    "email": "petriuks@google.lt",
    "class": 6,
    "parents_phone_numbers": [
        "+37089898888"
    ]
}
```

```
# Prideti mokini mokytojui
{
    "tutor_id": "68dfd73286998ba652258c44",
    "student_id": "68dfe430c266645c2c96b796",
    "subject": "MAT"
}
```

```
# Prideti pamoka
{
    "time": "2025-10-07 15:00",
    "tutor_id": "68e015c72541f9f89f6ca611",
    "student_ids": [
        "68dfe430c266645c2c96b796",
        "68dfe5e166fb223bfcdd8807"
    ],
    "subject": "MAT"
}
```

### Su parametrais

- Pakeisti pamokos laika
```
localhost:5000/lesson/change_time/68e022ffdb5a47817cf49790/2025-10-08 15:00
```