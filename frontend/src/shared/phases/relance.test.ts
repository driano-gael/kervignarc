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
  peutPoserUnePause,
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
    // Miroir de `TYPES_DEROULES` côté domaine : ailleurs l'arrêt serait accepté puis **inerte**, et
    // l'organisateur le découvrirait le jour J — ce que le refus existe pour empêcher.
    expect(peutPoserUnePause(phase({ type: 'qualification' }))).toBe(false)
  })

  it('ne l’offre pas quand le tour courant est inconnu', () => {
    // Sans origine, « dans x tours » ne se compte pas. Deviner couperait au mauvais endroit.
    expect(peutPoserUnePause(phase({ tourCourant: null }))).toBe(false)
  })

  it('ne l’offre pas sur une phase d’un seul tour', () => {
    // `nb_tours <= 1` est la signature du repli d'`avancement_bloc` (« je ne sais pas »), et une
    // phase d'un seul tour n'a de toute façon aucune frontière intérieure où couper.
    expect(peutPoserUnePause(phase({ nbTours: 1 }))).toBe(false)
  })
})
