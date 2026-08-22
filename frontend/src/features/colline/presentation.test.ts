// E05US027 — ce que l'écran de la colline dit : l'attente nommée, le repos, ce qui manque.
//
// Ces fonctions portent des CA de l'US — « la manche suivante n'apparaît qu'une fois la précédente
// close, et l'écran le dit », « l'archer au repos est dit en attente, jamais terminé » —, donc
// elles vivent hors du `.tsx` et se testent sans monter de DOM.

import { describe, expect, it } from 'vitest'

import type { Duel, Duelliste } from '../saisie-duels/api'
import type { Defi } from './api'
import {
  ceQuiManque,
  decrireDefi,
  etatDefi,
  motDeLaFin,
  nomDeLArcher,
  nommerAuRepos,
  type MancheLisible,
} from './presentation'

function archer(id: number, nom = `N${id}`): Duelliste {
  return { archer_id: id, nom, prenom: 'P' }
}

function manche(numero: number, close: boolean, auRepos: Duelliste[] = []): MancheLisible {
  return {
    numero,
    close,
    au_repos: auRepos,
    defis: [{ haut: archer(1), bas: archer(2) }],
  }
}

function duel(patch: Partial<Duel> = {}): Duel {
  return {
    manches: [],
    resultat: null,
    validee_par: null,
    ...patch,
  } as unknown as Duel
}

function defi(numero: number, patch: Partial<Defi> = {}): Defi {
  return {
    numero,
    manche: 1,
    position_haute: 1,
    position_basse: 2,
    couloirs: null,
    haut: archer(1, 'MARTIN'),
    bas: archer(2, 'DURAND'),
    duel: duel(),
    desynchronisee: false,
    ...patch,
  }
}

describe('la lecture d’un défi', () => {
  it('dit qui défie qui, dans le vocabulaire du format', () => {
    // ⚠️ **C'est l'information que le public suit.** Une rencontre de poule ou de ronde oppose deux
    // archers sans hiérarchie préalable ; ici l'un défie l'autre depuis une position plus basse, et
    // dire « MARTIN contre DURAND » perdrait qui monte si l'un gagne.
    expect(decrireDefi(4, 6)).toBe('le 6 défie le 4')
  })

  it('classe les états dans l’ordre où ils priment', () => {
    // La désynchronisation prime sur tout : un défi bloqué annoncé « à tirer » ferait attendre des
    // archers devant une cible où le serveur refuse toute écriture.
    expect(etatDefi(defi(1, { desynchronisee: true, duel: duel({ validee_par: 'ROUX' }) }))).toBe(
      'tir mis de côté — population à rétablir',
    )
    expect(etatDefi(defi(1, { duel: duel({ validee_par: 'ROUX' }) }))).toBe('validée')
    expect(
      etatDefi(defi(1, { duel: duel({ validation_en_attente: true } as Partial<Duel>) })),
    ).toBe('validation en attente')
    expect(
      etatDefi(defi(1, { duel: duel({ resultat: { termine: true } } as Partial<Duel>) })),
    ).toBe('à valider')
    expect(etatDefi(defi(1, { duel: duel({ manches: [{}] } as unknown as Partial<Duel>) }))).toBe(
      'en cours',
    )
    expect(etatDefi(defi(1))).toBe('à tirer')
  })
})

describe('le mot de la fin', () => {
  it('nomme l’attente quand la manche courante n’est pas close et qu’il en reste', () => {
    // Sans cette phrase, il ne reste qu'une absence : le scoreur ne peut pas distinguer « plus rien
    // à jouer » de « il reste des défis à saisir avant que la suite existe ».
    expect(motDeLaFin([manche(1, true), manche(2, false)], 3)).toEqual({
      etat: 'attente',
      courante: 2,
      suivante: 3,
    })
  })

  it('annonce la fin quand toutes les manches dues sont closes', () => {
    expect(motDeLaFin([manche(1, true), manche(2, true)], 2)).toEqual({ etat: 'fini' })
  })

  it('se tait quand la DERNIÈRE manche due est en cours', () => {
    // ⚠️ Le troisième état, et celui qu'une condition écrite dans le JSX rendrait invisible au
    // test : il n'y a pas de manche suivante à promettre, et rien n'est terminé non plus. Se taire
    // est la seule réponse juste — annoncer « fini » serait faux, annoncer une manche 3 aussi.
    expect(motDeLaFin([manche(1, true), manche(2, false)], 2)).toBeNull()
  })

  it('se tait sur une phase sans manche', () => {
    expect(motDeLaFin([], 3)).toBeNull()
  })
})

