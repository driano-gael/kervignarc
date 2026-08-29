// Tests des axes de l'admin et de la lecture d'adresse (E14US003, ADR-0058/0059). Partie pure.

import { describe, expect, it } from 'vitest'
import {
  AXES,
  AXE_PAR_DESTINATION,
  contextePilotage,
  BESOIN_TOURNOI,
  analyserSegmentsAdmin,
  destinationDunArcher,
  destinationDunResultat,
  destinationParDefaut,
  elementRetenu,
  OUVRE_UN_ELEMENT,
  segmentsCanoniques,
  destinationValide,
  segmentsAdmin,
  type Axe,
} from './axes'
import { AIDE_ECRANS, type DestinationAdminId } from './aide-ecrans'

describe('répartition des destinations', () => {
  it('CA — les 33 destinations livrées sont toutes rangées, aucune perdue', () => {
    // Le risque n°1 d'E14US003 : des destinations réétiquetées à la main. Une entrée oubliée
    // disparaîtrait **silencieusement** de la sidebar (elle est filtrée par axe), sans que `tsc` ni
    // aucun autre test ne le voie. ⚠️ Ce garde-fou est tombé à l'ajout d'E16US012, et c'est
    // **exactement** ce qu'on lui demande : il n'y a aucun moyen de l'oublier, puisqu'une
    // destination ajoutée sans son entrée d'aide (ou sans son axe) le fait échouer avant
    // d'atteindre la sidebar.

    // ⚠️ E16US010 a **retiré** « Doublons » (absorbée par la ligne d'archer) et **ajouté**
    // « archer » (la fiche du pilotage) : le compte revient à son point de départ par deux
    // mouvements contraires. Une destination retirée doit l'être des trois tables à la fois, et
    // c'est ce test qui l'impose.
    const rangees = Object.keys(AXE_PAR_DESTINATION)
    const toutes = Object.keys(AIDE_ECRANS)
    expect(toutes).toHaveLength(33)
    expect(rangees).toHaveLength(32)
    // La dernière est « tournoi » : elle n'appartient à aucun axe, c'est l'assemblage porté par
    // l'accueil.
    expect(toutes.filter((d) => !rangees.includes(d))).toEqual(['tournoi'])
  })

  it('chaque destination est rangée dans un axe connu', () => {
    const axes = new Set(Object.values(AXE_PAR_DESTINATION))
    expect(axes).toEqual(new Set<Axe>(['atelier', 'pilotage', 'gestion']))
  })

  it('CA — l’atelier ne travaille pas sur un tournoi ; le pilotage et la gestion, si', () => {
    expect(AXES.find((a) => a.axe === 'atelier')!.besoinTournoi).toBe(false)
    expect(AXES.find((a) => a.axe === 'pilotage')!.besoinTournoi).toBe(true)
    expect(AXES.find((a) => a.axe === 'gestion')!.besoinTournoi).toBe(true)
  })
})

