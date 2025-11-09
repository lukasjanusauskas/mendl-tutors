# MENDL-tutors
---

## ER diagrama

### Mongo

![](nosql_mendl.png)

Diagramoje baltai pažymėtos tos esybės, kurias turime kaip fizines kolekcijas duomenų bazėje.
Geltonai žymime sujungčias leneteles (angl. *join table*), kurios nurodo, kokius duomenis išrenkame į fizines kolekcijas, modeliuodami daug su daug (angl. *many-to-many*) sąryšius.
Mėlynai žymime tai, ką mes fizinėse kolekcijose laikome objektais (viduje kolekcijos object tipas), kas nėra atskira esybė. Pavyzdžiui *subjects* diagramoje yra išskirta atskirai, kadangi modeliuojame kaip objektą, tačiau dalykams atskiros fizinės kolekcijos nedarom, tai ir žymim kita spalva.

### Cassandra

![](nosql_cass.pdf)

Diagramoje mėlynai pažymėtos lentelės laikomos Cassandra, o žaliai - Mongo. Ryšius su `sutdent` žymim oranžine spalva, o ryšius su `tutor` - mėlynai.

## Projekto sturktūra
---

- `model/`: skriptai sukurti mongo duombazes
- `api/`: programos funkcijos (ir API)
- `app/`: Flask app'as

## Paleidimas
---

### Paleidimas su docker

```
docker build -t mendl-app:1.0 .
docker run -p 5000:5000 mendl-app:1.0
```

### Paleidimas Windows

- Be virtual environment
```
python -m app.app
```

- Su virtual environment

```
python -m venv venv

.\venv\Scripts\Activate.ps1
pip install -r requirements.txt # Jei dar neparsiųstos bibliotekos

python -m app.app
```

### Paleidimas Linux

```
# Priklauso nuo distro, gali buti python ne python3
python3 -m venv venv

source venv/bin/activate
pip3 install -r requirements.txt

python3 -m app.app
```
