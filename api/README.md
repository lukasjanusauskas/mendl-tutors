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

### Su parametrais