describe('destinationParDefaut', () => {
  it('le pilotage ouvre sur le tableau de bord (D-20)', () => {
    expect(destinationParDefaut('pilotage')).toBe('accueil')
  })

  it('la gestion ouvre sur les inscriptions', () => {
    expect(destinationParDefaut('gestion')).toBe('inscriptions')
  })

  it('l’ouverture d’un axe appartient TOUJOURS à cet axe', () => {
    // Sans ce garde, `entrerDansAxe` produirait une adresse que la validation rejette, et l'écran
    // affiché ne correspondrait pas à l'adresse — exactement ce que la validation existe pour éviter.
    for (const { axe } of AXES) {
      expect(
        AXE_PAR_DESTINATION[destinationParDefaut(axe) as keyof typeof AXE_PAR_DESTINATION],
      ).toBe(axe)
    }
  })

  it('CA E01US023 — AUCUNE destination de l’atelier n’exige un tournoi (DETTE-023 résorbée)', () => {
    // Le garde-fou a changé de nature, et c'est le fait notable : il disait « n'ouvre pas sur une
    // brique bloquée » — un contournement, tant que quatre destinations réclamaient un tournoi que
    // l'axe ne propose pas de choisir. Depuis ADR-0060 il n'y a plus de brique bloquée, donc on
    // vérifie l'invariant **fort**. ⚠️ Sa première version n'assertait que des appartenances d'axe,
    // `besoinTournoi` vivant hors de portée du test : elle passait au vert **alors que `simulation`
    // exigeait encore un tournoi** — un test qui affirme sans pouvoir lire est pire que pas de
    // test.
    const destinationsAtelier = Object.entries(AXE_PAR_DESTINATION)
      .filter(([, axe]) => axe === 'atelier')
      .map(([destination]) => destination as keyof typeof BESOIN_TOURNOI)

    expect(destinationsAtelier.filter((d) => BESOIN_TOURNOI[d])).toEqual([])
    expect(destinationsAtelier).toContain('categories')
    expect(destinationsAtelier).toContain('formats')
    // E01US025 : l'atelier ouvre sur le **format de tournoi**, son point d'entrée — et non plus sur
    // `categories`, qui n'est qu'une des briques que le format assemble.
    expect(destinationParDefaut('atelier')).toBe('formats')
  })

  it('les destinations qui règlent UNE édition sont au pilotage, pas à l’atelier', () => {
    // Le critère qui a fait bouger ces trois-là (ADR-0060 §6) : `plan` (la copie d'un tournoi) est
    // au pilotage tandis que `gabarits` (le modèle) est à l'atelier — on applique le même partage.
    const reglentUneEdition: DestinationAdminId[] = ['bareme', 'phases', 'simulation']
    for (const destination of reglentUneEdition) {
      expect(AXE_PAR_DESTINATION[destination as keyof typeof AXE_PAR_DESTINATION]).toBe('pilotage')
    }
  })

  it('toute destination rangée déclare si elle exige un tournoi', () => {
    // Garde-fou de complétude : `BESOIN_TOURNOI` et `AXE_PAR_DESTINATION` doivent couvrir les
    // mêmes clés. Le typage `Record` exhaustif l'impose déjà à la compilation ; ce test le dit à
    // l'exécution, pour que l'échec soit lisible plutôt qu'un message de `tsc`.
    expect(Object.keys(BESOIN_TOURNOI).sort()).toEqual(Object.keys(AXE_PAR_DESTINATION).sort())
  })
})

