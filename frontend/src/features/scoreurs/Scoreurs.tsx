// Définition des scoreurs d'un tournoi (E10US003) — réservé à l'admin (monté sous `estAdmin`).
//
// Liste (nom + **code**) + création (le nom seul ; le serveur génère le code) + renommage (code
// figé) + suppression : un module de **préparation** (P-6), redéfinissable tournoi en cours. Le
// code est le sésame que le scoreur retape pour ouvrir sa session. Supprimer un scoreur **invalide
// sa session** côté serveur, mais la trace de ses validations passées est conservée (E10US005).
// Code affiché en clair : secret d'usage, pas mot de passe — imprimé et remis en main propre.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Scoreur } from './api'
import { QrScoreur } from './QrScoreur'
import {
  useCreerScoreur,
  useModifierScoreur,
  useScoreurs,
  useSupprimerScoreur,
  useTelechargerCartesScoreurs,
} from './hooks'

export function Scoreurs({ tournoiId }: { tournoiId: number }) {
  const scoreurs = useScoreurs(tournoiId)
  const cartes = useTelechargerCartesScoreurs(tournoiId)
  // Un seul QR ouvert à la fois : porté par le **parent**, pas par un booléen dans chaque ligne —
  // l'exclusivité devient structurelle au lieu de dépendre d'un `useEffect` de synchronisation.
  // ⚠️ Indexé sur le **code** et non sur l'`id` : SQLite réattribue les `id` (PK sans
  // AUTOINCREMENT), donc supprimer un scoreur dont le QR est ouvert puis en créer un autre
  // rouvrait le QR **sans clic** sur le nouveau venu. Le code, lui, est unique dans toute la base
  // unique parmi les scoreurs vivants (`UNIQUE(code)`, ADR-0025 § Décision 2). Bloquant de revue.
  const [qrOuvert, setQrOuvert] = useState<string | null>(null)

  return (
    <section>
      <h3 className="carte__soustitre">Scoreurs</h3>
      <p className="carte__etat">
        Déclarez les 3 à 4 personnes qui valideront les scores. Chacune reçoit un code à retaper
        dans « Espace scoreur » pour ouvrir sa session.
      </p>
      <FormulaireScoreur tournoiId={tournoiId} />
      {scoreurs.isError && <MessageErreur erreur={scoreurs.error} />}
      {scoreurs.data && scoreurs.data.length === 0 && (
        <p className="carte__etat">Aucun scoreur déclaré pour ce tournoi.</p>
      )}
      {scoreurs.data && scoreurs.data.length > 0 && (
        <>
          <ul className="liste-scoreurs">
            {scoreurs.data.map((scoreur) => (
              <LigneScoreur
                key={scoreur.code}
                tournoiId={tournoiId}
                scoreur={scoreur}
                qrOuvert={qrOuvert === scoreur.code}
                ouvrirQr={(ouvrir) => setQrOuvert(ouvrir ? scoreur.code : null)}
              />
            ))}
          </ul>
          {/* **Imprimer toutes les cartes** (A08 : *« garde quand meme la possibilite de pouvoir
              tous les imprimer »*). Comme les etiquettes de cible, la route existait cote serveur
              depuis E09US008 sans qu'aucun ecran ne l'atteigne. */}
          <button
            type="button"
            className="bouton--discret"
            disabled={cartes.isPending}
            onClick={() => cartes.mutate()}
          >
            {cartes.isPending ? 'Generation...' : 'Imprimer toutes les cartes (PDF)'}
          </button>
          <MessageErreur erreur={cartes.error} />
        </>
      )}
    </section>
  )
}

