// Panneau d'inscription d'un archer sur les départs (créneaux) d'un tournoi (E02US009, ADR-0017).
//
// Inscrire l'archer sur un créneau encore libre, marquer une inscription payée / non payée, le
// désinscrire. Le **montant dû** de chaque inscription est dérivé du tarif du créneau (affiché tel
// quel, ADR-0017) ; la facturation (somme par archer) est E08US001. Rendu sous l'écran des archers,
// donc déjà réservé à l'admin.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
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
            <LigneInscription
              key={inscription.id}
              archerId={archerId}
              tournoiId={tournoiId}
              inscription={inscription}
            />
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

// `details` du 409 `inscription_payee_a_rembourser` (E08US005) : montant encaissé à rembourser et
// nom de l'archer, chiffrés côté serveur (jamais reconstitués côté client).
interface ARembourser {
  montant_centimes: number
  archer: string
}

// Vrai si l'erreur est le 409 « inscription payée à rembourser » — celui qui ouvre le dialogue de
// confirmation. On le distingue de toute autre erreur (500, 404, réseau) pour ne masquer QUE lui.
function estConfirmable(erreur: unknown): boolean {
  return erreur instanceof ErreurApi && erreur.code === 'inscription_payee_a_rembourser'
}

function LigneInscription({
  archerId,
  tournoiId,
  inscription,
}: {
  archerId: number
  tournoiId: number
  inscription: Inscription
}) {
  const marquer = useMarquerPaye(archerId)
  const desinscrire = useDesinscrire(archerId, tournoiId)
  // Confirmation en attente : renseignée quand le serveur signale une somme à rembourser (409).
  const [aRembourser, setARembourser] = useState<ARembourser | null>(null)

  const demanderDesinscription = () => {
    desinscrire.mutate(
      { inscriptionId: inscription.id, confirme: false },
      {
        onError: (erreur) => {
          // On n'ouvre le dialogue que si le serveur a bien chiffré la somme à rembourser : le cast
          // n'est sûr que gardé par le code **et** la présence de `details` (revue C1). Sinon on
          // laisse l'erreur s'afficher normalement (bandeau ci-dessous).
          if (
            erreur instanceof ErreurApi &&
            erreur.code === 'inscription_payee_a_rembourser' &&
            erreur.details
          ) {
            setARembourser(erreur.details as ARembourser)
          }
        },
      },
    )
  }

  const confirmerDesinscription = () => {
    desinscrire.mutate(
      { inscriptionId: inscription.id, confirme: true },
      { onSuccess: () => setARembourser(null) },
    )
  }

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
          onClick={demanderDesinscription}
        >
          Désinscrire
        </button>
      </span>
      {aRembourser !== null && (
        <div className="inscription__confirmation" role="alertdialog">
          <p>
            {aRembourser.archer} a réglé ce départ : le désinscrire ouvrira un remboursement de{' '}
            {decrireTarif(aRembourser.montant_centimes)}.
          </p>
          <span className="inscription__actions">
            <button
              type="button"
              className="bouton--danger"
              disabled={desinscrire.isPending}
              onClick={confirmerDesinscription}
            >
              Désinscrire et rembourser
            </button>
            <button
              type="button"
              className="bouton--discret"
              disabled={desinscrire.isPending}
              onClick={() => {
                // `reset()` efface l'erreur 409 de la mutation : sans lui, annuler laisserait le
                // message brut du 409 s'afficher dans le bandeau ci-dessous (revue B).
                setARembourser(null)
                desinscrire.reset()
              }}
            >
              Annuler
            </button>
          </span>
          {/* Une erreur du chemin **confirmé** (500, 404…) s'affiche DANS le dialogue : sinon le
              masquage du bandeau l'avalerait et le dialogue resterait muet (revue C1). Le 409
              confirmable lui-même n'est pas ré-affiché (le texte ci-dessus l'explique déjà). */}
          {!estConfirmable(desinscrire.error) && <MessageErreur erreur={desinscrire.error} />}
        </div>
      )}
      <MessageErreur erreur={marquer.error} />
      {/* Bandeau : hors dialogue, on affiche toute erreur de désinscription **sauf** le 409
          confirmable (traité par le dialogue). Pendant le dialogue, le bandeau se tait — l'erreur
          du chemin confirmé est montrée dans le dialogue ci-dessus. */}
      {aRembourser === null && !estConfirmable(desinscrire.error) && (
        <MessageErreur erreur={desinscrire.error} />
      )}
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
