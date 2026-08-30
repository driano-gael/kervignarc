// La fiche d'un archer **pendant** le tournoi (E16US010) — consultation, puis action.
//
// CA : « dans le cycle déroulé du tournoi, on peut faire une recherche d'un archer du tournoi et
// ouvrir sa fiche en consultation avec ses informations du tournoi, puis possibilité d'agir dessus
// si besoin ». C'est le pendant *pilotage* de l'édition de la liste des inscrits : ici on **lit**
// d'abord, on agit ensuite — l'inverse de la destination « Inscriptions », qui ouvre un formulaire.
//
// L'archer ouvert vient de l'adresse (ADR-0100), donc d'un résultat de recherche comme d'un lien.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useBlasons } from '../blasons/hooks'
import { useCategories } from '../categories/hooks'
import { useClubs } from '../clubs/hooks'
import type { NatureForfait } from '../forfaits/api'
import { useDeclarerForfaitQualif } from '../forfaits/hooks'
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
          <DeclarerForfait tournoiId={tournoiId} archerId={archer.id} />
        </>
      )}
    </section>
  )
}

// Déclaration d'un forfait de **qualification** depuis la fiche, en portée admin (E16US007 —
// arbitrage du commanditaire du 30/08/2026 : la route, réservée au scoreur, s'ouvre à
// l'organisateur ; elle est **élargie, pas doublée**, comme celle des duels en E16US008).
//
// ⚠️ **Déclarer seulement** : l'annulation (`D-15`) reste au panneau de l'espace scoreur, qui
// dispose du classement pour dire *qui* est déjà forfait. La fiche ne le sait pas, et un bouton
// « Annuler » qui ne saurait pas s'il a quelque chose à annuler serait pire que son absence.
function DeclarerForfait({ tournoiId, archerId }: { tournoiId: number; archerId: number }) {
  const [ouvert, setOuvert] = useState(false)
  const [nature, setNature] = useState<NatureForfait>('abandon')
  const [motif, setMotif] = useState('')
  const declarer = useDeclarerForfaitQualif(tournoiId, 'admin')

  if (declarer.isSuccess) {
    return (
      <p className="carte__etat">
        Forfait enregistré. Ses flèches déjà tirées sont conservées ; l’annulation se fait depuis
        l’espace scoreur, panneau « Forfaits — qualification ».
      </p>
    )
  }

  if (!ouvert) {
    return (
      <span className="archer__actions">
        <button type="button" className="bouton--discret" onClick={() => setOuvert(true)}>
          Déclarer un forfait
        </button>
      </span>
    )
  }

  return (
    <div className="formulaire formulaire--colonne">
      <label className="formulaire__libelle">
        Nature
        <select
          className="formulaire__champ"
          value={nature}
          onChange={(e) => setNature(e.target.value as NatureForfait)}
        >
          <option value="abandon">Abandon (relégué en fin de classement)</option>
          <option value="disqualification">Disqualification (sorti du classement)</option>
        </select>
      </label>
      <label className="formulaire__libelle">
        Motif (facultatif)
        <input
          className="formulaire__champ"
          value={motif}
          onChange={(e) => setMotif(e.target.value)}
        />
      </label>
      <div className="formulaire__actions">
        <button
          type="button"
          disabled={declarer.isPending}
          onClick={() => declarer.mutate({ archerId, nature, motif: motif.trim() || undefined })}
        >
          {declarer.isPending ? 'Enregistrement…' : 'Confirmer le forfait'}
        </button>
        <button type="button" className="bouton--discret" onClick={() => setOuvert(false)}>
          Annuler
        </button>
      </div>
      <MessageErreur erreur={declarer.error} />
    </div>
  )
}
