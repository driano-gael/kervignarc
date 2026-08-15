import { describe, expect, it } from 'vitest'
import type { ProchainDuel, RoutageArcher } from './api'
import {
  adversaire,
  alerte,
  apresRetour,
  destination,
  detail,
  encoreEnLice,
  panneauOuvert,
  partitionner,
  posesParCible,
  rang,
  serieClose,
  titre,
} from './presentation'

function prochain(patch: Partial<ProchainDuel> = {}): ProchainDuel {
  return {
    numero: 1,
    tour: 1,
    libelle: 'Demi-finale',
    cible: 4,
    position: 'B',
    adversaire: { archer_id: 2, nom: 'DUPONT', prenom: 'Jean' },
    sources_en_attente: [],
    manque: null,
    alerte: null,
    ...patch,
  }
}

function archer(patch: Partial<RoutageArcher> = {}): RoutageArcher {
  return {
    archer_id: 1,
    nom: 'MARTIN',
    prenom: 'Léa',
    issue: 'prochain_duel',
    prochain: prochain(),
    prochaine_manche: null,
    rang_final: null,
    rang_min: null,
    rang_max: null,
    tour_sortie: null,
    destination: null,
    motif: null,
    ...patch,
  }
}

describe('destination', () => {
  it('donne la cible et la place', () => {
    expect(destination(prochain())).toBe('Cible 4 · couloir B')
  })

  it('tolère une cible sans position', () => {
    expect(destination(prochain({ position: null }))).toBe('Cible 4')
  })

  it('rend null quand la cible n’est pas encore attribuée', () => {
    // Tour ≥ 2 : le placement intégral 1→N est E05US010. Surtout pas la cible du tour 1, qui serait
    // périmée — c'est le panneau qui enverrait le finaliste sur son ancienne butte.
    expect(destination(prochain({ cible: null, position: null }))).toBeNull()
  })
})

describe('adversaire', () => {
  it('nomme l’adversaire quand il est connu', () => {
    expect(adversaire(prochain())).toBe('DUPONT Jean')
  })

  it('nomme le duel attendu plutôt que de laisser un blanc', () => {
    const attente = prochain({ adversaire: null, sources_en_attente: [2] })
    expect(adversaire(attente)).toBe('en attente du duel n°2')
  })

  it('cumule les sources quand les deux camps sont en attente', () => {
    const attente = prochain({ adversaire: null, sources_en_attente: [2, 3] })
    expect(adversaire(attente)).toBe('en attente du duel n°2, n°3')
  })
})

describe('rang', () => {
  it('dit « vainqueur » plutôt que « 1ᵉ »', () => {
    expect(rang(archer({ rang_final: 1 }))).toBe('Vainqueur du tableau')
  })

  it('ordonne les autres places du podium', () => {
    expect(rang(archer({ rang_final: 3 }))).toBe('3ᵉ du tableau')
  })

  it('n’invente aucun rang tant qu’il n’est pas acquis', () => {
    expect(rang(archer({ rang_final: null }))).toBeNull()
  })

  // E07US008 : la fourchette *ex æquo*. Dans un tableau tronqué au podium, les quatre battus des
  // quarts sont 5ᵉ-8ᵉ et **aucun match ne les départage** — la fourchette n'est donc pas une
  // approximation du rang, c'est le rang.
  it('annonce la fourchette quand aucun match ne départage', () => {
    expect(rang(archer({ rang_final: null, rang_min: 5, rang_max: 8 }))).toBe('5ᵉ-8ᵉ du tableau')
  })

  it('referme la fourchette sur un rang unique quand elle en désigne un seul', () => {
    // Sans ce cas, un tableau en placement intégral afficherait « 7ᵉ-7ᵉ » — le même calcul, rendu
    // ridicule par sa mise en phrase.
    expect(rang(archer({ rang_final: null, rang_min: 7, rang_max: 7 }))).toBe('7ᵉ du tableau')
  })

  it('préfère le rang exact à la fourchette quand les deux existent', () => {
    expect(rang(archer({ rang_final: 2, rang_min: 2, rang_max: 2 }))).toBe('2ᵉ du tableau')
  })
})

