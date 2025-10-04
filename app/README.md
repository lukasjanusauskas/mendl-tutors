# Puslapis

MENDL UI puslapis.

## Struktūra

```
app/
├── app.py             # Puslapio paleidimas
├── templates/         # HTML failai
│   ├── base.html
│   ├── index.html
│   └── students.html
│   ...
└── static/            # CSS ir JavaScript
    ├── css/
    └── js/
```

## Puslapio paleidimas

1. Paleidimas:
   ```
   python app.py
   ```

2. Naršyklėje nueikite į `http://localhost:5000`

## Naujo puslapio pridėjimas

1. HTML failus kurkite aplanke `templates/`
2. Pridėkite naują puslapį į `app.py`

## CSS ir JS pridėjimas

- CSS failus kurkite aplanke `static/css/`
- JavaSript failus kurkite aplanke `static/js/`