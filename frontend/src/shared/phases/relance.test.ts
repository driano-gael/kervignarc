// Le rappel de relance (E05US034) — tests du front, écrits **depuis le CA**.
//
// L'oracle est la puce *« l'application rappelle qu'une phase attend sa relance. Pastille au tableau
// de bord (« 2 phases attendent votre relance depuis 14 min ») »* de `stories/E05-moteur-phases.md`
// § E05US034, et la phrase qui la suit : *« sans ce filet, la capacité livrée en E05US033 crée un
// mode de panne neuf »*.
//
// ⚠️ **Ce fichier ne teste ni le déclenchement ni l'horodatage** : les deux sont serveur, avec leurs
// oracles dans `backend/tests/test_service_arrets_programmes.py`. Ici ne vit que la traduction d'un
// instant en attente lisible — la seule règle que le front porte, et celle qui décide si
// l'organisateur regarde ou passe son chemin.

import { describe, expect, it } from 'vitest'

import {
  libelleEtatDuTour,
  peutPoserUnePause,
  phasesSuspendues,
  toursBloquablesRestants,
  phraseDeRelance,
  resumeDeRelance,
  type ArretQuiAttend,
  type PhasePosable,
} from './relance'

const MIDI = Date.parse('2026-03-14T12:00:00Z')

function arret(phases: number[], depuis: string | null = null): ArretQuiAttend {
  return { phases_arretees: phases, arrete_depuis: depuis }
}

describe('resumeDeRelance', () => {
  it('ne dit rien quand rien n’est éteint', () => {
    expect(resumeDeRelance([], MIDI)).toBeNull()
  })

  it('ne dit rien d’un arrêt qui n’a encore coupé aucune phase', () => {
    // Un arrêt de créneau **armé** dont chaque phase finit son tour n'a éteint personne : annoncer
    // une attente ferait décompter une salle où tout le monde tire encore.
    expect(resumeDeRelance([arret([])], MIDI)).toBeNull()
  })

  it('compte les phases éteintes, pas les arrêts', () => {
    // CA — « 2 phases attendent votre relance ». Un arrêt de portée créneau en éteint plusieurs d'un
    // coup ; annoncer « 1 pause » minimiserait ce que l'organisateur doit rallumer.
    const resume = resumeDeRelance([arret([7, 8, 9])], MIDI)

    expect(resume?.nbPhases).toBe(3)
  })

  it('ne compte pas deux fois une phase que deux arrêts revendiquent', () => {
    // Cas réel : un arrêt de créneau coupe la phase 7, un second arrêt armé la retrouve **déjà** en
    // pause et la compte comme arrêtée (`_resoudre_les_arrets_armes`). Sans dédoublonnage, la
    // pastille annoncerait 3 phases sur une salle qui en compte 2 — un chiffre faux dans le sens
    // qui alarme, donc celui qui use la vigilance le plus vite.
    const resume = resumeDeRelance([arret([7, 8]), arret([7])], MIDI)

    expect(resume?.nbPhases).toBe(2)
  })

  it('décompte depuis la plus ancienne extinction', () => {
    // C'est le chiffre qui **décide** : « ça fait 25 min » appelle un geste, « ça fait 1 min » non.
    // Prendre la plus récente ferait rajeunir l'attente à chaque nouvelle coupe.
    const resume = resumeDeRelance(
      [arret([7], '2026-03-14T11:35:00Z'), arret([8], '2026-03-14T11:58:00Z')],
      MIDI,
    )

    expect(resume?.minutes).toBe(25)
  })

  it('lit l’horodatage tel que le serveur le sérialise, offset explicite compris', () => {
    // ⚠️ Ce cas existe parce que les autres fixtures écrivent un `Z`, **forme que Pydantic n'émet
    // pas** : il rend `+00:00`. Une revue (E05US034) a montré que le vrai risque est en amont —
    // l'adapter SQLite rendait un `datetime` *naive*, donc une chaîne **sans offset**, que
    // `Date.parse` lit en **heure locale** : « depuis 120 min » sur une salle arrêtée depuis une
    // minute. Le garde-fou vit côté serveur (`test_arrets_api.py`) ; ici on épingle que la forme
    // réellement transmise est comprise, et que les deux notations donnent le même instant.
    const resume = resumeDeRelance([arret([7], '2026-03-14T11:35:00+00:00')], MIDI)

    expect(resume?.minutes).toBe(25)
  })

  it('reste muet sur la durée quand aucun arrêt n’est daté', () => {
    // Une base migrée en pleine journée garde ses franchissements sans leur heure (migration 0049).
    // La phrase doit tenir sans compteur : c'est elle qui porte le CA, pas le nombre de minutes.
    const resume = resumeDeRelance([arret([7])], MIDI)

    expect(resume).toEqual({ nbPhases: 1, minutes: null })
  })

  it('ne rend jamais une durée négative', () => {
    // L'horloge du poste d'admin peut être en avance de quelques secondes sur celle du serveur : un
    // « depuis -1 min » ferait douter de tout l'écran pour un écart sans importance.
    const resume = resumeDeRelance([arret([7], '2026-03-14T12:00:30Z')], MIDI)

    expect(resume?.minutes).toBe(0)
  })

  it('ignore une date illisible sans perdre le compte des phases', () => {
    // Le compteur est un confort, la phrase est le CA : une donnée abîmée ne doit pas faire
    // disparaître l'alerte.
    const resume = resumeDeRelance([arret([7], 'pas-une-date')], MIDI)

    expect(resume).toEqual({ nbPhases: 1, minutes: null })
  })
})