describe('repêchage (E07US008)', () => {
  const repeche = (patch: Partial<RoutageArcher> = {}) =>
    archer({
      issue: 'repeche',
      prochain: null,
      tour_sortie: 'Quart de finale',
      destination: { phase_id: 3, ordre: 3, type: 'elimination_directe' },
      ...patch,
    })

  it('nomme la phase qui reprend l’archer', () => {
    expect(titre(repeche(), () => 'Élimination directe')).toBe('Repêché → 3. Élimination directe')
  })

  it('nomme le type depuis le catalogue même sans nommeur explicite', () => {
    // Correctif de revue : le défaut était l'**identité**, si bien qu'un appelant qui oubliait le
    // second argument affichait la valeur d'énumération brute. C'était le cas de `PanneauRoutage`
    // (canal n°1) — un oubli qu'aucun outil ne pouvait signaler.
    expect(titre(repeche())).toBe('Repêché → 3. Élimination directe')
  })

  it('retombe sur la chaîne brute pour un type que ce bundle ne connaît pas', () => {
    // Déploiement décalé : le backend peut connaître un type plus récent que l'appli ouverte depuis
    // des heures sur un téléphone. Mieux vaut « 4. tir_a_la_perche » que rien.
    const inconnu = repeche({ destination: { phase_id: 9, ordre: 4, type: 'tir_a_la_perche' } })
    expect(titre(inconnu)).toBe('Repêché → 4. tir_a_la_perche')
  })

  it('n’annonce jamais « éliminé » à un repêché', () => {
    // Le cas qui motive l'issue distincte : un repêché à qui l'on dit « éliminé » rentre chez lui
    // avant son duel. `TERMINE` aurait suffi techniquement — pas métier.
    expect(titre(repeche())).not.toContain('Éliminé')
  })

  it('le compte encore en lice, contrairement à un éliminé', () => {
    expect(encoreEnLice(repeche())).toBe(true)
    expect(encoreEnLice(archer({ issue: 'termine', prochain: null, rang_final: 5 }))).toBe(false)
  })

  it('dit d’où il vient en détail, pour rattacher la destination à ce qu’il vient de vivre', () => {
    expect(detail(repeche())).toBe('Quart de finale')
  })

  it('relaie le motif du serveur quand aucune phase ne le reprend', () => {
    // Trou de composition : le routing repêche, mais rien ne prélève ces battus. C'est le premier
    // endroit où ce trou rencontre un humain — se taire le ferait passer pour une panne réseau.
    const orphelin = repeche({
      destination: null,
      motif: 'repêché — phase de repêchage non configurée',
    })
    expect(titre(orphelin)).toBe('Repêché')
    expect(detail(orphelin)).toBe('repêché — phase de repêchage non configurée')
  })
})

// Le garde-fou du **bloquant** de la revue. Laissée dans le composant, la partition n'avait aucun
// filet : c'est la remarque de la 2ᵉ passe qui l'a fait remonter ici.
describe('partitionner (E07US008)', () => {
  const pose = archer({ archer_id: 1, prochain: prochain({ cible: 4 }) })
  const sansCible = archer({
    archer_id: 2,
    prochain: prochain({ cible: null, position: null, manque: 'cible attribuée au lancement' }),
  })
  const sorti = archer({ archer_id: 3, issue: 'termine', prochain: null, rang_final: 5 })

  it('range dans le pas de tir celui qui a une butte', () => {
    expect(partitionner([pose]).poses).toEqual([pose])
  })

  it('range EN ATTENTE, jamais parmi les sortis, celui qui est en lice sans cible', () => {
    // ⚠️ **Le bloquant, en une assertion.** Le serveur ne pose une cible qu'au tour 1 : partitionner
    // sur la cible rangeait les demi-finalistes sous « Sortis du tableau », sur l'écran projeté du
    // gymnase, pendant toute la durée du tableau sauf le premier tour.
    const { attente, sortis } = partitionner([sansCible])
    expect(attente).toEqual([sansCible])
    expect(sortis).toEqual([])
  })

  it('range parmi les sortis celui qui n’a plus de duel', () => {
    const repeche = archer({ archer_id: 4, issue: 'repeche', prochain: null })
    expect(partitionner([sorti, repeche]).sortis).toEqual([sorti, repeche])
  })

  it('ne perd et ne duplique personne', () => {
    // Une partition, au sens strict : la réunion rend l'effectif d'origine. Sans cette assertion,
    // un futur quatrième groupe pourrait faire disparaître une catégorie en silence.
    const tous = [pose, sansCible, sorti]
    const { poses, attente, sortis } = partitionner(tous)
    expect([...poses, ...attente, ...sortis]).toHaveLength(tous.length)
  })
})

