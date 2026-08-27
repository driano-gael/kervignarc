"""Registre des prises de contrôle d'écran — en mémoire, **sans persistance**.

⚠️ **C'est un choix, pas une facilité** : une prise est un geste du jour J (« podium 10 min ») ; un
redémarrage doit **libérer** les écrans, jamais les laisser figés sur une consigne que plus personne
ne se rappelle avoir posée. Le réglage durable — le déroulé — est en base, lui.
"""

from __future__ import annotations

import threading

from domain.ecran import PriseDeControle
from domain.poste import PosteId


class RegistreConsignesMemoire:
    """Prises de contrôle en mémoire : `poste_id` → consigne posée + instant de pose."""

    def __init__(self) -> None:
        self._prises: dict[PosteId, PriseDeControle] = {}
        self._verrou = threading.Lock()

    def poser(self, poste_id: PosteId, prise: PriseDeControle) -> None:
        """Pose (ou remplace) la prise de contrôle d'un écran.

        Remplacer plutôt qu'empiler : « impose le podium » après « impose le plan » est une
        correction de l'organisateur, pas une file d'attente — la dernière volonté gagne.
        """
        with self._verrou:
            self._prises[poste_id] = prise

    def prise_de(self, poste_id: PosteId) -> PriseDeControle | None:
        """Prise en vigueur pour cet écran, ou `None`. Ne juge pas l'expiration (cf. port)."""
        with self._verrou:
            return self._prises.get(poste_id)

    def retirer(self, poste_id: PosteId) -> None:
        """Rend la main sur un écran ; sans effet s'il n'était pas sous consigne."""
        with self._verrou:
            self._prises.pop(poste_id, None)

    def retirer_si(self, poste_id: PosteId, prise: PriseDeControle) -> None:
        """Retire la prise **seulement si c'est toujours cet objet-là** (cf. port).

        Comparaison d'**identité** (`is`) et non d'égalité : deux prises successives peuvent être
        structurellement identiques (même vue, même durée) tout en étant deux gestes distincts, et
        seule la seconde doit survivre. La lecture et le retrait tiennent dans **un seul** verrou —
        c'est ce qui ferme la fenêtre, pas la condition à elle seule.
        """
        with self._verrou:
            if self._prises.get(poste_id) is prise:
                del self._prises[poste_id]

    def toutes(self) -> dict[PosteId, PriseDeControle]:
        """Copie des prises en vigueur, par écran (copie : l'appelant itère hors du verrou)."""
        with self._verrou:
            return dict(self._prises)
