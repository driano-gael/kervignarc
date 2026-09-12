# 12/09/2026 — L'accueil du tournoi parle par départ

Quand l'organisateur ouvre un tournoi, il atterrit sur l'**accueil**. Jusqu'à aujourd'hui, cet écran
ne savait parler que du tournoi **entier** : 120 inscrits, 113 réglés, 26 postes en ligne. Or une
journée ne se déroule pas « en un bloc » : elle se déroule en **départs** — le créneau de 9 h, celui
de 14 h, celui de 17 h 30. Pour savoir où en était l'un d'eux, il fallait changer d'écran et le
choisir dans une liste, **un seul à la fois**.

Désormais, l'accueil s'ouvre sur **un cadre par départ, tous côte à côte**. Chacun porte son horaire,
son état (*à lancer*, *en cours*, *clos*), et le **nombre d'archers inscrits sur ce créneau-là** —
comparé à son quota quand il en a un. C'est la réponse au « j'arrive et je vois » demandé au
questionnaire de maquettes.

Deux gains viennent avec :

- **Une pause se voit là où elle a lieu.** Quand une phase s'arrête toute seule, l'accueil affichait
  jusqu'ici un message général — « une phase attend votre relance » — sans dire **quel créneau**
  était à l'arrêt. Le message est maintenant sur le cadre du départ concerné, et sur lui seul.
- **Les boutons « Démarrer » et « Terminer » cessent d'agir en silence.** Ils renvoient vers les
  écrans « Prêt à démarrer ? » et « Prêt à terminer ? », qui **listent d'abord ce qui manque**. On
  avait deux portes pour le même geste : l'une expliquait, l'autre pas. C'est celle qui explique qui
  l'emporte, sur l'écran le plus consulté.

En contrepartie, deux choses quittent l'accueil : le chiffre « Inscrits » (la somme des cadres le
dit) et le message général de relance (absorbé). « Réglés » et « Postes en ligne » restent — ce sont
des informations du tournoi entier, qu'aucun créneau ne porte.

**Ce que l'accueil ne dit volontairement pas** : l'avancement sportif (« qualification, tour 2 sur
3 »). Cette information exige de reconstruire tous les tableaux d'un créneau à chaque
rafraîchissement — un coût que l'écran d'atterrissage ne peut pas payer plusieurs fois par minute.
Elle reste sur « Suivi du déroulé », où elle est déjà.

Scénario de recette : [`docs/fonctionnel/E16US021.md`](../docs/fonctionnel/E16US021.md).