describe('titre', () => {
  it('met la destination en avant — c’est ce que l’archer vient chercher', () => {
    expect(titre(archer())).toBe('Cible 4 · couloir B')
  })

  it('retombe sur le tour quand la cible n’est pas encore connue', () => {
    expect(titre(archer({ prochain: prochain({ cible: null, position: null }) }))).toBe(
      'Demi-finale',
    )
  })

  it('annonce le rang acquis', () => {
    expect(titre(archer({ issue: 'termine', prochain: null, rang_final: 2 }))).toBe('2ᵉ du tableau')
  })

  it('dit où l’archer est sorti quand son rang n’est pas encore publié', () => {
    const sorti = archer({
      issue: 'termine',
      prochain: null,
      tour_sortie: 'Quart de finale',
      motif: 'rang publié en fin de phase',
    })
    expect(titre(sorti)).toBe('Éliminé — Quart de finale')
  })

  it('avoue l’ignorance plutôt que d’afficher un vide', () => {
    const inconnu = archer({ issue: 'indisponible', prochain: null, motif: 'non retenu' })
    expect(titre(inconnu)).toBe('Destination inconnue')
  })
})

describe('detail', () => {
  it('donne le tour et l’adversaire quand tout est connu', () => {
    expect(detail(archer())).toBe('Demi-finale · DUPONT Jean')
  })

  it('remonte le motif du serveur quand la cible manque, sans répéter le tour', () => {
    const sansCible = archer({
      prochain: prochain({
        cible: null,
        position: null,
        manque: 'cible attribuée au lancement du tour',
      }),
    })
    expect(detail(sansCible)).toBe('cible attribuée au lancement du tour · DUPONT Jean')
  })

  it('relaie tel quel le motif du serveur, quel qu’il soit', () => {
    // Deux causes distinctes de « pas de cible » (tour à venir / pas de plan) : le front ne les
    // redevine pas, il affiche la phrase du serveur — c'est lui qui sait pourquoi.
    const sansPlan = archer({
      prochain: prochain({ cible: null, position: null, manque: 'cible non attribuée' }),
    })
    expect(detail(sansPlan)).toBe('cible non attribuée · DUPONT Jean')
  })

  it('remonte le motif du serveur pour une issue terminée', () => {
    const sorti = archer({ issue: 'termine', prochain: null, motif: 'rang publié en fin de phase' })
    expect(detail(sorti)).toBe('rang publié en fin de phase')
  })
})

