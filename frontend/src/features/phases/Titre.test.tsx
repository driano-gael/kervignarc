// Le **titre de phase** et la **fiche dépliable**, sur l'écran des phases d'un tournoi (E16US002).
//
// Tests dérivés du CA d'A07 (`stories/E16-retours-maquettes.md` → E16US002) : « *un écran liste les
// phases du tournoi, une ligne par phase* » et « *ouvrir une ligne ouvre la fiche de la phase — son
// **titre** et ses **réglages propres au type*** ».
//
// ⚠️ **Ce fichier monte `Phases` en entier, pas un contrôle isolé** — même parti que
// `Decoupage.test.tsx`, et pour la raison que son en-tête raconte : un test de formatage ne voit
// pas un défaut de câblage. Ce qu'on garde ici n'est pas « le champ sait s'afficher », c'est
// « l'organisateur peut nommer sa phase, quel qu'en soit le type ».
//
// ⚠️ **Les requêtes sont portées à la LIGNE** (`ligne()`), jamais à l'écran. L'écran monte en
// permanence un formulaire d'**ajout** qui porte les mêmes libellés que la fiche : une requête
// globale y matcherait le formulaire d'ajout et resterait verte avec la fiche entièrement décâblée.
// C'est le défaut latent que `Decoupage.test.tsx` portait, découvert en écrivant cette US.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { ConfigPhase, EtapeDeroule } from './api'
import { getPhases, modifierPhase } from './api'
import { Phases } from './Phases'

vi.mock('./api', () => ({
  getPhases: vi.fn(),
  getAvancement: vi.fn(async () => []),
  ajouterPhase: vi.fn(),
  modifierPhase: vi.fn(),
  reordonnerPhases: vi.fn(),
  supprimerPhase: vi.fn(),
  changerStatutPhase: vi.fn(),
}))

const TABLEAU: EtapeDeroule = {
  id: 7,
  tournoi_id: 1,
  ordre: 1,
  type: 'elimination_directe',
  sources: [],
  effectif: null,
  barrage_jusqu_au: null,
  profondeur: null,
  poules: null,
  big_shoot_off: null,
  suisse: null,
  colline: null,
  decoupage: null,
  nb_volees: null,
  arrets: [],
  titre: null,
}

const QUALIFICATION: EtapeDeroule = {
  ...TABLEAU,
  id: 8,
  ordre: 1,
  type: 'qualification',
  nb_volees: 20,
}

function monter(phases: EtapeDeroule[]) {
  vi.mocked(getPhases).mockResolvedValue(phases)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<Phases tournoiId={1} />, { wrapper: Enveloppe })
}

function ligne(index = 0) {
  // ⚠️ **Filtré sur `.phase`, et ce n'est pas cosmétique** : `shared/phases/ReglageArrets` rend un
  // `<li>` **par pause programmée**, à l'intérieur d'une fiche. Indexer tous les `listitem` du
  // document est vert tant qu'aucune fixture ne porte d'arrêt — puis `ligne(1)` désignerait une
  // ligne de pause. C'est le piège que `ouvrirLaFiche` documente, déplacé d'un cran (relevé en revue).
  const element = screen.getAllByRole('listitem').filter((el) => el.classList.contains('phase'))[
    index
  ]
  if (element === undefined) throw new Error(`Aucune ligne de phase au rang ${index}.`)
  return within(element)
}

/** La config effectivement envoyée au serveur par le **dernier** `PUT`.
 *
 * ⚠️ `calls.at(-1)` et non `calls[0]` : les mocks ne sont pas réinitialisés entre les tests d'un
 * même fichier, donc lire le premier appel renvoie celui du test précédent — deux de ces
 * assertions passaient ainsi sur la charge utile d'un voisin.
 */
function configEnvoyee(): ConfigPhase {
  const appel = vi.mocked(modifierPhase).mock.calls.at(-1) as
    [number, number, ConfigPhase] | undefined
  if (appel === undefined) throw new Error('aucun PUT de phase n’a été émis')
  return appel[2]
}

