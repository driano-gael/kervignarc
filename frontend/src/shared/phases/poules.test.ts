// Le modèle du réglage de poules (E05US023) — conversions et aperçu de répartition.
//
// L'oracle est le **CA** de `stories/E05-moteur-phases.md` pour la répartition (« 32 archers en
// poules de 4 donnent 8 poules de 4 ; 30 archers donnent 7 poules — cinq de 4 et deux de 5 ») et
// le comportement du domaine pour le serpent (`composer_poules`), que ce module **mire**.

import { describe, expect, it } from 'vitest'

import {
  decrireRepartition,
  depuisReglage,
  estValide,
  POULES_PAR_DEFAUT,
  repartition,
  versReglage,
} from './poules'

describe('repartition', () => {
  it('arrondit le nombre de groupes vers le bas', () => {
    // CA : « 32 archers en poules de 4 donnent 8 poules de 4 ».
    expect(repartition(32, 4)).toHaveLength(8)
    expect(repartition(32, 4).every((t) => t === 4)).toBe(true)
  })

  it('gonfle quelques poules plutôt que d’en créer une trop petite', () => {
    // CA : « 30 archers donnent 7 poules — cinq de 4 et deux de 5 ». Aucune poule sous la taille
    // demandée : c'est l'invariant retenu, l'inverse (8 poules dont deux de 3) a été écarté.
    const tailles = repartition(30, 4)
    expect(tailles).toHaveLength(7)
    expect(tailles.filter((t) => t === 5)).toHaveLength(2)
    expect(tailles.filter((t) => t === 4)).toHaveLength(5)
    expect(Math.min(...tailles)).toBeGreaterThanOrEqual(4)
  })

  it('gonfle les poules que le serpent gonfle, pas systématiquement les premières', () => {
    // Le serpent repart en sens inverse un passage sur deux : à 10 archers en poules de 3, le
    // dernier passage est le 4ᵉ (impair) et l'archer supplémentaire tombe dans la **dernière**
    // poule. Supposer « toujours les premières » ferait mentir l'aperçu sur le contenu du groupe 1.
    expect(repartition(10, 3)).toEqual([3, 3, 4])
    expect(repartition(30, 4)).toEqual([5, 5, 4, 4, 4, 4, 4])
  })

  it('ne descend jamais sous une poule, même à effectif serré', () => {
    // CA : « 7 archers en poules de 4 → une poule de 7, que l'organisateur voit et corrige s'il
    // n'en veut pas ». C'est précisément le cas que l'aperçu doit rendre visible.
    expect(repartition(7, 4)).toEqual([7])
  })

  it('ne rend rien sur une saisie illisible', () => {
    expect(repartition(0, 4)).toEqual([])
    expect(repartition(30, 1)).toEqual([])
    expect(repartition(Number.NaN, 4)).toEqual([])
  })
})

describe('decrireRepartition', () => {
  it('dit la répartition en clair, des plus grosses aux plus petites', () => {
    expect(decrireRepartition(repartition(30, 4))).toBe('7 poules : 2 de 5, 5 de 4')
  })

  it('accorde le singulier', () => {
    expect(decrireRepartition([7])).toBe('1 poule : 1 de 7')
  })

  it('ne dit rien quand il n’y a rien à dire', () => {
    expect(decrireRepartition([])).toBe('')
  })
})

