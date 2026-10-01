# 1er octobre 2026 — Chaque phase de duels choisit son barème

**US** : `E01US011` · **Jalon** : J4 (2ᵉ US sur 7)

## Ce qui change

Jusqu'ici, tous les duels se jouaient au barème **FFTA** : premier à **6** points de set, les arcs à
poulies au cumul. Le format du club (premier à **4** points) était connu de l'application, mais
aucun écran ne permettait de le choisir.

Désormais, l'organisateur règle le barème **phase par phase**, sur l'écran des phases d'un tournoi
comme dans l'atelier des formats. Un tableau principal peut se jouer au barème FFTA et une repasse au
format club, dans le même tournoi. Deux boutons pré-remplissent le réglage, et chaque arme peut
avoir ses **propres règles** : les poulies au cumul, par exemple, sont posées toutes seules quand
le tournoi a une catégorie de cette arme.

Le barème de qualification gagne aussi un bouton **format club** (5 volées de 3 flèches).

## Pour l'organisateur

- Un réglage oublié ne change rien : une phase non réglée joue comme avant.
- Le barème **se fige dès qu'un duel de la phase a été tiré**. Le changer ensuite ferait relire
  les duels déjà validés sous d'autres règles, et un vainqueur pourrait basculer sans que personne
  ne le voie. L'application refuse donc, avec un message qui dit pourquoi.
- Un format enregistré emporte son barème : l'année suivante, il se réapplique tel quel.
- Pour la même raison, l'**arme d'une catégorie** ne se renomme plus une fois qu'un duel d'une phase
  réglée a été tiré.
- Au format club, deux archers à **4-4** dans la même manche ne se départagent plus au classement :
  ils tirent un **barrage**, comme à 5-5 au barème fédéral.
- Pas encore possible : les ½ finales et finales du club **à 6 points** dans un tableau à 4. Une US
  dédiée est inscrite.

Scénario de vérification : [`docs/fonctionnel/E01US011.md`](../docs/fonctionnel/E01US011.md).