async function ouvrirLaFiche(index = 0) {
  // ⚠️ **Le bouton se cherche DANS sa ligne, pas dans la liste globale.** Une fois une fiche
  // ouverte, son bouton devient « Fermer la fiche » : la liste des « Ouvrir la fiche » se décale,
  // et viser le n-ième élément de cette liste désigne la mauvaise ligne — ou aucune. Un premier
  // jet le faisait, et le clic partait dans le vide sans que l'assertion s'en aperçoive.
  await screen.findAllByRole('listitem')
  await userEvent.click(ligne(index).getByRole('button', { name: 'Ouvrir la fiche' }))
}

describe('le titre d’une phase', () => {
  it('remplace le libellé du type dans la liste quand il est renseigné', async () => {
    monter([{ ...TABLEAU, titre: 'Tableau des jeunes' }])

    expect(await screen.findByText('Tableau des jeunes')).toBeInTheDocument()
  })

  it('laisse le type tenir lieu de libellé quand il n’y en a pas', async () => {
    // Aucun déroulé existant n'a de titre : l'écran ne doit pas changer d'aspect pour eux.
    monter([TABLEAU])

    expect(await screen.findByText('Élimination directe')).toBeInTheDocument()
  })

  it('n’efface pas le type de la ligne : il devient un détail, il ne disparaît pas', async () => {
    // Sans lui, deux phases nommées ne diraient plus ce qu'elles **font** — et c'est justement
    // quand le déroulé porte plusieurs phases du même type que les titres servent.
    monter([{ ...TABLEAU, titre: 'Tableau des jeunes' }])
    await screen.findByText('Tableau des jeunes')

    expect(ligne().getByText(/Élimination directe/)).toBeInTheDocument()
  })

  it('distingue à l’œil deux phases de même type, ce qui est la raison d’être du champ', async () => {
    // Le CA voisin — « plusieurs phases de type qualification aux réglages différents » — a été
    // livré côté moteur par E05US024/E05US025. Sans titre, l'écran les rendait identiques : même
    // libellé de type, seul le rang pour les distinguer.
    monter([
      { ...QUALIFICATION, id: 1, ordre: 1, titre: 'Qualification jeunes' },
      { ...QUALIFICATION, id: 2, ordre: 2, titre: 'Qualification adultes' },
    ])

    expect(await screen.findByText('Qualification jeunes')).toBeInTheDocument()
    expect(screen.getByText('Qualification adultes')).toBeInTheDocument()
  })
})

describe('la fiche d’une phase', () => {
  it('est fermée au départ : la liste reste une liste', async () => {
    // C'est le fond du refus A07 — l'écran empilait tous les réglages à plat. Une liste de dix
    // phases qui déplierait tout serait le même mur, une US plus tard.
    monter([TABLEAU])
    await screen.findAllByRole('button', { name: 'Ouvrir la fiche' })

    expect(ligne().queryByLabelText(/Titre de la phase/)).not.toBeInTheDocument()
  })

  it('porte le titre et les réglages du type une fois ouverte', async () => {
    // ⚠️ **La seconde assertion manquait** (relevé en revue) : le test ne gardait que la moitié
    // « titre » du CA, alors que la bascule est désormais l'**unique** chemin vers
    // `FormulairePhase` — le bouton « Éditer » a disparu. `Profondeur.test.tsx` et
    // `Arrets.test.tsx` montent le formulaire **directement**, donc aucun test ne gardait ce
    // chemin : pour tout type non-qualification, rien ne prouvait que la fiche expose ses réglages.
    // C'est la classe « composant livré, appelant non monté » que ce dossier a déjà payée trois fois.
    monter([TABLEAU])
    await ouvrirLaFiche()

    expect(ligne().getByLabelText(/Titre de la phase/)).toBeInTheDocument()
    expect(ligne().getByText(/Pauses programmées/)).toBeInTheDocument()
  })

  it('s’ouvre aussi sur la qualification, qui n’en avait aucune', async () => {
    // ⚠️ **Le cas qui portait le défaut.** La qualification est « gérée ailleurs » : elle n'ouvrait
    // aucun formulaire, et ses réglages traînaient à plat dans la barre d'actions. Elle était donc
    // le seul type impossible à nommer — précisément celui dont le CA dit qu'on peut en avoir
    // plusieurs.
    monter([QUALIFICATION])
    await ouvrirLaFiche()

    expect(ligne().getByLabelText(/Titre de la phase/)).toBeInTheDocument()
    expect(ligne().getByText(/Barrage jusqu.au rang/)).toBeInTheDocument()
  })

  it('n’ouvre que la fiche cliquée, pas celles des voisines', async () => {
    // Sans quoi « déplier une fiche » redeviendrait « déplier le mur », le refus d'origine.
    monter([
      { ...TABLEAU, id: 1, ordre: 1 },
      { ...TABLEAU, id: 2, ordre: 2 },
    ])
    await ouvrirLaFiche(0)

    expect(ligne(0).getByLabelText(/Titre de la phase/)).toBeInTheDocument()
    expect(ligne(1).queryByLabelText(/Titre de la phase/)).not.toBeInTheDocument()
  })
})