describe('versReglage', () => {
  it('rend le régime « la poule classe » quand aucun qualifié n’est demandé', () => {
    // ADR-0083 §5 : `nb_qualifies` vide **est** le régime « la poule classe », et c'est lui qui fait
    // départager tout ex æquo irréductible au barrage.
    expect(versReglage(POULES_PAR_DEFAUT)?.nb_qualifies).toBeNull()
  })

  it('rend le nombre de qualifiés quand la poule qualifie', () => {
    const reglage = versReglage({ ...POULES_PAR_DEFAUT, produit: 'qualifies', qualifies: '2' })
    expect(reglage?.nb_qualifies).toBe(2)
  })

  it('écrit toujours le barème, même au défaut 3 / 1 / 0', () => {
    // Le barème est un **choix** de l'organisateur : le relire d'un défaut de code ferait changer
    // ses points de match le jour où le défaut change.
    expect(versReglage(POULES_PAR_DEFAUT)?.bareme).toEqual({ victoire: 3, nul: 1, defaite: 0 })
  })

  it('refuse une saisie en cours plutôt que d’inventer une valeur', () => {
    expect(versReglage({ ...POULES_PAR_DEFAUT, taille: '' })).toBeUndefined()
    expect(versReglage({ ...POULES_PAR_DEFAUT, taille: '1' })).toBeUndefined()
    expect(versReglage({ ...POULES_PAR_DEFAUT, victoire: '' })).toBeUndefined()
    expect(estValide({ ...POULES_PAR_DEFAUT, taille: '' })).toBe(false)
  })

  it('n’exige un nombre de qualifiés que si la poule qualifie', () => {
    expect(estValide({ ...POULES_PAR_DEFAUT, qualifies: '' })).toBe(true)
    expect(estValide({ ...POULES_PAR_DEFAUT, produit: 'qualifies', qualifies: '' })).toBe(false)
  })
})

describe('depuisReglage', () => {
  it('retombe sur le réglage par défaut quand la phase n’est pas réglée', () => {
    expect(depuisReglage(null)).toEqual(POULES_PAR_DEFAUT)
  })

  it('fait l’aller-retour sans rien perdre', () => {
    const etat = {
      taille: '5',
      produit: 'qualifies' as const,
      qualifies: '3',
      victoire: '2',
      nul: '1',
      defaite: '0',
      departage: true,
      mode: 'par_niveau' as const,
      serpentAssume: false,
    }
    const reglage = versReglage(etat)
    expect(reglage).toBeDefined()
    expect(depuisReglage(reglage!)).toEqual(etat)
  })

  it('lit « serpent » d’une étape enregistrée avant que le mode existe', () => {
    // Le backend n'écrit la clé qu'au mode non-défaut (c'est ce qui évite une migration) : une
    // étape d'avant E05US029 arrive donc sans elle, et le serpent est ce qu'elle jouait.
    const ancien = {
      taille_visee: 4,
      bareme: null,
      nb_qualifies: null,
      rencontres_par_archer: null,
      departage_inter_poules: false,
    }
    expect(depuisReglage(ancien)).toMatchObject({ mode: 'serpent', serpentAssume: false })
  })

  it('n’envoie pas la dérogation depuis un réglage par niveau', () => {
    // Sinon une case armée sous le serpent, puis abandonnée en basculant le mode, ressusciterait
    // au retour — en levant un refus que plus personne n'a assumé.
    const reglage = versReglage({
      ...POULES_PAR_DEFAUT,
      mode: 'par_niveau',
      serpentAssume: true,
    })
    expect(reglage?.serpent_assume).toBe(false)
  })
})

// --- E05US029 : la répartition par niveau, miroir de `_tranches_de_niveau` ------------------------
//
// L'oracle est le CA (« 36 archers → 6 poules de niveau : rangs 1-6, 7-12, 13-18, 19-24, 25-30,
// 31-36 ») et l'arbitrage du cadrage du 21/08/2026 sur le gonflement par le bas.

describe('répartition par niveau', () => {
  it('découpe l’effectif en tranches de rangs contiguës', () => {
    expect(decrireRepartition(repartition(36, 6, 'par_niveau'), 'par_niveau')).toBe(
      '6 poules de niveau : rangs 1-6, 7-12, 13-18, 19-24, 25-30, 31-36',
    )
  })

  it('gonfle les groupes du bas quand l’effectif ne tombe pas juste', () => {
    // 34 archers en poules de 6 → 5 groupes, 4 archers à replacer : les tranches du haut restent à
    // la taille visée. C'est la **même** règle que le domaine, recopiée et non supposée.
    expect(repartition(34, 6, 'par_niveau')).toEqual([6, 7, 7, 7, 7])
  })

  it('laisse le serpent inchangé', () => {
    expect(repartition(30, 4)).toEqual(repartition(30, 4, 'serpent'))
    expect(decrireRepartition(repartition(30, 4))).toBe('7 poules : 2 de 5, 5 de 4')
  })

  it('dit une poule de niveau au singulier', () => {
    expect(decrireRepartition(repartition(7, 4, 'par_niveau'), 'par_niveau')).toBe(
      '1 poule de niveau : rangs 1-7',
    )
  })
})
