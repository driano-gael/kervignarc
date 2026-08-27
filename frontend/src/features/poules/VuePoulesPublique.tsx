// La vue **publique** d'une phase de poules (E05US031, ADR-0089).
//
// Un seul composant pour **deux** surfaces, comme `VueTableaux` : l'appli publique et l'écran de
// salle (`interactif=false`). ⚠️ **« Trois surfaces » jusqu'à la revue** : la formule recopiée
// ajoutait l'écran d'organisation, qui ne monte pas cette vue — or c'est cette liste qui
// **justifie** « cette vue ne lit pas le store, elle reçoit `mode` et `suivis` en props ».
// **L'historique est ici gratuit** : une poule est un round-robin, ses tours tiennent à l'écran, on
// les affiche donc tous — pas de navigation par tour comme le suisse en réclame une.

import { LigneRencontre } from '../../shared/duels/LigneRencontre'
import { decrirePlaces } from '../../shared/salle/place'
import { participants } from '../../shared/duels/rencontre'
import { messageDeLecture } from '../../shared/api/etatDeLecture'
import { type ModeAffichage } from '../../shared/suivis/focus'
import type { PoulePublique, RencontrePublique } from './api'
import { useEtatPoules } from './hooks'

export function VuePoulesPublique({
  tournoiId,
  phaseId,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  phaseId: number
  /** La bascule « mes archers / tout » de l'appli publique (ADR-0079). */
  mode?: ModeAffichage
  /** Les archers suivis **sur ce tournoi**, descendus par l'appelant — jamais lus au store ici.
   *
   * Même règle que `VueTableaux`, et pour la même raison : cette vue sert aussi l'écran de salle,
   * qui n'a que faire d'un store public et ne doit pas s'y abonner. */
  suivis?: number[]
}) {
  const etat = useEtatPoules(tournoiId, phaseId)
  const donnees = etat.data

  // Les **données priment sur l'erreur** : React Query garde le `data` de la dernière lecture
  // réussie pendant un échec. Tester `isError` d'abord jetterait une poule encore exacte au premier
  // clignotement réseau et laisserait l'écran projeté sur un message d'erreur ≥ 20 s.
  if (donnees === undefined) {
    return <p className="carte__etat">{messageDeLecture(etat)}</p>
  }
  if (donnees.poules.length === 0) {
    return <p className="carte__etat">Les poules ne sont pas encore composées.</p>
  }

  const retenues =
    mode === 'suivis' ? donnees.poules.filter((p) => concerne(p, suivis)) : donnees.poules
  if (retenues.length === 0) {
    // ⚠️ **Aucun de vos archers ici ≠ aucune poule** — la règle « chaque écran nomme son propre
    // vide » (ADR-0079). Le cas est banal : on suit des archers d'une catégorie, la phase affichée
    // est celle d'une autre.
    return (
      <p className="carte__etat">
        Aucun des archers que vous suivez n’est engagé dans ces poules. Passez à « Tout le tournoi »
        pour les voir toutes.
      </p>
    )
  }

  return (
    <div className="encours">
      {/* Une poule qu'aucun bloc ne porte : le plan n'est pas posé, ou la salle est trop petite.
          On le **dit**, sinon la poule s'affiche sans cible et le spectateur croit à un oubli. */}
      {donnees.conflits.length > 0 && (
        <p className="carte__etat">
          {donnees.conflits.length === 1
            ? 'Une poule n’a pas encore de cibles attribuées.'
            : `${donnees.conflits.length} poules n’ont pas encore de cibles attribuées.`}
        </p>
      )}
      {retenues.map((poule) => (
        <BlocPoule key={poule.numero} poule={poule} suivis={suivis} />
      ))}
    </div>
  )
}

/** Un archer suivi tire-t-il dans cette poule ? Lu sur les **membres**, pas sur les rencontres :
 * une poule composée mais pas encore appariée n'a aucune rencontre, et la filtrer alors ferait
 * disparaître de l'écran l'archer qu'on suit précisément parce qu'il va y tirer. */
function concerne(poule: PoulePublique, suivis: readonly number[]): boolean {
  return poule.membres.some((membre) => suivis.includes(membre.archer_id))
}

function BlocPoule({ poule, suivis }: { poule: PoulePublique; suivis: readonly number[] }) {
  const places = poule.bloc === null ? null : decrirePlaces(poule.bloc)
  return (
    <section className="encours__bloc">
      <h4 className="encours__titre">
        Poule {poule.numero}
        {places !== null && <span className="encours__places"> · {places}</span>}
      </h4>

      {poule.rencontres.length === 0 ? (
        <p className="carte__etat">Poule composée — les rencontres ne sont pas encore appariées.</p>
      ) : (
        parTour(poule.rencontres).map(({ tour, rencontres }) => (
          <div key={tour} className="encours__tour">
            <h5 className="encours__tour-titre">Tour {tour}</h5>
            <ul className="encours__lignes">
              {rencontres.map((r) => (
                <LigneRencontre
                  key={r.numero}
                  rencontre={r}
                  places={r.couloirs === null ? null : decrirePlaces(r.couloirs)}
                  souligne={participants(r).some((id) => suivis.includes(id))}
                />
              ))}
            </ul>
          </div>
        ))
      )}

      {poule.classement.length > 0 && (
        <table className="deroule__table">
          <caption>Classement de la poule</caption>
          <thead>
            <tr>
              <th>Rang</th>
              <th>Archer</th>
              <th>Points</th>
            </tr>
          </thead>
          <tbody>
            {poule.classement.map((ligne) => (
              <tr key={ligne.archer_id}>
                <td>
                  {ligne.rang}
                  {ligne.ex_aequo ? ' =' : ''}
                </td>
                <td>{nomDansLaPoule(poule, ligne.archer_id)}</td>
                <td>{ligne.points_match}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Le barrage se **tire** au panneau de barrages (E06US003) ; ici on annonce seulement qu'il
          est dû, sinon le classement paraît figé sur une égalité que rien n'explique. */}
      {poule.barrage_requis && (
        <p className="carte__etat">Un barrage est nécessaire pour départager cette poule.</p>
      )}
    </section>
  )
}

/** Les rencontres groupées par tour, dans l'ordre — l'historique complet du round-robin. */
function parTour(
  rencontres: readonly RencontrePublique[],
): { tour: number; rencontres: RencontrePublique[] }[] {
  const parNumero = new Map<number, RencontrePublique[]>()
  for (const rencontre of rencontres) {
    parNumero.set(rencontre.tour, [...(parNumero.get(rencontre.tour) ?? []), rencontre])
  }
  return [...parNumero.entries()]
    .sort(([a], [b]) => a - b)
    .map(([tour, groupe]) => ({ tour, rencontres: groupe }))
}

/** Le nom d'un archer, retrouvé dans les **membres** de la poule — `#id` si personne ne le porte.
 *
 * Lu sur les membres et non sur les rencontres : le classement existe dès la composition, avant
 * qu'aucune rencontre ne soit appariée. Le repli reste pour ne pas rendre `undefined` à l'écran. */
function nomDansLaPoule(poule: PoulePublique, archerId: number): string {
  const qui = poule.membres.find((membre) => membre.archer_id === archerId)
  return qui === undefined ? `#${archerId}` : `${qui.prenom} ${qui.nom}`.trim()
}