describe('phraseDeRelance', () => {
  it('écrit la phrase du CA', () => {
    expect(phraseDeRelance({ nbPhases: 2, minutes: 14 })).toBe(
      '2 phases attendent votre relance depuis 14 min.',
    )
  })

  it('accorde au singulier', () => {
    expect(phraseDeRelance({ nbPhases: 1, minutes: 3 })).toBe(
      'Une phase attend votre relance depuis 3 min.',
    )
  })

  it('dit « à l’instant » plutôt que « depuis 0 min »', () => {
    expect(phraseDeRelance({ nbPhases: 1, minutes: 0 })).toBe(
      'Une phase attend votre relance — à l’instant.',
    )
  })

  it('omet le compteur plutôt que d’inventer un zéro', () => {
    // Un compteur inventé est pire qu'un compteur absent : il ferait croire que la salle vient de
    // s'arrêter, donc qu'il n'y a pas urgence.
    expect(phraseDeRelance({ nbPhases: 2, minutes: null })).toBe(
      '2 phases attendent votre relance.',
    )
  })
})

describe('peutPoserUnePause — quand offrir « bloquer dans x tours »', () => {
  // Chaque cas correspond à un refus que le serveur prononcerait. Offrir un geste dont on sait déjà
  // qu'il sera refusé est ce que la table des transitions de cycle de vie évite déjà par ailleurs :
  // le laisser visible transforme un refus explicite en clic perdu au milieu de la salle.

  function phase(patch: Partial<PhasePosable> = {}): PhasePosable {
    return { statut: 'en_cours', type: 'suisse', tourCourant: 2, nbTours: 5, ...patch }
  }

  it('offre le geste sur une phase en cours dont le tour est lisible', () => {
    expect(peutPoserUnePause(phase())).toBe(true)
  })

  it('ne l’offre pas sur une phase qui n’a pas démarré', () => {
    expect(peutPoserUnePause(phase({ statut: 'a_venir' }))).toBe(false)
  })

  it('ne l’offre pas sur une phase déjà en pause', () => {
    // Rien à interrompre : la relance est le geste qui a du sens ici, pas une seconde coupe.
    expect(peutPoserUnePause(phase({ statut: 'en_pause' }))).toBe(false)
  })

  it('ne l’offre pas sur un type dont l’application ne lit pas le tour', () => {
    // Miroir de `TYPES_ARRETABLES` côté domaine : ailleurs l'arrêt serait accepté puis **inerte**,
    // et l'organisateur le découvrirait le jour J — ce que le refus existe pour empêcher.
    //
    // ⚠️ **Le cas de garde était la qualification jusqu'à E05US035**, qui l'a rendue arrêtable en
    // lui donnant un découpage en tours et un lecteur d'avancement (ADR-0093). L'échauffement prend
    // sa place, et il n'est pas près de la quitter : il n'a ni barème ni feuille de marque, donc
    // aucune donnée existante ne dit où il en est.
    expect(peutPoserUnePause(phase({ type: 'echauffement' }))).toBe(false)
  })

  it('l’offre désormais sur une qualification', () => {
    // CA E05US035 : le format que tout le monde tire cesse d'être le seul sur lequel on ne peut pas
    // programmer de pause.
    expect(peutPoserUnePause(phase({ type: 'qualification' }))).toBe(true)
  })

  it('ne l’offre pas quand le tour courant est inconnu', () => {
    // Sans origine, « dans x tours » ne se compte pas. Deviner couperait au mauvais endroit.
    expect(peutPoserUnePause(phase({ tourCourant: null }))).toBe(false)
  })

  it('ne l’offre pas au dernier tour de la phase', () => {
    // `apres_tour = tourCourant + x - 1`, et le serveur refuse `apres_tour >= nbTours` : à la
    // ronde 5 sur 5, **aucune** valeur saisie n'est acceptable. Offrir le formulaire garantissait
    // donc un 422, une fois par phase, sur toutes les phases (revue E05US034).
    expect(peutPoserUnePause(phase({ tourCourant: 5, nbTours: 5 }))).toBe(false)
  })

  it('l’offre encore à l’avant-dernier tour, où « dans 1 tour » reste jouable', () => {
    // Le cas adverse du précédent : sans lui, une condition trop stricte (`<` devenu `<=`)
    // fermerait le geste un tour trop tôt sans qu'aucun test ne rougisse.
    expect(peutPoserUnePause(phase({ tourCourant: 4, nbTours: 5 }))).toBe(true)
  })

  it('ne l’offre pas sur une phase d’un seul tour', () => {
    // `nb_tours <= 1` est la signature du repli d'`avancement_bloc` (« je ne sais pas »), et une
    // phase d'un seul tour n'a de toute façon aucune frontière intérieure où couper.
    expect(peutPoserUnePause(phase({ nbTours: 1 }))).toBe(false)
  })
})

