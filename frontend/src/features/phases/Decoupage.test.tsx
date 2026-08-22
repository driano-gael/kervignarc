// Le **découpage en tours** d'une qualification, sur l'écran des phases (E05US035, ADR-0093).
//
// ⚠️ **Ce fichier existe parce que la revue a montré qu'aucun test ne pouvait voir le défaut** —
// et c'est la seconde fois dans ce même dossier, après `BorneSuisse.test.tsx`, dont l'entête
// raconte exactement la même histoire.
//
// `decoupage.ts` était pur, testé, parfaitement vert. Pendant ce temps, `ReglageDecoupage` était
// monté dans `FormulairePhase` sous `{estQualification && …}` — une branche **morte** : la
// qualification n'ouvre jamais ce formulaire (`gereeAilleurs`) et n'est pas dans
// `TYPES_AJOUTABLES`. Le réglage central de l'US n'était donc atteignable par **aucun** écran de
// tournoi, et `nb_volees`, ajouté au serveur exprès pour l'alimenter, n'avait aucun lecteur.
//
// Un test de formatage ne voit pas un défaut de câblage ; seul un test qui monte **l'écran** le
// voit. C'est pourquoi celui-ci monte `Phases` en entier, et non le contrôle isolé : ce qu'on
// garde ici n'est pas « le composant sait afficher », c'est « l'organisateur peut l'atteindre ».
//
// ⚠️ **Le GESTE a changé en E16US002, l'INTENTION est intacte.** Les réglages de la qualification
// vivaient à plat dans la barre d'actions ; ils sont désormais dans **sa fiche**, qu'on ouvre
// depuis sa ligne (c'est le CA d'A07 : « sur chaque ligne on peut ouvrir une fiche de la phase »).
// Ces tests ouvrent donc la fiche avant de chercher le réglage. Ce que le garde-fou empêche n'a
// pas bougé d'un pouce : un réglage recâblé sous une condition que la qualification ne satisfait
// jamais ferait échouer le clic sur un écran réellement monté, exactement comme avant. Ce qui
// n'est **plus** garanti, et il faut le dire : le réglage n'est plus visible **sans clic**.

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import type { EtapeDeroule } from './api'
import { getPhases } from './api'
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

const QUALIFICATION: EtapeDeroule = {
  id: 7,
  tournoi_id: 1,
  ordre: 1,
  type: 'qualification',
  sources: [],
  effectif: null,
  barrage_jusqu_au: null,
  profondeur: null,
  poules: null,
  big_shoot_off: null,
  suisse: null,
  colline: null,
  decoupage: null,
  titre: null,
  nb_volees: 20,
  arrets: [],
}

function monter(phase: EtapeDeroule) {
  monterPlusieurs([phase])
}

/** Ouvre la fiche de la première (ou n-ième) phase listée — le geste du CA d'A07.
 *
 * Passe par un vrai clic sur un vrai bouton : c'est ce qui fait que le garde-fou de câblage tient
 * toujours. Un réglage monté sous une condition inatteignable ne s'afficherait pas davantage
 * après ce clic qu'avant.
 */
/** Les requêtes **portées à la ligne de phase**, et non à l'écran entier.
 *
 * ⚠️ **Ce cadrage manquait, et il rendait ces tests plus faibles que leur nom** (constaté en
 * E16US002). L'écran monte en permanence un formulaire **d'ajout** en tête, qui affiche lui aussi
 * « Pauses programmées ». `findByText` résolvant à la **première** correspondance — et le
 * formulaire d'ajout étant rendu avant que React Query n'ait servi la liste —, l'assertion
 * matchait le formulaire d'ajout, pas la fiche de la qualification. Elle serait restée verte avec
 * le réglage de la qualification entièrement décâblé : exactement le défaut que ce fichier existe
 * pour empêcher. Porter la requête à la ligne le referme.
 */
function ligne(index = 0) {
  // Filtré sur `.phase` : `ReglageArrets` rend un `<li>` par pause à l'intérieur d'une fiche, donc
  // indexer tous les `listitem` du document décalerait les rangs dès qu'une fixture porte un arrêt.
  const element = screen.getAllByRole('listitem').filter((el) => el.classList.contains('phase'))[
    index
  ]
  if (element === undefined) throw new Error(`Aucune ligne de phase au rang ${index}.`)
  return within(element)
}

async function ouvrirLaFiche(index = 0) {
  // ⚠️ **Le bouton se cherche DANS sa ligne, pas dans la liste globale.** Une fois une fiche
  // ouverte, son bouton devient « Fermer la fiche » : la liste des « Ouvrir la fiche » se décale,
  // et viser le n-ième élément de cette liste désigne la mauvaise ligne — ou aucune. Un premier
  // jet le faisait, et le clic partait dans le vide sans que l'assertion s'en aperçoive.
  await screen.findAllByRole('listitem')
  await userEvent.click(ligne(index).getByRole('button', { name: 'Ouvrir la fiche' }))
}

