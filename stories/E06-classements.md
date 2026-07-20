# E06 — Classements & résultats — User Stories

> EPIC : [EPIC-06](../epics/EPIC-06-classements.md) · Réfs : CDC fonctionnel M7, `moteur-placement-lucky-loser.md` §3-4.

> ⚠️ **Maille révisée le 17/07/2026** — regroupement des US au grain « capacité » (8 → 4). Les anciennes
> US découpées par sous-aspect (départage, catégorie, agrégation de rangs, profondeur) sont devenues des
> **critères d'acceptation** de l'US de capacité qui les porte. **Aucun comportement n'est perdu** (règle 9
> — chaque ancien titre = une puce CA identifiée). Les dépendances entrantes internes ont été redirigées
> vers l'US survivante. Correspondance ancien → nouveau en fin de fichier.

---

### E06US001 — Classement de qualification (cumul, départage, par catégorie)
*En tant que* public/organisateur, *je veux* le classement de qualification trié, départagé et disponible par catégorie, *afin de* connaître les positions sans ambiguïté.
- **CA — cumul (ex-001)** : archers triés par score cumulé (somme des volées **validées**, cf.
  `Serie.cumul`) ; mis à jour en live ; par tournoi.
- **CA — départage (ex-002)** : à score égal, tri par nombre de 10 puis de 9 ; départage déterministe
  et **traçable** — le nombre de 10 et de 9 est **restitué** dans chaque ligne, vérifiable à l'œil.
  Les deux critères sont séquentiels (`referentiel-ffta` §8.1) ; si l'égalité subsiste, le **défaut**
  est l'**ex æquo** (rangs partagés). Départager les places à enjeu par un **barrage** de tir (§8.2)
  reste une **option configurable** (US dédiée E06US003 ; politique `tiebreak` d'ADR-0004) : les deux
  résolutions doivent rester **ouvertes** — seul le défaut (ex æquo) est fixé ici.
- **CA — catégorie (ex-008)** : **deux rangs** coexistent (arbitrage produit du 20/07/2026) — un rang
  **scratch** (global, toutes catégories) et un rang **par catégorie** (repartant de 1 par catégorie,
  ex æquo partagés **avec sauts** — même règle que le scratch, **pas** un rang « dense » sans trou :
  deux ex æquo en 2ᵉ place sont suivis d'un 4ᵉ) ; un **filtre** d'affichage restreint à une catégorie
  sans changer les rangs. Applicable qualif et duels.
- **Notes** : politique `tiebreak` (ADR-0004) pour le départage, preset FFTA modifiable. En E06US001
  la règle FFTA est implémentée comme **clé de tri isolée et nommée** dans le domaine (couture
  d'injection future) ; la machinerie `Phase.config.tiebreak` **n'est pas** introduite ici — son
  moteur relève d'EPIC-05, qu'ADR-0004 scope lui-même là-bas (règle 12). Le classement dérive des
  **séries** de saisie (E04US002), pas de l'agrégat `Score` du walking skeleton (repointé en E06US001).
- **Absorbe** : ex-E06US002, E06US008. **Dépend de** : E04US002 · **Jalon** : J1

### E06US003 — Barrage de tir pour places décisives
*En tant que* système, *je veux* un barrage quand le comptage ne suffit pas, *afin de* trancher les places décisives.
- **CA** : déclenchement d'un barrage (shoot-off) pour les positions à enjeu ; résultat intégré au classement.
- **Notes** : dépendances redirigées au regroupement du 17/07/2026 — l'ex-`E06US002` (dont dépendait cette
  US) a rejoint `E06US001` ; l'ex-`E04US016` a rejoint `E04US013` (redirection déjà actée dans
  `E04-saisie-scores.md`).
- **Dépend de** : E06US001, E04US013 · **Jalon** : J2

### E06US004 — Podium des duels & agrégation des rangs
*En tant que* public, *je veux* voir le podium et un classement de duels cohérent, *afin de* connaître les vainqueurs et le rang de chacun.
- **CA — podium (ex-004)** : rangs 1-4 issus de la finale/petite finale (E05US005) ; affiché et exportable.
- **CA — agrégation (ex-005)** : rangs des différentes phases fusionnés en un classement cohérent par catégorie.
- **Absorbe** : ex-E06US005. **Dépend de** : E05US005 · **Jalon** : J2

### E06US006 — Classement intégral 1→N & profondeur configurable
*En tant que* public/organisateur, *je veux* un classement complet dont je choisis la profondeur, *afin de* connaître le rang de chaque archer, adapté au tournoi.
- **CA — rang unique (ex-006)** : chaque archer a un rang unique 1→N, alimenté par les matchs terminaux (E05US010).
- **CA — profondeur configurable (ex-007)** : mode 1→N (défaut) OU top N + regroupement du reliquat ; politique `depth`.
- **Notes** : cohérent avec l'oracle 120.
- **Absorbe** : ex-E06US007. **Dépend de** : E05US010 · **Jalon** : J3

---

## Correspondance ancien → nouveau (maille du 17/07/2026)

| Ancienne US | Titre d'origine | Devient |
|---|---|---|
| E06US001 | Classement de qualification (cumul) | **E06US001** — CA « cumul » |
| E06US002 | Départage qualif (nb de 10 puis 9) | **E06US001** — CA « départage » |
| E06US003 | Barrage de tir pour places décisives | **E06US003** (inchangée) |
| E06US004 | Podium issu des duels | **E06US004** — CA « podium » |
| E06US005 | Agréger les rangs de tableau | **E06US004** — CA « agrégation » |
| E06US006 | Classement intégral 1→N | **E06US006** — CA « rang unique » |
| E06US007 | Profondeur de classement configurable | **E06US006** — CA « profondeur configurable » |
| E06US008 | Classement par catégorie | **E06US001** — CA « catégorie » |