describe('analyserSegmentsAdmin', () => {
  it('sans segment : accueil de l’admin, aucun tournoi', () => {
    expect(analyserSegmentsAdmin([])).toEqual({
      tournoiId: null,
      axe: null,
      destinationDemandee: null,
      elementDemande: null,
    })
  })

  it('reconnaît un axe seul', () => {
    expect(analyserSegmentsAdmin(['pilotage'])).toEqual({
      tournoiId: null,
      axe: 'pilotage',
      destinationDemandee: null,
      elementDemande: null,
    })
  })

  it('reconnaît tournoi + axe + destination', () => {
    expect(analyserSegmentsAdmin(['12', 'pilotage', 'supervision'])).toEqual({
      tournoiId: 12,
      axe: 'pilotage',
      destinationDemandee: 'supervision',
      elementDemande: null,
    })
  })

  it('le tournoi est reconnu à sa FORME, sans ambiguïté avec un axe', () => {
    // Aucun axe ni aucune destination n'est numérique : la distinction est totale.
    expect(analyserSegmentsAdmin(['atelier', 'gabarits']).tournoiId).toBeNull()
    expect(analyserSegmentsAdmin(['7']).tournoiId).toBe(7)
    expect(analyserSegmentsAdmin(['7']).axe).toBeNull()
  })

  it('CA E16US010 — un 4ᵉ segment nomme l’élément que la destination doit ouvrir', () => {
    // Sans lui, un résultat de recherche ne peut rien dire de plus que « va sur cet écran » :
    // l'état d'ouverture vivait en useState local à la ligne, hors d'atteinte (ADR-0100).
    expect(analyserSegmentsAdmin(['12', 'gestion', 'inscriptions', '57']).elementDemande).toBe(57)
  })

  it('un élément SANS destination pour l’ouvrir est ignoré', () => {
    // L'adresse porterait sinon un état que rien ne consomme.
    expect(analyserSegmentsAdmin(['12', 'gestion', '57']).elementDemande).toBeNull()
  })

  it('sur l’accueil, « fiche » demande d’ouvrir le tournoi courant', () => {
    // La liste des tournois vit sur l'accueil, qui n'a ni axe ni destination : un 4ᵉ segment ne
    // l'atteint pas. `/admin/12` dit « c'est celle-là », `/admin/12/fiche` dit « ouvre-la ».
    expect(analyserSegmentsAdmin(['12', 'fiche']).elementDemande).toBe(12)
    expect(analyserSegmentsAdmin(['12']).elementDemande).toBeNull()
    expect(analyserSegmentsAdmin(['12', 'fiche']).axe).toBeNull()
  })

  it('« fiche » sans tournoi n’ouvre rien', () => {
    expect(analyserSegmentsAdmin(['fiche']).elementDemande).toBeNull()
  })

  it('sur l’accueil, un AUTRE tournoi que le courant s’ouvre sans le remplacer', () => {
    // ⚠️ Le défaut corrigé en revue : `/admin/7/fiche` faisait de 7 le tournoi de travail, et le
    // refermer renvoyait sur `/admin` nu. Deux slots, deux sens (ADR-0100 §2).
    const route = analyserSegmentsAdmin(['12', 'fiche', '7'])

    expect(route.tournoiId).toBe(12)
    expect(route.elementDemande).toBe(7)
  })

  it('aucun axe ne s’appelle « fiche » — sinon la forme d’accueil deviendrait inatteignable', () => {
    // Une ligne, parce que le jour où un axe porterait ce nom, `/admin/12/fiche` cesserait
    // silencieusement d'ouvrir un formulaire pour entrer dans un axe.
    expect(AXES.map((a) => a.axe)).not.toContain('fiche')
  })

  it('un axe inconnu retombe sur l’accueil, pas sur une page vide', () => {
    expect(analyserSegmentsAdmin(['preparation', 'blasons'])).toEqual({
      tournoiId: null,
      axe: null,
      destinationDemandee: null,
      elementDemande: null,
    })
  })
})

describe('segmentsAdmin', () => {
  it('est la réciproque exacte d’analyserSegmentsAdmin', () => {
    const cas: [number | null, Axe | null, DestinationAdminId | null][] = [
      [null, null, null],
      [null, 'atelier', 'gabarits'],
      [12, 'pilotage', 'supervision'],
      [3, 'gestion', 'paiements'],
    ]
    for (const [tournoiId, axe, destination] of cas) {
      const segments = segmentsAdmin(tournoiId, axe, destination)
      const relu = analyserSegmentsAdmin(segments)
      expect(relu.tournoiId).toBe(tournoiId)
      expect(relu.axe).toBe(axe)
      expect(relu.destinationDemandee).toBe(axe === null ? null : destination)
    }
  })

  it('l’élément ouvert fait l’aller-retour, sous ses deux formes', () => {
    // Réciprocité : c'est elle qui garantit qu'un lien copié rouvre la même fiche après un F5.
    expect(segmentsAdmin(12, 'gestion', 'inscriptions', 57)).toEqual([
      '12',
      'gestion',
      'inscriptions',
      '57',
    ])
    expect(
      analyserSegmentsAdmin(segmentsAdmin(12, 'gestion', 'inscriptions', 57)).elementDemande,
    ).toBe(57)
    expect(segmentsAdmin(12, null, null, 12)).toEqual(['12', 'fiche'])
    expect(analyserSegmentsAdmin(segmentsAdmin(12, null, null, 12)).elementDemande).toBe(12)
  })

  it('l’élément n’est PAS jeté silencieusement sur l’accueil', () => {
    // Il l'était : `segmentsAdmin(12, null, null, 7)` rendait `['12']`, l'élément disparaissait
    // sans erreur — et c'est ce qui avait forcé l'appelant à confondre les deux slots.
    expect(segmentsAdmin(12, null, null, 7)).toEqual(['12', 'fiche', '7'])
    expect(segmentsAdmin(12, null, null, 12)).toEqual(['12', 'fiche'])
    // Refermer la fiche ne désélectionne pas le tournoi.
    expect(segmentsAdmin(12, null, null, null)).toEqual(['12'])
  })

  it('CA — le tournoi survit au changement d’écran et d’axe', () => {
    // C'est la promesse « un lien s'ouvre sur la même vue » : sans le tournoi dans l'adresse, 21
    // destinations sur 24 retombent sur « choisissez un tournoi » après un F5.
    expect(segmentsAdmin(12, 'gestion', 'inscriptions')).toEqual(['12', 'gestion', 'inscriptions'])
  })
})