describe('la charge utile envoyée au serveur', () => {
  // ⚠️ **Ces trois tests manquaient à la première livraison, et trois axes de revue l'ont relevé.**
  // `configInchangee` a été extraite avec, en argument, « `titre` en aurait été le TROISIÈME bug :
  // sans cette fonction, régler un barrage renommait la phase en silence » — et rien ne l'exerçait.
  // Toutes les fixtures portaient `titre: null`, donc la borne n'était jamais atteinte : une
  // régression qui perdrait le titre serait restée verte des deux côtés.
  //
  // Le `PUT` est une édition **totale** : ce qui n'est pas réémis est effacé. C'est exactement la
  // classe de bug que ce fichier a déjà payée deux fois (le barrage effaçait le découpage ; le
  // couple découpage/arrêts partait en 422).

  const QUALIFICATION_REGLEE: EtapeDeroule = {
    ...QUALIFICATION,
    titre: 'Qualification jeunes',
    decoupage: { nb_tours: 2 },
    barrage_jusqu_au: 8,
  }

  it('renommer une phase n’efface ni son découpage ni son barrage', async () => {
    monter([QUALIFICATION_REGLEE])
    await ouvrirLaFiche()

    const champ = ligne().getByLabelText(/Titre de la phase/)
    await userEvent.clear(champ)
    await userEvent.type(champ, 'Qualification adultes')
    await userEvent.click(ligne().getAllByRole('button', { name: 'Enregistrer' })[0]!)

    expect(configEnvoyee().titre).toBe('Qualification adultes')
    expect(configEnvoyee().decoupage).toEqual({ nb_tours: 2 })
    expect(configEnvoyee().barrage_jusqu_au).toBe(8)
  })

  it('vider le champ retire le titre, ce qui est le seul geste pour y revenir', async () => {
    monter([QUALIFICATION_REGLEE])
    await ouvrirLaFiche()

    await userEvent.clear(ligne().getByLabelText(/Titre de la phase/))
    await userEvent.click(ligne().getAllByRole('button', { name: 'Enregistrer' })[0]!)

    expect(configEnvoyee().titre).toBeNull()
  })

  it('régler le barrage ne renomme pas la phase — la 3ᵉ occurrence annoncée', async () => {
    // Le sens inverse du premier test, et c'est celui que la docstring de `configInchangee`
    // désigne nommément : un widget à champ unique qui oublierait de réémettre le titre
    // l'effacerait, avec un `PUT` qui réussit et aucun message.
    monter([QUALIFICATION_REGLEE])
    await ouvrirLaFiche()

    const rang = ligne().getByLabelText(/Barrage jusqu.au rang/)
    await userEvent.clear(rang)
    await userEvent.type(rang, '4')
    await userEvent.click(ligne().getAllByRole('button', { name: 'Enregistrer' })[1]!)

    expect(configEnvoyee().barrage_jusqu_au).toBe(4)
    expect(configEnvoyee().titre).toBe('Qualification jeunes')
    expect(configEnvoyee().decoupage).toEqual({ nb_tours: 2 })
  })
})
