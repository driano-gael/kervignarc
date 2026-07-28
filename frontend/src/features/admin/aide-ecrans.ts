// Textes d'aide contextuelle des écrans d'administration (E14US002).
//
// Un dictionnaire **unique** `id de destination → texte`, consommé par la coquille (`CoquilleAdmin`)
// pour rendre l'aide de la destination active via `<AideEcran>`. Centraliser ici plutôt que dans
// chacune des 22 features donne **un seul point de vérité** : ajouter/corriger une aide se fait à un
// seul endroit, et un écran ne peut pas silencieusement se retrouver sans aide (clé absente = pas de
// bouton, visible d'un coup d'œil ici).
//
// Les clés sont les `id` des destinations déclarées dans `CoquilleAdmin` (`tournoi`, `accueil`, …).
// Elles doivent rester synchronisées : une destination ajoutée là-bas gagne son aide ici.
//
// Registre de langage : **organisateur, non technique** (règle 3 — le vocabulaire technique reste au
// code). Chaque entrée dit **ce qui se saisit** sur l'écran **et à quoi ça sert en aval** — c'est le
// « pourquoi » réclamé à la démo du 27/07/2026, pas une simple étiquette.
//
// ⚠️ **Premier jet à relire avec l'organisateur.** La story E14US002 prévoit que le contenu se rédige
// en langage métier avec lui ; ces formulations sont une base de départ raisonnable, pas une version
// arrêtée. Corriger le texte ne touche que ce fichier.

// Union littérale des `id` de destination admin. La typer — plutôt que `string` — fait **prouver au
// compilateur** l'invariant du CA « chaque écran porte une aide » : `Record<DestinationAdminId, …>`
// oblige le dictionnaire à couvrir **exactement** ces clés (une manquante ou en trop = erreur `tsc`),
// et `CoquilleAdmin` annote le champ `id` de ses destinations avec ce même type — ajouter une
// destination sans son aide ne compile plus. La synchro clés ↔ écrans n'est donc plus manuelle.
export type DestinationAdminId =
  | 'tournoi'
  | 'accueil'
  | 'categories'
  | 'blasons'
  | 'gabarits'
  | 'plan'
  | 'bareme'
  | 'phases'
  | 'departs'
  | 'clubs'
  | 'scoreurs'
  | 'inscriptions'
  | 'doublons'
  | 'placement'
  | 'duels'
  | 'paiements'
  | 'postes'
  | 'supervision'
  | 'completude'
  | 'classement'
  | 'exports'
  | 'archive'
  | 'jeu-essai'
  | 'simulation'