describe('destinationValide', () => {
  it('accepte une destination proposée par l’axe', () => {
    expect(destinationValide('supervision', ['accueil', 'supervision'])).toBe('supervision')
  })

  it('REFUSE une destination qui appartient à un autre axe', () => {
    // Sans ce garde, /admin/atelier/supervision afficherait un écran de pilotage sous l'intitulé
    // « Atelier » — exactement le mélange que le découpage en axes supprime.
    expect(destinationValide('supervision', ['gabarits', 'clubs'])).toBeNull()
  })

  it('sans destination demandée : rien, l’axe choisira son ouverture', () => {
    expect(destinationValide(null, ['gabarits'])).toBeNull()
  })
})

// — Ligne de contexte de l'axe Pilotage (E17US003, planche A02). —
//
// Deux règles que le rendu ne montre pas, et qui sont donc à la charge du test : un tournoi **en
// pause** compte comme en cours, et l'absence rend `null` (pas une chaîne vide).
describe('contextePilotage', () => {
  it('nomme les tournois en cours', () => {
    expect(
      contextePilotage([
        { nom: 'Challenge des champions', statut: 'en_cours' },
        { nom: 'Nocturne extérieur', statut: 'en_cours' },
      ] as const),
    ).toBe('Challenge des champions · Nocturne extérieur')
  })

  it('compte un tournoi **en pause** comme en cours — il est lancé, il attend', () => {
    expect(contextePilotage([{ nom: 'Trophée de la ville', statut: 'en_pause' }] as const)).toBe(
      'Trophée de la ville',
    )
  })

  it.each([
    ['aucun tournoi', []],
    ['que des brouillons', [{ nom: 'À venir', statut: 'brouillon' }]],
    ['que du terminé ou de l’archivé', [{ nom: 'L’an dernier', statut: 'archive' }]],
  ] as const)('ne dit rien quand rien n’est en cours — %s', (_cas, tournois) => {
    // `null` et non `''` : l'appelant n'a pas à distinguer « rien à dire » de « quelque chose à
    // dire, mais vide ».
    expect(contextePilotage(tournois)).toBeNull()
  })
})

describe('destinationDunArcher', () => {
  it('CA — en PILOTAGE, un archer du tournoi courant ouvre sa fiche « en consultation »', () => {
    expect(destinationDunArcher('pilotage', 12, 12)).toEqual({
      axe: 'pilotage',
      destination: 'archer',
      tournoi: 12,
    })
  })

  it('CA — hors pilotage, il ouvre sa fiche « en modification »', () => {
    // Négatif apparié au positif ci-dessus : c'est le MOMENT qui décide, pas l'entité.
    expect(destinationDunArcher('gestion', 12, 12).destination).toBe('inscriptions')
    expect(destinationDunArcher('atelier', 12, 12).destination).toBe('inscriptions')
    expect(destinationDunArcher(null, 12, 12).destination).toBe('inscriptions')
  })

  it('un archer d’une AUTRE édition part à sa liste, dans SON tournoi', () => {
    // La fiche de pilotage lit sa place et ses créneaux : sur un archer d'ailleurs elle serait
    // vide, et le tournoi courant montrerait une fiche qui ne lui appartient pas.
    expect(destinationDunArcher('pilotage', 12, 7)).toEqual({
      axe: 'gestion',
      destination: 'inscriptions',
      tournoi: 7,
    })
  })

  it('sans tournoi porté par le résultat, on retombe sur le tournoi courant', () => {
    expect(destinationDunArcher('gestion', 12, null).tournoi).toBe(12)
  })
})

