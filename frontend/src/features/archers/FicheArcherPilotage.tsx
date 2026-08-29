// La fiche d'un archer **pendant** le tournoi (E16US010) — consultation, puis action.
//
// CA : « dans le cycle déroulé du tournoi, on peut faire une recherche d'un archer du tournoi et
// ouvrir sa fiche en consultation avec ses informations du tournoi, puis possibilité d'agir dessus
// si besoin ». C'est le pendant *pilotage* de l'édition de la liste des inscrits : ici on **lit**
// d'abord, on agit ensuite — l'inverse de la destination « Inscriptions », qui ouvre un formulaire.
//
// L'archer ouvert vient de l'adresse (ADR-0100), donc d'un résultat de recherche comme d'un lien.

import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useBlasons } from '../blasons/hooks'
import { useCategories } from '../categories/hooks'
import { useClubs } from '../clubs/hooks'
import { PlaceDeLArcher } from '../placement/PlaceDeLArcher'
import { useArchers } from './hooks'

export function FicheArcherPilotage({
  tournoiId,
  archerId,
  onCorrigerLaFiche,
  onModifierLePlacement,
}: {
  tournoiId: number
  archerId: number | null
  onCorrigerLaFiche: (id: number) => void
  onModifierLePlacement: () => void
}) {
  const archers = useArchers(tournoiId)
  const clubs = useClubs()
  const categories = useCategories(tournoiId)
  const blasons = useBlasons(tournoiId)

  if (archerId === null) {
    return (
      <section>
        <h3 className="carte__soustitre">Fiche d’un archer</h3>
        {/* Une destination qui s'ouvre vide doit dire **par où on y entre**, sinon elle se lit
            comme un écran cassé. */}
        <p className="carte__etat">
          Cherchez un archer dans la barre de recherche, en haut à gauche : sa fiche s’ouvre ici.
        </p>
      </section>
    )
  }

  const archer = archers.data?.find((a) => a.id === archerId)
  const categorie = categories.data?.find((c) => c.id === archer?.categorie_id)
  const club = clubs.data?.find((c) => c.id === archer?.club_id)
  const blason =
    categorie?.blason_id != null
      ? blasons.data?.find((b) => b.id === categorie.blason_id)
      : undefined

  return (
    <section>
      <h3 className="carte__soustitre">Fiche d’un archer</h3>
      {archers.isError && <MessageErreur erreur={archers.error} />}
      {/* `isSuccess` et non `data === undefined` : tant que la requête court, l'archer est
          introuvable pour une raison qui n'est pas la bonne. */}
      {archers.isSuccess && archer === undefined && (
        <p className="carte__etat">
          Cet archer n’est pas inscrit à ce tournoi. Il appartient peut-être à une autre édition.
        </p>
      )}
      {archer !== undefined && (
        <>
          <p className="archer__identite">
            {archer.nom} {archer.prenom}
          </p>
          <p className="archer__details">
            {categorie?.libelle ?? '—'}
            {blason !== undefined && ` · ${blason.nom}`}
            {club !== undefined && ` · ${club.nom}`}
            {archer.club_id === null && ' · club inconnu'}
            {archer.handicap !== 0 && ` · handicap ${archer.handicap}`}
          </p>

          <h4 className="carte__soustitre">Où il tire</h4>
          <PlaceDeLArcher archerId={archer.id} tournoiId={tournoiId} />

          <h4 className="carte__soustitre">Agir</h4>
          <span className="archer__actions">
            <button
              type="button"
              className="bouton--discret"
              onClick={() => onCorrigerLaFiche(archer.id)}
            >
              Corriger sa fiche
            </button>
            <button type="button" className="bouton--discret" onClick={onModifierLePlacement}>
              Modifier son placement
            </button>
          </span>
          {/* ⚠️ **Pas de bouton « Déclarer un forfait », et ce n'est pas un oubli** : la route de
              qualification est réservée au scoreur (`exiger_scoreur`), `E16US008` n'ayant élargi
              que celle des duels. Un bouton partirait en 401.
              ⚠️ **Ce paragraphe énonce une frontière de RÔLES** : son élargissement à l'organisateur
              est en arbitrage — `stories/E16-retours-maquettes.md` § E16US010. Le jour où il est
              tranché, cette phrase devient fausse à l'écran. */}
          <p className="carte__etat">
            Un abandon se déclare depuis l’espace scoreur : en qualification, cette écriture lui est
            réservée. En duel, le feu vert permet à l’organisateur de le faire lui-même.
          </p>
        </>
      )}
    </section>
  )
}