describe('les archers au repos', () => {
  it('les nomme plutôt que de les laisser disparaître', () => {
    // ⚠️ **Ce n'est pas un bye** : personne ne gagne rien et personne ne bouge. Et ce n'est pas un
    // cas limite d'effectif impair — à portée 1, ce sont les **deux extrémités** de la colline une
    // manche sur deux, quel que soit l'effectif. Sans cette liste, le scoreur les cherche.
    expect(nommerAuRepos(manche(2, false, [archer(3, 'LE GOFF'), archer(4, 'ROUX')]))).toEqual([
      'LE GOFF P',
      'ROUX P',
    ])
  })

  it('rend une liste vide sur une manche où tout le monde tire', () => {
    // Le régime de la manche 1 à portée 1 : la réponse normale, pas un cas d'erreur.
    expect(nommerAuRepos(manche(1, false))).toEqual([])
  })
})

describe('le nom d’un archer', () => {
  it('le retrouve dans les défis', () => {
    expect(nomDeLArcher([manche(1, true)], 2)).toBe('N2 P')
  })

  it('le retrouve aussi quand il se repose', () => {
    // Le repli inverse serait visible à l'écran : un archer au repos en manche 1 n'apparaîtrait
    // qu'en `#3` dans la colline, à côté de noms complets.
    expect(nomDeLArcher([manche(1, true, [archer(3, 'LE GOFF')])], 3)).toBe('LE GOFF P')
  })

  it('rend un identifiant plutôt qu’un vide s’il ne figure nulle part', () => {
    expect(nomDeLArcher([manche(1, true)], 99)).toBe('#99')
  })
})

describe('ce qui manque dans une manche en cours', () => {
  it('sépare les quatre attentes, qui n’appellent pas le même geste', () => {
    // ⚠️ La distinction décide de **qui doit agir** : un défi non saisi attend le scoreur de sa
    // cible, un défi saisi et non validé attend un geste de validation, un défi en file attend le
    // **réseau** (personne n'a rien à faire), un défi bloqué attend un rétablissement de
    // population. Les confondre renvoie chercher partout dans un gymnase (`P-3`).
    const manque = ceQuiManque([
      defi(1),
      defi(2, { duel: duel({ resultat: { termine: true } } as Partial<Duel>) }),
      defi(3, { duel: duel({ validation_en_attente: true } as Partial<Duel>) }),
      defi(4, { desynchronisee: true }),
      defi(5, { duel: duel({ validee_par: 'ROUX' }) }),
    ])

    expect(manque.aSaisir).toHaveLength(1)
    expect(manque.aValider).toHaveLength(1)
    expect(manque.enFile).toHaveLength(1)
    expect(manque.bloques).toHaveLength(1)
  })

  it('nomme les défis par leurs positions et par les archers', () => {
    // Les positions d'abord : c'est ce qui permet de retrouver la cible dans la salle.
    expect(ceQuiManque([defi(1)]).aSaisir[0]).toBe('le 2 défie le 1 — MARTIN P / DURAND P')
  })

  it('n’appelle pas « à valider » un défi à demi tiré', () => {
    // ⚠️ `resultat.termine` et non `manches.length > 0` : proposer une validation que
    // `Duel.valider` refuse (`DuelIncomplet`) enverrait le scoreur buter sur un 422.
    const manque = ceQuiManque([
      defi(1, { duel: duel({ manches: [{}] } as unknown as Partial<Duel>) }),
    ])

    expect(manque.aValider).toEqual([])
    expect(manque.aSaisir).toHaveLength(1)
  })
})