describe('serieClose', () => {
  const validee = { verrouillee: true }
  const saisie = { verrouillee: false }

  it('est close quand toutes les volées du barème sont validées', () => {
    expect(serieClose([validee, validee], 2)).toBe(true)
  })

  it('n’est pas close tant qu’il reste des volées à tirer', () => {
    expect(serieClose([validee], 2)).toBe(false)
  })

  it('n’est pas close si une volée est saisie mais pas validée', () => {
    // C'est le scoreur qui clôt une série, pas le marqueur : un tir non validé ne route personne.
    expect(serieClose([validee, saisie], 2)).toBe(false)
  })

  it('n’est pas close tant que le barème est inconnu', () => {
    expect(serieClose([validee, validee], null)).toBe(false)
  })

  it('est close pour un archer forfait, même sans une seule volée', () => {
    // Un abandon / une DSQ (E04US015) laisse l'archer dans la grille avec une série qui ne se
    // complétera JAMAIS. Sans cette clause, la cible entière resterait « en cours » à vie et ses
    // trois autres archers ne verraient jamais leur destination.
    expect(serieClose([], 2, true)).toBe(true)
    expect(serieClose([saisie], 2, true)).toBe(true)
  })

  it('n’est pas close pour un archer non forfait dont la série traîne', () => {
    expect(serieClose([], 2, false)).toBe(false)
  })
})

describe('panneauOuvert / apresRetour', () => {
  // Le piège que ces deux fonctions existent pour éviter : le lien manuel a donné un second sens à
  // « fermé » (« j'ai jeté un œil ») là où il n'en avait qu'un (« j'ai vu le panneau de fin »).
  // Sans distinction, une consultation en cours de saisie éteint la bascule automatique de fin de
  // cible — c'est-à-dire le CA central de l'US, en silence.
  it('s’ouvre tout seul quand la cible a fini', () => {
    expect(panneauOuvert({ cibleClose: true, ferme: false, force: false })).toBe(true)
  })

  it('reste fermé tant que la cible tire', () => {
    expect(panneauOuvert({ cibleClose: false, ferme: false, force: false })).toBe(false)
  })

  it('s’ouvre à la main même si la cible tire encore', () => {
    expect(panneauOuvert({ cibleClose: false, ferme: false, force: true })).toBe(true)
  })

  it('ne se rouvre pas tout seul après avoir été vu', () => {
    expect(panneauOuvert({ cibleClose: true, ferme: true, force: false })).toBe(false)
  })

  it('consulter puis refermer en cours de saisie laisse la bascule automatique armée', () => {
    const suite = apresRetour({ cibleClose: false })
    expect(panneauOuvert({ cibleClose: false, ...suite })).toBe(false)
    // …et quand la cible finit, il s'ouvre bien tout seul.
    expect(panneauOuvert({ cibleClose: true, ...suite })).toBe(true)
  })

  it('refermer le panneau de fin de cible le consomme', () => {
    const suite = apresRetour({ cibleClose: true })
    expect(panneauOuvert({ cibleClose: true, ...suite })).toBe(false)
  })
})

describe('alerte', () => {
  it('remonte l’avertissement de placement du serveur', () => {
    const separe = archer({ prochain: prochain({ alerte: 'placement à revoir' }) })
    expect(alerte(separe)).toBe('placement à revoir')
  })

  it('est nulle quand le placement est sain', () => {
    expect(alerte(archer())).toBeNull()
  })

  it('ne s’applique qu’à un archer qui a un duel devant lui', () => {
    expect(alerte(archer({ issue: 'termine', prochain: null }))).toBeNull()
  })
})

