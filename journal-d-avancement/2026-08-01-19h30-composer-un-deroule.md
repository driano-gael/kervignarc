# 1er août 2026, 19h30 — Composer un déroulé, le voir, et le faire tourner

**US livrée : E01US024.**

Jusqu'à hier, l'organisateur pouvait *nommer* un déroulé type et le ranger dans la bibliothèque du
club, mais l'écran ne savait en fabriquer qu'un seul genre : une qualification. Pour composer autre
chose, il fallait créer un tournoi, y régler les phases, puis remonter le résultat en modèle — un
détour qui obligeait à ouvrir une édition pour obtenir un patron.

Un nouvel écran apparaît dans l'Atelier : **Composer un déroulé**. Il apporte quatre choses.

**On compose vraiment.** Toutes les phases du catalogue, pas seulement la qualification : ce qu'on
demande aux archers (barème), combien ils sont, et surtout **d'où ils viennent** — les 32 premiers du
classement, les gagnants du tour 2, ou tout le reste. C'est la première fois que ces trois façons de
peupler une phase sont accessibles depuis un écran.

**On enregistre à tout moment, même à moitié fait.** C'était la demande explicite : un déroulé se
construit par étapes, et refuser d'enregistrer tant qu'il n'est pas complet interdisait de le
construire. Un brouillon incohérent est donc sauvegardé sans protester — mais il ne peut pas servir
un vrai tournoi tant qu'il ne tient pas debout, et l'écran dit **précisément** ce qui manque.

**On le voit.** Un schéma se dessine : une case par phase, une flèche par groupe d'archers qui passe
de l'une à l'autre, avec les effectifs. Chaque case répond aux quatre questions — qui est là (combien,
et quelle tranche de rangs), ce qu'on leur demande, où ils iront après, combien de tours. Et pour un
tableau à duels, les **braquets** : *« tour 1 · 16 duels → perdants rangs 17 à 32 »*, tour après tour,
jusqu'à la finale. Ce qui ne va pas se voit **sur le dessin** — la case fautive est cerclée — plutôt
que dans un message abstrait.

Changer le nombre d'archers en haut de l'écran **redessine tout**, sans toucher au format. Un déroulé
prévu pour 120 personnes se regarde à 82, puis à 20. À 20, l'application signale que le tableau des 32
ne trouvera pas son compte — mais **sans bloquer** : le déroulé n'est pas faux, il ne tient simplement
pas à ce nombre-là. Cette distinction entre « faux » et « ne tient pas ici » est la décision de
conception de cette US.

**On le fait tourner.** Un bouton joue le déroulé sur des archers inventés et rend ce qu'il produit :
le nombre total de duels, les tours par phase, et le classement 1→N effectivement fabriqué. Rien
n'est enregistré nulle part.

Cette simulation a immédiatement servi. Elle a montré qu'un tableau à N duellistes ne coûte pas
N−1 duels, comme on le calcule de tête, mais **N** : la petite finale pour la 3ᵉ place s'ajoute.
L'organisateur qui dimensionnait ses scoreurs sur le compte théorique se serait trompé d'un duel par
tableau — exactement le genre de chose qu'aucune relecture ne donne.

---

**Une limite, affichée plutôt que tue.** Le schéma sait dire que seuls les 32 premiers doivent monter
au tableau ; le moteur qui joue réellement les duels ne sait pas encore lire cette consigne et fait
monter tout le monde. Deux affichages le disent désormais, et pas seulement après une simulation :
une **réserve permanente** sous le verdict dès qu'une phase prélève, et le détail des trois chiffres
(archers, tours, duels) dans le tableau de simulation quand ils divergent. Même traitement pour les
poules, le système suisse et la colline, qui se **composent** aujourd'hui mais que le moteur ne sait
pas encore **dérouler** : l'écran le dit, au lieu d'afficher un tiret qui ressemblerait à un
résultat. C'est un chantier identifié du moteur, à traiter dans une prochaine étape ; en attendant,
le schéma fait foi pour la composition et le chiffre de la simulation donne la charge maximale.
