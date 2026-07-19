# ADR-0034 — Le poste sélectionne son départ courant (geste manuel ; automatisation différée)

- **Statut** : Accepté
- **Date** : 2026-07-19
- **Décideurs** : Organisateur / Architecte
- **Amende** : [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md) (E04US002) et, par
  extension du contrat du poste, [`stories/E04-saisie-scores.md`](../../stories/E04-saisie-scores.md)
  (E04US001, note de rattachement). N'amende pas la dette.
- **Introduit par** : E04US002 (saisie de qualification — tranche backend).
- **S'appuie sur** : [ADR-0029](0029-mode-d-identite-poste-de-cible-et-jeton-de-poste.md) (jeton de
  poste, session résolue en `Poste`), [ADR-0033](0033-source-de-saisie-affectations-cible-depart.md)
  (les archers viennent des `Affectation` `(cible, départ)`).
- **Prépare** : E12US002 (« lancer un tour ») — qui **automatisera** le geste posé ici.

## Contexte et problème

ADR-0033 établit que les archers d'un poste se reconstituent par `(cible_index, depart_id)`. Mais le
`Poste` (ADR-0029) n'est rattaché qu'à un **lieu** — `(tournoi_id, cible_index)` — et une cible sert
**plusieurs départs** dans la journée. Il faut donc apprendre au poste **quel départ** il sert, sans
pour autant construire dès maintenant la mécanique J2 « lancer un tour » (E12US002), qui synchronise
tous les postes d'un coup au démarrage d'un tour.

Le cas courant du club est **un seul départ** ayant des archers sur une cible donnée ; le
**chevauchement** (deux départs actifs) doit néanmoins rester possible (intérieur + extérieur, ou
matin/après-midi) — le modèle ne doit donc pas graver « un seul départ ».

## Décision

**1. La session de poste porte un `depart_id` courant, posé par un geste explicite.** Le poste, une
fois rattaché à sa cible (ADR-0029), se met « en mode départ X » : un appel dédié fixe le départ
courant de la session. Tant qu'aucun départ n'est fixé, le poste connaît son lieu mais **ne peut pas
saisir** (il ne sait pas qui afficher) — refus explicite, pas un affichage vide ambigu.

**2. Le geste est manuel dans cette US ; son automatisation est différée à E12US002.** « Lancer un
tour » (E12US002, `D-25`) fera **exactement le même geste** — fixer le départ courant — mais pour
**tous** les postes à la fois, au feu vert de l'admin. On implémente ici la **primitive** (un poste,
un départ) ; E12US002 en fera l'**orchestration** (tous les postes, un départ, d'un coup). Rien n'est
jeté ni dupliqué : la couture de E12US002 réutilisera ce même point d'entrée.

**3. Le modèle supporte N départs par cible.** Le départ courant est une propriété **du poste**, pas
du tournoi : deux postes de deux cibles (ou d'un même lieu physique servi en chevauchement) peuvent
pointer des départs différents. Aucune notion de « départ actif global » n'est introduite — elle
n'existera qu'avec le cycle de vie du départ (E12US008), plus tard.

**4. Garde de cohérence.** Fixer un départ courant vérifie qu'il appartient au **tournoi du poste**
(sinon erreur applicative, jamais 500). La légalité fine de la saisie (l'archer est-il affecté à
`(cible, départ)` ?) reste au service de saisie (ADR-0033 §3).

## Conséquences

- **+** E04US002 est **débloquée** sans anticiper l'orchestrateur J2 : la primitive suffit à saisir.
- **+** E12US002 hérite d'un point d'accroche propre — « lancer un tour » = fixer le départ courant de
  tous les postes concernés — au lieu d'inventer un mécanisme parallèle.
- **+** Le chevauchement de départs reste modélisable (propriété par poste), même si le cas courant
  est mono-départ.
- **−** Un geste manuel de plus le jour J (mettre le poste sur son départ) tant qu'E12US002 n'existe
  pas. Acceptable : c'est le même geste que le rattachement de la tablette, et le cas mono-départ se
  présélectionnera côté front. Signalé, non contourné.
- **−** Le départ courant est un **état de session** (en mémoire, comme la session de poste
  d'ADR-0029), non persisté : au redémarrage serveur, un poste re-fixe son départ. Cohérent avec le
  modèle de session existant ; pas de migration.
