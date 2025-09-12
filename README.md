# MENDL-tutors
---

## Paleidimas Windows
---

- Su virtual environment

Sukurti virtual environment, kad nebūtų konfliktų:
```
python -m venv venv
```

Aktyvuoti virtual enviroment ir atsiųsti
```
.\venv\Scripts\Activate.ps1
pip install -r requirements     # Vieną kartą

python main.py
```

Jei iškils sunkumų pabandykit: `Set-ExecutionPolicy Unrestricted -Scope Process` arba `Set-ExecutionPolicy Unrestricted -Force`

- Be virtual environment

```
pip install -r requirements.txt
python main.py
```

## Paleidimas Linux
---

Jei bandysit per WSL2 ar MIF'o servus/VM'us paleisti
```
python3 -m venv venv            # Gali tekti atsiųsti python3-venv. 
                                # Jei nepavyks, pabandykit paprastą python vietoj python3.
```

```
source venv/bin/activate        # Kaskart
pip install -r requirements.txt # Atsisiuntimas, tai tik kartą
python3 main.py                 # Jei nepavyks, tai tsg python
```
