# MENDL-tutors
---

## Projekto sturktūra
---

- `model/`: skriptai sukurti mongo duombazes
- `api/`: programos API
- `app/`: Flask app'as

## Paleidimas
---

### Paleidimas su docker

```
docker build -t mendl-app:1.0 .
docker run mendl-app:1.0
```

### Paleidimas Windows

- Be virtual environment
```
python -m app.app
```

- Su virtual environment

Aktyvuoti virtual enviroment ir atsiųsti
```
python -m venv venv

.\venv\Scripts\Activate.ps1
pip install -r requirements.txt # Jei dar neparsiųsta

python -m app.app
```

### Paleidimas Linux
Jei bandysit per WSL2

```
# Priklauso nuo, distro, gali buti python3
python3 -m venv venv

source venv/bin/activate
pip3 install -r requirements.txt

python3 -m app.app
```
