"""Point d'entrée du backend Kervignarc.

Démarre l'application **via la composition root** (`bootstrap`). Aucune logique de câblage
ici : tout est assemblé dans `bootstrap.composition.create_app()` (guide §2.2).

Lancement (dev) :
    uvicorn main:app --reload
"""

from bootstrap.composition import create_app

app = create_app()
