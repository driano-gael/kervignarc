// Écran « Sauvegardes » (E11US006, ADR-0119) : lister, vérifier, restaurer à chaud. Les règles —
// intégrité, version, copie de sécurité, sessions fermées — sont au serveur ; l'écran les dit.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { BoutonConfirme } from '../../shared/ui/BoutonConfirme'
import type { NatureSauvegarde, Restauration, Sauvegarde, VerdictSauvegarde } from './api'
import { datePrise, taille } from './presentation'
import { useRestaurerSauvegarde, useSauvegardes, useVerifierSauvegarde } from './hooks'

const NATURES: Record<NatureSauvegarde, string> = {
  periodique: 'Automatique',
  avant_restauration: 'Copie avant restauration',
}

const VERDICTS: Record<VerdictSauvegarde, string> = {
  restaurable: 'Intègre — peut être restaurée',
  corrompue: 'Abîmée — ne peut pas être restaurée',
  version_differente: 'D’une autre version de l’application — ne peut pas être restaurée ici',
}

export function Sauvegardes() {
  const sauvegardes = useSauvegardes()
  const restaurer = useRestaurerSauvegarde()
  const [derniere, setDerniere] = useState<{ restauration: Restauration; date: string } | null>(
    null,
  )

  const lancer = (sauvegarde: Sauvegarde) => {
    setDerniere(null)
    restaurer.mutate(sauvegarde.nom, {
      onSuccess: (restauration) => setDerniere({ restauration, date: datePrise(sauvegarde) }),
    })
  }

  return (
    <section className="carte">
      <h2 className="carte__entete">Sauvegardes</h2>
      <p className="carte__etat">
        Une copie de la base est prise automatiquement pendant que le serveur tourne. Restaurer
        remet <strong>tous les tournois</strong> dans l’état de la copie choisie ; l’état actuel est
        d’abord mis de côté, et se restaure à son tour pour annuler.
      </p>
      {derniere !== null && (
        <p className="carte__etat carte__etat--ok" role="status">
          Base restaurée à l’état du {derniere.date}. L’état précédent est conservé sous «{' '}
          {derniere.restauration.copie_de_securite} ». Les tablettes de cible et les scoreurs
          doivent se reconnecter.
        </p>
      )}
      <MessageErreur erreur={restaurer.error} />
      <MessageErreur erreur={sauvegardes.error} />
      {sauvegardes.data?.length === 0 && (
        <p className="carte__etat">
          Aucune sauvegarde pour l’instant : la première est prise après quelques minutes de
          fonctionnement.
        </p>
      )}
      {sauvegardes.data !== undefined && sauvegardes.data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Prise le</th>
              <th scope="col">Nature</th>
              <th scope="col">Taille</th>
              <th scope="col">Vérification</th>
              <th scope="col">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {sauvegardes.data.map((sauvegarde) => (
              <LigneSauvegarde
                key={sauvegarde.nom}
                sauvegarde={sauvegarde}
                restaurationEnCours={restaurer.isPending}
                onRestaurer={() => lancer(sauvegarde)}
              />
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

function LigneSauvegarde({
  sauvegarde,
  restaurationEnCours,
  onRestaurer,
}: {
  sauvegarde: Sauvegarde
  restaurationEnCours: boolean
  onRestaurer: () => void
}) {
  const verifier = useVerifierSauvegarde()
  const date = datePrise(sauvegarde)

  return (
    <tr>
      <td>{date}</td>
      <td>{NATURES[sauvegarde.nature]}</td>
      <td>{taille(sauvegarde.taille_octets)}</td>
      <td>
        {verifier.data !== undefined ? (
          <span role="status">{VERDICTS[verifier.data.verdict]}</span>
        ) : (
          <button
            type="button"
            className="bouton--discret"
            aria-label={`Vérifier la sauvegarde du ${date}`}
            disabled={verifier.isPending}
            onClick={() => verifier.mutate(sauvegarde.nom)}
          >
            Vérifier
          </button>
        )}
        <MessageErreur erreur={verifier.error} />
      </td>
      <td>
        <BoutonConfirme
          libelle="Restaurer…"
          libelleConfirmer="Restaurer"
          titre={`Restaurer la sauvegarde du ${date} ?`}
          message="Tous les tournois reviennent à l’état de cette sauvegarde. Ce qui a été saisi depuis disparaît de la base."
          detail="L’état actuel est d’abord copié et pourra être restauré. Les tablettes et les scoreurs devront se reconnecter."
          ton="danger"
          className="bouton--danger"
          disabled={restaurationEnCours}
          enCours={restaurationEnCours}
          onConfirmer={onRestaurer}
        />
      </td>
    </tr>
  )
}