describe('libelleEtatDuTour — « où en est cette phase »', () => {
  // Le CA était laissé ouvert par la fiche (« sur preuve d'usage ») et a été tranché dans l'US :
  // message circonstancié, aucune clôture persistée. Tranché ne veut pas dire testé — il ne l'était
  // pas, la règle vivant en conditions JSX (relevé en revue, axe B).

  it('dit l’unité du format et la position dans la phase', () => {
    expect(
      libelleEtatDuTour({ tour_courant: 3, nb_tours: 5, libelle_tour_courant: 'Ronde 3' }),
    ).toBe('Ronde 3 — tour 3 sur 5')
  })

  it('se tait sur une phase d’un seul tour', () => {
    // Une qualification est *une* étape : « tour 1 sur 1 » n'apprend rien et occupe une ligne.
    // `nb_tours <= 1` est aussi la signature du repli d'`avancement_bloc` (« je ne sais pas »).
    expect(
      libelleEtatDuTour({ tour_courant: 1, nb_tours: 1, libelle_tour_courant: 'Qualification' }),
    ).toBeNull()
  })

  it('se tait quand le tour n’est pas lisible', () => {
    expect(
      libelleEtatDuTour({ tour_courant: null, nb_tours: 5, libelle_tour_courant: null }),
    ).toBeNull()
  })

  it('dit la position sans inventer de préfixe quand le libellé manque', () => {
    // ⚠️ Le cas qui a motivé l'extraction : la version JSX repliait sur `Tour ${tour_courant}`, donc
    // rendait « Tour 3 — tour 3 sur 5 », le mot du repli redoublant la phrase qui suit.
    // ⚠️ Un premier correctif l'avait déclaré **mort**, ce qui était faux : `libelle_de_tour` rend
    // `null` pour toute unité `PHASE_ENTIERE`, pas seulement quand le tour est illisible (relevé en
    // 2ᵉ passe). Supprimer la phrase sur une hypothèse fausse l'aurait fait disparaître en silence
    // le jour où un tel type annoncerait plusieurs tours. On garde donc la position seule.
    expect(libelleEtatDuTour({ tour_courant: 3, nb_tours: 5, libelle_tour_courant: null })).toBe(
      'tour 3 sur 5',
    )
  })

  it('se tait quand il n’y a pas d’avancement du tout', () => {
    expect(libelleEtatDuTour(null)).toBeNull()
  })
})