export const AIDE_ECRANS: Record<DestinationAdminId, string> = {
  tournoi:
    'Créez ou choisissez le tournoi sur lequel vous travaillez. Tout ce que vous réglez ensuite — ' +
    'catégories, départs, inscriptions… — appartient au tournoi sélectionné ici.',
  accueil:
    'La photo d’ensemble du tournoi : où il en est, ce qu’il reste à préparer, et les chiffres-clés ' +
    '(inscrits, réglés, postes connectés). Partez d’ici pour savoir quoi faire ensuite.',
  categories:
    'Définissez les catégories qui tirent dans ce tournoi (âge et type d’arc, par exemple « Sénior ' +
    'arc classique »). Chaque archer sera rattaché à une catégorie, qui détermine sa cible et son ' +
    'classement.',
  blasons:
    'Réglez les blasons (les cibles en papier) utilisés et reliez-les aux catégories. Le blason fixe ' +
    'la taille de cible et les valeurs de points possibles à la saisie des scores.',
  gabarits:
    'Préparez des modèles de plan de salle réutilisables (nombre de cibles, disposition). Un gabarit ' +
    'sert de point de départ au plan de salle d’un tournoi ; il n’appartient à aucun tournoi précis.',
  plan:
    'Décrivez la salle de ce tournoi : combien de cibles et comment elles sont disposées. Le plan ' +
    'conditionne le placement des archers et le nombre de postes de saisie le jour J.',
  bareme:
    'Fixez le barème de qualification (nombre de volées et de flèches) et le grain de validation (à ' +
    'quel moment un score est verrouillé). C’est ce qui cadre la saisie et le calcul du classement.',
  phases:
    'Définissez l’enchaînement des phases après la qualification (élimination directe, placement…). ' +
    'La séquence décrit le format du tournoi et pilote la génération des duels.',
  departs:
    'Créez les départs (créneaux horaires) et leur tarif. Un archer s’inscrit sur un départ ; celui-ci ' +
    'sert au placement, au planning du jour J et au calcul du montant dû.',
  clubs:
    'Tenez à jour la liste des clubs. Elle sert à rattacher chaque archer à son club (référentiel ' +
    'commun à tous les tournois) et alimente le placement (mixité des clubs sur une cible).',
  scoreurs:
    'Déclarez les personnes qui saisiront les scores et générez leur code d’accès. Un scoreur ouvre ' +
    'l’espace de saisie avec ce code, sans mot de passe administrateur.',
  inscriptions:
    'Créez les archers et inscrivez-les sur un ou plusieurs départs. L’inscription alimente les ' +
    'listes, le placement, le montant dû et, le jour J, la saisie des scores.',
  doublons:
    'Repérez les archers qui semblent en double (même nom, même club) et fusionnez leurs fiches. ' +
    'Nettoyer la liste évite les erreurs de placement et de comptage.',
  placement:
    'Répartissez les archers inscrits sur les cibles et les postes. Le plan peut être généré ' +
    'automatiquement puis ajusté au doigt (glisser-déposer) ; il détermine où chacun tire.',
  duels:
    'Ajustez le placement des duellistes d’une phase à élimination directe pour mettre les adversaires ' +
    'côte à côte. Le plan est proposé automatiquement et modifiable au glisser-déposer.',
  paiements:
    'Suivez qui a réglé son inscription et combien. Le montant dû se calcule à partir des départs de ' +
    'chaque archer ; vous pointez ici les paiements reçus.',
  postes:
    'Affichez, cible par cible, le QR de rattachement à imprimer ou à scanner. Une tablette scanne le ' +
    'QR de sa cible pour ouvrir la saisie sans avoir à s’identifier.',
  supervision:
    'Suivez en direct l’état des postes de saisie le jour J : qui est connecté, où en est la saisie. ' +
    'Sert à repérer un poste en panne ou en retard sans quitter votre place.',
  completude:
    'Vérifiez ce qui manque avant de terminer le tournoi (inscriptions, placement, scores…). Le ' +
    'contrôle liste les points bloquants et débloque la clôture quand tout est prêt.',
  classement:
    'Consultez le classement, mis à jour en direct au fil de la saisie. C’est une vue de lecture : ' +
    'rien ne s’y saisit, elle reflète les scores validés.',
  exports:
    'Générez les documents imprimables du jour J : listes de placement, par club, feuilles de ' +
    'paiement. À imprimer pour l’accueil et les bénévoles.',
  archive:
    'Constituez le paquet de fin de tournoi (sauvegarde de la base, fichiers CSV et PDF) à conserver. ' +
    'Choisissez ce que vous voulez inclure avant de générer l’archive.',
  'jeu-essai':
    'Outil de démonstration et de test : peuplez un tournoi de données factices, ou instanciez un ' +
    'scénario prêt à l’emploi (petit, gros, multi-format). Ce sont des données réelles — à réserver ' +
    'aux tournois de test.',
  simulation:
    'Rejouez le tournoi courant en accéléré, sans rien enregistrer : un robot génère des scores et ' +
    'fait avancer qualifications puis duels. Mettez en pause pour saisir vous-même à la place d’un ' +
    'rôle (cible, scoreur), puis rendez la main au robot. Idéal pour démontrer le déroulé ou vérifier ' +
    'que tout s’enchaîne — aucune donnée réelle n’est modifiée.',
}