function LigneScoreur({
  tournoiId,
  scoreur,
  qrOuvert,
  ouvrirQr,
}: {
  tournoiId: number
  scoreur: Scoreur
  qrOuvert: boolean
  ouvrirQr: (ouvrir: boolean) => void
}) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerScoreur(tournoiId)

  if (edition) {
    return (
      <li>
        <FormulaireScoreur
          tournoiId={tournoiId}
          scoreur={scoreur}
          onTermine={() => setEdition(false)}
        />
      </li>
    )
  }

  return (
    <li className="scoreur">
      <div className="scoreur__ligne">
        <span className="scoreur__nom">{scoreur.nom}</span>
        {/* Code en évidence, en chiffres/lettres lisibles : c'est ce qu'on recopie sur le papier. */}
        <code className="scoreur__code">{scoreur.code}</code>
        <span className="scoreur__actions">
          {/* ⚠️ Révélation **une par une** (arbitrage E16US015) : le QR rend le code personnel
              scannable à distance, là où le code écrit demande de s'approcher. */}
          {/* ⚠️ Le libellé visible tient sur la ligne, mais le **nom accessible** nomme le
              scoreur — sur TOUS les boutons de la ligne, y compris les destructeurs : dix
              « Supprimer » identiques au lecteur d'écran, sur une action qui coupe une session. */}
          <button
            type="button"
            className="bouton--discret"
            aria-expanded={qrOuvert}
            aria-label={`${qrOuvert ? 'Masquer' : 'Afficher'} le QR de ${scoreur.nom}`}
            onClick={() => ouvrirQr(!qrOuvert)}
          >
            {qrOuvert ? 'Masquer le QR' : 'Afficher le QR'}
          </button>
          <button
            type="button"
            className="bouton--discret"
            aria-label={`Renommer ${scoreur.nom}`}
            onClick={() => setEdition(true)}
          >
            Renommer
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                aria-label={`Confirmer la suppression de ${scoreur.nom}`}
                onClick={() => supprimer.mutate(scoreur.id)}
              >
                Confirmer la suppression
              </button>
              <button
                type="button"
                className="bouton--discret"
                aria-label={`Annuler la suppression de ${scoreur.nom}`}
                onClick={() => setConfirmationSuppression(false)}
              >
                Annuler
              </button>
            </>
          ) : (
            <button
              type="button"
              className="bouton--danger"
              aria-label={`Supprimer ${scoreur.nom}`}
              onClick={() => setConfirmationSuppression(true)}
            >
              Supprimer
            </button>
          )}
        </span>
      </div>
      {qrOuvert && (
        <div className="scoreur__qr">
          <QrScoreur
            tournoiId={tournoiId}
            scoreurId={scoreur.id}
            code={scoreur.code}
            nom={scoreur.nom}
          />
          <p className="carte__etat">
            À scanner par {scoreur.nom} : ouvre sa session sans retaper le code.
          </p>
        </div>
      )}
      {confirmationSuppression && (
        <p className="carte__etat">
          Sa session en cours sera coupée ; ses validations passées restent tracées.
        </p>
      )}
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

// Formulaire partagé création / renommage : sans `scoreur` il crée (le serveur génère le code),
// avec il renomme (le code est figé, hors du formulaire).
function FormulaireScoreur({
  tournoiId,
  scoreur,
  onTermine,
}: {
  tournoiId: number
  scoreur?: Scoreur
  onTermine?: () => void
}) {
  const enEdition = scoreur !== undefined
  const [nom, setNom] = useState(scoreur?.nom ?? '')

  const creer = useCreerScoreur(tournoiId)
  const modifier = useModifierScoreur(tournoiId)
  const mutation = enEdition ? modifier : creer

  // Reprend la règle du domaine (nom non vide) pour éviter une requête vouée au 422 ; le serveur
  // reste l'autorité (revalidation à la frontière).
  const entreeValide = nom.trim() !== ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!entreeValide) return
    if (enEdition) {
      modifier.mutate({ scoreurId: scoreur.id, entree: { nom } }, { onSuccess: onTermine })
    } else {
      // Création : on réinitialise le champ pour enchaîner une autre déclaration.
      creer.mutate({ nom }, { onSuccess: () => setNom('') })
    }
  }

  return (
    <div>
      {enEdition && <h4 className="carte__soustitre">Renommer le scoreur</h4>}
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom du scoreur"
          aria-label="Nom du scoreur"
        />
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || !entreeValide}>
            {enEdition ? 'Enregistrer' : 'Ajouter le scoreur'}
          </button>
          {enEdition && (
            <button type="button" className="bouton--discret" onClick={onTermine}>
              Annuler
            </button>
          )}
        </div>
      </form>
      <MessageErreur erreur={mutation.error} />
    </div>
  )
}