describe('phasesSuspendues — ce que l’écran de salle doit annoncer', () => {
  // ⚠️ Cette suite existe à cause d'un bloquant de 2ᵉ passe. Le premier correctif annonçait « le tir
  // est suspendu » dès qu'une phase du créneau était en pause — sur une surface qui s'adresse au
  // gymnase entier, alors que la portée par défaut d'un arrêt est **la phase seule**. Les tests
  // d'alors ne pouvaient pas le voir : ils montaient un créneau à une seule phase, où « une phase
  // est en pause » et « la salle est arrêtée » sont indiscernables.

  it('se tait quand rien n’est en pause', () => {
    expect(
      phasesSuspendues([
        { statut: 'en_cours', type: 'suisse' },
        { statut: 'terminee', type: 'qualification' },
      ]),
    ).toBeNull()
  })

  it('annonce sans qualifier quand plus rien ne tire', () => {
    // La phrase générale est alors **vraie** : la salle est arrêtée.
    expect(
      phasesSuspendues([
        { statut: 'en_pause', type: 'suisse' },
        { statut: 'terminee', type: 'qualification' },
      ]),
    ).toEqual([])
  })

  it('nomme ce qui est suspendu quand une autre phase tire encore', () => {
    // **Le cas du bloquant.** Sans cette distinction, l'écran projeté faisait arrêter les archers du
    // tableau, qui n'étaient pas concernés.
    expect(
      phasesSuspendues([
        { statut: 'en_pause', type: 'suisse' },
        { statut: 'en_cours', type: 'elimination_directe' },
      ]),
    ).toEqual(['Système suisse'])
  })

  it('nomme les deux quand deux phases sont suspendues et qu’une troisième tire', () => {
    expect(
      phasesSuspendues([
        { statut: 'en_pause', type: 'suisse' },
        { statut: 'en_pause', type: 'poules' },
        { statut: 'en_cours', type: 'elimination_directe' },
      ]),
    ).toHaveLength(2)
  })

  it('ne compte pas une phase à venir comme du tir en cours', () => {
    // Sinon un déroulé normal — une phase arrêtée, les suivantes pas encore lancées — basculerait en
    // forme nominative alors que la salle est bel et bien à l'arrêt.
    expect(
      phasesSuspendues([
        { statut: 'en_pause', type: 'suisse' },
        { statut: 'a_venir', type: 'elimination_directe' },
      ]),
    ).toEqual([])
  })
})

describe('toursBloquablesRestants — la borne du champ de saisie', () => {
  // Elle doit valoir exactement `nb_tours - tour_courant`, parce que le serveur pose
  // `apres_tour = tour_courant + x - 1` et refuse `apres_tour >= nb_tours`. Écrite en dur dans le
  // JSX, cette coïncidence n'avait aucun oracle (relevé en revue).

  it('laisse bloquer jusqu’au dernier tour de la phase', () => {
    expect(
      toursBloquablesRestants({ statut: 'en_cours', type: 'suisse', tourCourant: 2, nbTours: 5 }),
    ).toBe(3)
  })

  it('n’en laisse qu’un à l’avant-dernier tour', () => {
    expect(
      toursBloquablesRestants({ statut: 'en_cours', type: 'suisse', tourCourant: 4, nbTours: 5 }),
    ).toBe(1)
  })

  it('n’en laisse aucun au dernier tour', () => {
    // Cohérent avec `peutPoserUnePause`, qui n'offre alors plus le formulaire : les deux règles
    // doivent tomber ensemble, sans quoi l'écran offrirait un champ borné à zéro.
    expect(
      toursBloquablesRestants({ statut: 'en_cours', type: 'suisse', tourCourant: 5, nbTours: 5 }),
    ).toBe(0)
    expect(
      peutPoserUnePause({ statut: 'en_cours', type: 'suisse', tourCourant: 5, nbTours: 5 }),
    ).toBe(false)
  })

  it('rend zéro plutôt qu’un nombre inventé quand le tour est illisible', () => {
    expect(
      toursBloquablesRestants({
        statut: 'en_cours',
        type: 'suisse',
        tourCourant: null,
        nbTours: 5,
      }),
    ).toBe(0)
  })
})
