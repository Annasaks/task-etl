# Task ETL

Pipeline ETL (Extract, Transform, Load) en Python.

## Structure

```
task-etl/
├── extract/
│   └── extractor.py      # Lecture des données source
├── transform/
│   └── transformer.py    # Nettoyage et transformation
├── load/
│   └── loader.py         # Écriture vers la destination
├── config.py             # Chargement des variables d'environnement
├── main.py               # Point d'entrée du pipeline
├── requirements.txt      # Dépendances Python
└── .env                  # Variables d'environnement (ne pas commiter)
```

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copie `.env` et remplis les valeurs :

```bash
cp .env .env.local
```

## Lancement

```bash
python main.py
```