describe('segmentsCanoniques', () => {
  const route = {
    tournoiId: 12,
    axe: 'gestion' as const,
    destinationDemandee: 'inscriptions',
    elementDemande: 57,
  }

  it('BLOQUANT corrigé — la canonisation CONSERVE l’élément ouvert', () => {
    // La version d'origine vivait dans `CoquilleAdmin` et rappelait `segmentsAdmin` sans son 4ᵉ
    // argument : l'adresse était réécrite sans l'élément, et la fiche se refermait aussitôt.
    expect(segmentsCanoniques(route, 'gestion', 'inscriptions')).toEqual([
      '12',
      'gestion',
      'inscriptions',
      '57',
    ])
  })

  it('mais le LÂCHE quand la destination affichée n’est pas celle demandée', () => {
    // Négatif apparié : un signet périmé (`…/doublons/57`) ne doit pas ouvrir l'élément 57 sur la
    // destination de repli, qui ne le connaît pas.
    const perimee = { ...route, destinationDemandee: 'doublons' }

    expect(segmentsCanoniques(perimee, 'gestion', 'inscriptions')).toEqual([
      '12',
      'gestion',
      'inscriptions',
    ])
  })
})

describe('destinationDunResultat', () => {
  it('un club mène à l’atelier, en gardant le tournoi de travail', () => {
    expect(destinationDunResultat('club', null, 'pilotage', 12)).toEqual({
      axe: 'atelier',
      destination: 'clubs',
      tournoi: 12,
    })
  })

  it('un tournoi n’a NI axe NI destination — sa fiche vit sur l’accueil', () => {
    // C'est ce qui force l'appelant à passer par la forme `fiche` (ADR-0100 §3) : sans ce `null`,
    // il chercherait une destination qui n'existe pas.
    expect(destinationDunResultat('tournoi', 7, 'gestion', 12).destination).toBeNull()
  })

  it('un archer délègue à la règle du moment, sans la recopier', () => {
    expect(destinationDunResultat('archer', 12, 'pilotage', 12)).toEqual(
      destinationDunArcher('pilotage', 12, 12),
    )
  })
})

describe('OUVRE_UN_ELEMENT', () => {
  it('exactement trois destinations consomment un élément — celles qui sont câblées', () => {
    // ⚠️ Le `Record` exhaustif force une **réponse** à la compilation, il ne garde aucune
    // **valeur** : basculer `supervision` à `true` ne faisait rien tomber (relevé en 3ᵉ passe).
    // Ces trois-là sont celles auxquelles `CoquilleAdmin` passe réellement `ouvrir`.
    const consommatrices = Object.entries(OUVRE_UN_ELEMENT)
      .filter(([, ouvre]) => ouvre)
      .map(([destination]) => destination)
      .sort()

    expect(consommatrices).toEqual(['archer', 'clubs', 'inscriptions'])
  })

  it('une destination qui ne consomme PAS d’élément le lâche de l’adresse', () => {
    // C'est la seconde garde d'`elementRetenu`, celle qui n'était exercée nulle part.
    const route = {
      tournoiId: 12,
      axe: 'pilotage' as const,
      destinationDemandee: 'supervision',
      elementDemande: 57,
    }

    expect(elementRetenu(route, 'supervision')).toBeNull()
    expect(segmentsCanoniques(route, 'pilotage', 'supervision')).toEqual([
      '12',
      'pilotage',
      'supervision',
    ])
  })

  it('et une destination qui le consomme le GARDE — l’exclusion n’est pas globale', () => {
    const route = {
      tournoiId: 12,
      axe: 'gestion' as const,
      destinationDemandee: 'inscriptions',
      elementDemande: 57,
    }

    expect(elementRetenu(route, 'inscriptions')).toBe(57)
  })
})
