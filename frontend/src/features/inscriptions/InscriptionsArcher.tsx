// Panneau d'inscription d'un archer sur les départs (créneaux) d'un tournoi (E02US009, ADR-0017).
//
// Inscrire l'archer sur un créneau encore libre, marquer une inscription payée / non payée, le
// désinscrire. Le **montant dû** de chaque inscription est dérivé du tarif du créneau (affiché tel
// quel, ADR-0017) ; la facturation (somme par archer) est E08US001. Rendu sous l'écran des archers,
// donc déjà réservé à l'admin.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { decrireTarif } from '../competition/format'
import { useDeparts } from '../departs/hooks'
import type { Inscription } from './api'
import { useDesinscrire, useInscrire, useInscriptions, useMarquerPaye } from './hooks'

export function InscriptionsArcher({
  archerId,
  tournoiId,
}: {
  archerId: number
  tournoiId: number
}) {
  const inscriptions = useInscriptions(archerId)
  const departs = useDeparts(tournoiId)

  // Créneaux encore proposables : ceux du tournoi sur lesquels l'archer n'est pas déjà inscrit.
  // Le serveur reste l'autorité (il refuse un doublon par `deja_inscrit`) ; ce filtre n'est
  // qu'une commodité d'écran, pour ne pas proposer un créneau déjà pris.
  const dejaInscrit = new Set((inscriptions.data ?? []).map((i) => i.depart_id))
  const disponibles = (departs.data ?? []).filter((depart) => !dejaInscrit.has(depart.id))

  return (
    <div className="inscriptions">
      <h5 className="carte__soustitre">Départs de l'archer</h5>
      {inscriptions.isError && <MessageErreur erreur={inscriptions.error} />}
      {inscriptions.isSuccess && inscriptions.data.length === 0 && (
        <p className="carte__etat">Aucune inscription pour l'instant.</p>
      )}
      {inscriptions.data && inscriptions.data.length > 0 && (
        <ul className="liste-inscriptions">
          {inscriptions.data.map((inscription) => (
            <LigneInscription key={inscription.id} archerId={archerId} inscription={inscription} />
          ))}
        </ul>
      )}
      {departs.isError && <MessageErreur erreur={departs.error} />}
      {/* Le formulaire ne s'affiche qu'une fois les départs **chargés** : sans ce garde, un échec de
          chargement (`disponibles` alors vide, mais `isSuccess` faux) tomberait sur « tous inscrits »
          — un état faux (les créneaux n'ont pas pu être lus, ils ne sont pas « tous pris »). */}
      {departs.isSuccess && (
        <FormulaireInscription
          archerId={archerId}
          disponibles={disponibles.map((depart) => ({
            id: depart.id,
            libelle: libelleDepart(depart.numero, depart.horaire, depart.tarif_centimes),
          }))}
          aucunDepart={departs.data.length === 0}
        />
      )}
    </div>
  )
}

function LigneInscription({
  archerId,
  inscription,
}: {
  archerId: number
  inscription: Inscription
}) {
  const marquer = useMarquerPaye(archerId)
  const desinscrire = useDesinscrire(archerId)

  return (
    <li className="inscription">
      <span className="inscription__creneau">
        {libelleDepart(
          inscription.numero_depart,
          inscription.horaire,
          inscription.montant_du_centimes,
        )}
      </span>
      <span className="inscription__statut">{inscription.paye ? 'Payé' : 'Non payé'}</span>
      <span className="inscription__actions">
        <button
          type="button"
          className="bouton--discret"
          disabled={marquer.isPending}
          onClick={() => marquer.mutate({ inscriptionId: inscription.id, paye: !inscription.paye })}
        >
          {inscription.paye ? 'Marquer non payé' : 'Marquer payé'}
        </button>
        <button
          type="button"
          className="bouton--danger"
          disabled={desinscrire.isPending}
          onClick={() => desinscrire.mutate(inscription.id)}
        >
          Désinscrire
        </button>
      </span>
      <MessageErreur erreur={marquer.error ?? desinscrire.error} />
    </li>
  )
}

function FormulaireInscription({
  archerId,
  disponibles,
  aucunDepart,
}: {
  archerId: number
  disponibles: { id: number; libelle: string }[]
  aucunDepart: boolean
}) {
  const [departId, setDepartId] = useState('')
  const inscrire = useInscrire(archerId)

  if (aucunDepart) {
    return (
      <p className="carte__etat">
        Aucun créneau n'est configuré pour ce tournoi — définissez les départs d'abord.
      </p>
    )
  }
  if (disponibles.length === 0) {
    return <p className="carte__etat">L'archer est inscrit sur tous les créneaux disponibles.</p>
  }

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (departId === '') return
    inscrire.mutate(Number(departId), { onSuccess: () => setDepartId('') })
  }

  return (
    <form className="formulaire" onSubmit={soumettre}>
      <select
        className="formulaire__champ"
        value={departId}
        onChange={(e) => setDepartId(e.target.value)}
        aria-label="Départ (créneau) à ajouter"
      >
        <option value="">Choisir un créneau…</option>
        {disponibles.map((depart) => (
          <option key={depart.id} value={depart.id}>
            {depart.libelle}
          </option>
        ))}
      </select>
      <button type="submit" disabled={inscrire.isPending || departId === ''}>
        Inscrire sur ce créneau
      </button>
      <MessageErreur erreur={inscrire.error} />
    </form>
  )
}

// Libellé d'un créneau : « Départ N · horaire · tarif ». `montantOuTarif` est soit le tarif du
// départ (au choix), soit le montant dû dérivé d'une inscription — les deux sont égaux (ADR-0017).
function libelleDepart(numero: number, horaire: string | null, montantOuTarif: number): string {
  const quand = horaire ?? 'horaire non précisé'
  return `Départ ${numero} · ${quand} · ${decrireTarif(montantOuTarif)}`
}