describe('posesParCible — le pas de tir en « mes archers »', () => {
  // ⚠️ La règle testée ici est celle qu'un correctif de revue a dû poser : **la butte reste
  // entière, adversaire compris**. Sur un tableau de duels, le voisin de cible *est* l'adversaire ;
  // filtrer ligne à ligne comme on filtre le reste de l'écran cachait contre qui l'archer suivi
  // tire, et laissait croire à une butte à un seul tireur.
  const moi = archer({ archer_id: 1, prochain: prochain({ cible: 7, position: 'A' }) })
  const monAdversaire = archer({
    archer_id: 2,
    nom: 'DURAND',
    prochain: prochain({ cible: 7, position: 'B' }),
  })
  const ailleurs = archer({ archer_id: 3, prochain: prochain({ cible: 9, position: 'A' }) })
  const tous = [moi, monAdversaire, ailleurs]

  it('rend la butte entière quand un seul de ses tireurs est suivi', () => {
    const poses = posesParCible([moi], tous, true)

    expect(poses.map((l) => l.archer_id)).toEqual([1, 2])
  })

  it('écarte les buttes où aucun archer suivi ne tire', () => {
    const poses = posesParCible([moi], tous, true)

    expect(poses.map((l) => l.archer_id)).not.toContain(3)
  })

  it('rend tout le pas de tir hors centrage', () => {
    const poses = posesParCible([], tous, false)

    expect(poses.map((l) => l.archer_id)).toEqual([1, 2, 3])
  })

  it('ne rend aucune butte quand aucun archer suivi n’est posé', () => {
    // Cas réel : les archers suivis sont en lice mais leur cible n'est pas encore attribuée (les
    // tours ≥ 2 la reçoivent au lancement). La section « en lice, cible pas encore attribuée » les
    // porte ; le pas de tir, lui, n'a rien à montrer — et surtout pas tout le tournoi.
    expect(posesParCible([], tous, true)).toEqual([])
  })

  it('ignore les archers sortis, même sur une butte retenue', () => {
    // ⚠️ L'archer sorti porte **une butte retenue** (3ᵉ passe de revue). Un premier jet lui donnait
    // `prochain: null` : il était alors écarté par le garde « pas de cible », jamais par son issue,
    // si bien que le test passait avec une implémentation qui ignore complètement `partitionner` —
    // c'est-à-dire fausse — tout en annonçant le contraire dans son titre.
    const sorti = archer({
      archer_id: 4,
      issue: 'termine',
      prochain: prochain({ cible: 7, position: 'C' }),
    })

    const poses = posesParCible([moi], [...tous, sorti], true)

    expect(poses.map((l) => l.archer_id)).toEqual([1, 2])
  })
})

// --- Big Shoot Off : la 5ᵉ issue (E05US028, correctif de revue) --------------------------------
//
// Ces tests ancrent un défaut qui était **entièrement côté front** : le serveur publiait
// `prochaine_manche`, ses DTO et trois tests backend verts, mais aucun consommateur front n'avait
// été touché. Les finalistes lisaient « Destination inconnue » et étaient rangés avec les sortis —
// le scénario de recette de l'US était infaisable en salle.
describe('routage d’un finaliste de Big Shoot Off', () => {
  function finaliste(patch: Partial<RoutageArcher> = {}): RoutageArcher {
    return archer({
      issue: 'prochaine_manche',
      prochain: null,
      prochaine_manche: {
        numero: 2,
        elimine: 2,
        cible: null,
        position: null,
        manque: 'cible non attribuée',
      },
      ...patch,
    })
  }

  it('annonce la manche qui vient, pas « Destination inconnue »', () => {
    expect(titre(finaliste())).toBe('Manche 2')
  })

  it('dit combien d’archers sortent à ce tour, et nomme la cible manquante', () => {
    expect(detail(finaliste())).toBe('2 archers sortent · cible non attribuée')
  })

  it('accorde le singulier quand un seul archer sort', () => {
    const seul = finaliste({
      prochaine_manche: {
        numero: 3,
        elimine: 1,
        cible: null,
        position: null,
        manque: null,
      },
    })
    expect(detail(seul)).toBe('1 archer sort')
  })

  it('le compte comme encore en lice — sinon il rentre chez lui au milieu de la finale', () => {
    expect(encoreEnLice(finaliste())).toBe(true)
    // Sur une phase de Big Shoot Off, les finalistes **sont** le pas de tir : ils vont en attente
    // (pas de plan de cibles, `DETTE-059`), surtout pas sous « Sortis du tableau ».
    const { attente, sortis } = partitionner([finaliste()])
    expect(attente.map((l) => l.archer_id)).toEqual([1])
    expect(sortis).toEqual([])
  })

  it('n’affiche pas d’alerte de placement : un Big Shoot Off n’oppose personne', () => {
    expect(alerte(finaliste())).toBeNull()
  })
})