function monterPlusieurs(phases: EtapeDeroule[]) {
  vi.mocked(getPhases).mockResolvedValue(phases)
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Enveloppe({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  render(<Phases tournoiId={1} />, { wrapper: Enveloppe })
}

describe('le découpage en tours sur l’écran des phases', () => {
  it('est atteignable sur une qualification, sans passer par un formulaire d’édition', async () => {
    // LE test du bloquant : la qualification est « gérée ailleurs », donc son réglage doit vivre
    // à côté de la carte, comme le barrage — et non dans un formulaire qu'elle n'ouvre jamais.
    monter(QUALIFICATION)
    await ouvrirLaFiche()

    expect(ligne().getByText(/Découpage en tours/)).toBeInTheDocument()
  })

  it('annonce ce que le découpage donne, sur le barème RÉEL du tournoi', async () => {
    // L'autre moitié : `nb_volees` vient du serveur (`EtapeReponse`). S'il n'arrivait pas, l'écran
    // afficherait « la longueur dépend du barème du tournoi qui appliquera ce format » — phrase de
    // l'atelier de bibliothèque, absurde ici — et tout resterait vert.
    monter({ ...QUALIFICATION, decoupage: { nb_tours: 2 } })
    await ouvrirLaFiche()

    expect(ligne().getByText(/2 tours de 10 volées/)).toBeInTheDocument()
  })

  it('nomme le refus à venir quand le découpage ne tombe pas juste', async () => {
    monter({ ...QUALIFICATION, decoupage: { nb_tours: 3 } })
    await ouvrirLaFiche()

    expect(ligne().getByText(/20 volées ne se découpent pas en 3 tours égaux/)).toBeInTheDocument()
  })

  it('porte la fiche de pauses dès que la qualification est découpée', async () => {
    // ⚠️ **Bloquant de 2ᵉ passe** : le premier correctif avait fermé la moitié `decoupage` du trou
    // de câblage et laissé la moitié `arrets` ouverte — `ReglageArrets` n'était monté que dans
    // `FormulairePhase`, que la qualification n'ouvre jamais. On pouvait donc découper la
    // qualification sans pouvoir y poser la pause, c'est-à-dire que l'US restait inerte sur le geste
    // même pour lequel le découpage existe.
    monter({ ...QUALIFICATION, decoupage: { nb_tours: 2 } })
    await ouvrirLaFiche()

    expect(ligne().getByText(/Pauses programmées/)).toBeInTheDocument()
    expect(ligne().queryByText(/Découpez-la d’abord en tours/)).not.toBeInTheDocument()
  })

  it('refuse la pause en nommant le geste, tant que la qualification n’est pas découpée', async () => {
    // Le motif doit être **circonstancié** : dire « ce type de phase n'annonce pas ses tours »
    // serait faux deux fois — le type l'annonce depuis cette US, et la qualification manquerait à
    // l'énumération des types arrêtables. Surtout, le geste réparateur est deux blocs plus haut.
    monter(QUALIFICATION)
    await ouvrirLaFiche()

    expect(ligne().getByText(/Découpez-la d’abord en tours/)).toBeInTheDocument()
  })

  it('n’expose le réglage que sur la qualification, pas sur ses voisines', async () => {
    // ⚠️ Décor à **deux** exemplaires (correctif de 2ᵉ passe) : avec une seule phase, les tests
    // ci-dessus prouvaient « atteignable », pas « atteignable **là et seulement là** » — ils
    // seraient restés verts si le bloc avait été monté sans condition de type.
    monterPlusieurs([
      QUALIFICATION,
      { ...QUALIFICATION, id: 8, ordre: 2, type: 'suisse', nb_volees: null },
    ])
    // Les **deux** fiches sont ouvertes : sinon la longueur de 1 ne prouverait rien de plus que
    // « une seule fiche est ouverte ». C'est la version E16US002 du correctif de 2ᵉ passe rappelé
    // ci-dessus — le décor à deux exemplaires perdrait tout son sens si l'on n'en dépliait qu'un.
    await ouvrirLaFiche(0)
    await ouvrirLaFiche(1)

    expect(screen.getAllByText(/Découpage en tours/)).toHaveLength(1)
  })

  it('dit qu’aucune pause ne peut se poser tant que la qualification n’est pas découpée', async () => {
    // La phrase doit être vraie : c'est le pendant visible du refus serveur. Avant le correctif,
    // l'écran l'affichait tout en offrant, deux blocs plus bas, un formulaire de pause.
    monter(QUALIFICATION)
    await ouvrirLaFiche()

    expect(ligne().getByText(/La qualification se tire d’un seul bloc/)).toBeInTheDocument()
  })
})
