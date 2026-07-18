// Configuration des départs (créneaux) d'un tournoi (E02US004, ADR-0017) — réservée à l'admin
// (montée sous `estAdmin`).
//
// Un départ est un créneau du tournoi (le tournoi rejoué plusieurs fois dans la journée) : il porte
// un **numéro** (attribué par le serveur), un **horaire** facultatif et un **tarif** obligatoire, en
// euros à l'écran mais transmis en **centimes** (ADR-0012). L'inscription d'un archer sur des départs
// est une autre US (E02US009) : ici on ne fait que **définir** les créneaux et leur prix.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import {
  centimesVersSaisieEuros,
  decrireTarif,
  saisieEurosVersCentimes,
} from '../competition/format'
import type { Depart, NouveauDepart } from './api'
import { useCreerDepart, useDeparts, useModifierDepart, useSupprimerDepart } from './hooks'

export function Departs({ tournoiId }: { tournoiId: number }) {
  const departs = useDeparts(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Départs (créneaux)</h3>
      <FormulaireDepart tournoiId={tournoiId} />
      {departs.isError && <MessageErreur erreur={departs.error} />}
      {departs.data && departs.data.length > 0 && (
        <ul className="liste-departs">
          {departs.data.map((depart) => (
            <LigneDepart key={depart.id} tournoiId={tournoiId} depart={depart} />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneDepart({ tournoiId, depart }: { tournoiId: number; depart: Depart }) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerDepart(tournoiId)

  // `depart_avec_inscriptions` (ADR-0018) : un **signalement**, pas un refus — le créneau porte des
  // inscriptions, mais l'admin peut confirmer. Le seul dont la confirmation **détruit** (les
  // inscriptions partent, les payées seront à rembourser — E08US005) : d'où le bouton `--danger` et
  // un libellé qui nomme la perte. Le message du serveur décompte les payées ; c'est lui qu'on lit.
  const inscriptionsSignalees =
    supprimer.error instanceof ErreurApi && supprimer.error.code === 'depart_avec_inscriptions'

  if (edition) {
    return (
      <li>
        <FormulaireDepart
          tournoiId={tournoiId}
          depart={depart}
          onTermine={() => setEdition(false)}
        />
      </li>
    )
  }

  return (
    <li className="depart">
      <div className="depart__ligne">
        <span className="depart__numero">Départ {depart.numero}</span>
        <span className="depart__attributs">{decrire(depart)}</span>
        <span className="depart__actions">
          <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
            Éditer
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate({ departId: depart.id })}
              >
                Confirmer la suppression
              </button>
              <button
                type="button"
                className="bouton--discret"
                onClick={() => {
                  // `reset()` : sans lui, un signalement en cours resterait affiché sur une ligne
                  // où l'admin vient justement de renoncer.
                  supprimer.reset()
                  setConfirmationSuppression(false)
                }}
              >
                Annuler
              </button>
            </>
          ) : (
            <button
              type="button"
              className="bouton--danger"
              onClick={() => setConfirmationSuppression(true)}
            >
              Supprimer
            </button>
          )}
        </span>
      </div>
      {inscriptionsSignalees ? (
        <div className="carte__etat" role="alert">
          <p>{supprimer.error?.message}</p>
          <button
            type="button"
            className="bouton--danger"
            disabled={supprimer.isPending}
            onClick={() =>
              supprimer.mutate({ departId: depart.id, autoriserSuppressionInscrits: true })
            }
          >
            Supprimer quand même, avec les inscriptions
          </button>
        </div>
      ) : (
        <MessageErreur erreur={supprimer.error} />
      )}
    </li>
  )
}

// Décrit un départ pour l'affichage : horaire (si précisé) · tarif · quota (si plafonné).
function decrire(depart: Depart): string {
  const horaire = depart.horaire ?? 'horaire non précisé'
  const base = `${horaire} · ${decrireTarif(depart.tarif_centimes)}`
  return depart.quota === null ? base : `${base} · quota ${depart.quota}`
}

// Analyse la saisie du quota : vide = pas de plafond (null, valide) ; sinon un entier ≥ 1. Une
// saisie non entière ou ≤ 0 renvoie `'invalide'` pour bloquer l'envoi (évite un 422 assuré). On
// n'applique ici que la **borne basse** (≥ 1) et l'intégrité entière ; le **plafond** (1 000,
// `QUOTA_DEPART_MAX`) n'est vérifié que côté serveur — le serveur reste l'autorité, une valeur trop
// grande passe ce pré-contrôle et récolte un 422 affiché (comme le tarif, dont le front n'enforce
// pas non plus le plafond).
function analyserQuota(saisie: string): number | null | 'invalide' {
  const texte = saisie.trim()
  if (texte === '') return null
  if (!/^\d+$/.test(texte)) return 'invalide'
  const valeur = Number(texte)
  return valeur >= 1 ? valeur : 'invalide'
}

// Formulaire partagé création / édition : sans `depart` il crée, avec il édite. Le tarif est
// **obligatoire** (un créneau a toujours un prix — saisir « 0 » pour un créneau gratuit) ; l'horaire
// est facultatif.
function FormulaireDepart({
  tournoiId,
  depart,
  onTermine,
}: {
  tournoiId: number
  depart?: Depart
  onTermine?: () => void
}) {
  const enEdition = depart !== undefined
  const [tarif, setTarif] = useState(depart ? centimesVersSaisieEuros(depart.tarif_centimes) : '')
  const [horaire, setHoraire] = useState(depart?.horaire ?? '')
  // Pré-rempli en édition : le PUT est un **remplacement complet**, un quota laissé vide **retire**
  // le plafond côté serveur. En repartir de la valeur courante évite de l'effacer par mégarde.
  const [quota, setQuota] = useState(depart?.quota != null ? String(depart.quota) : '')

  const creer = useCreerDepart(tournoiId)
  const modifier = useModifierDepart(tournoiId)
  const mutation = enEdition ? modifier : creer

  // Le tarif est requis : un champ vide ou une saisie invalide donne `null`, ce qui bloque l'envoi
  // (évite un 422 assuré) ; le serveur reste l'autorité (revalidation à la frontière).
  const tarifCentimes = saisieEurosVersCentimes(tarif)
  const tarifSaisi = tarif.trim() !== ''
  // Validité **propre au tarif** : pilote le message du champ tarif, indépendamment du quota. Sans
  // cette séparation, un quota invalide ferait afficher l'erreur du tarif sur un tarif pourtant
  // correct (le message pointerait le mauvais champ).
  const tarifInvalide = tarifSaisi && tarifCentimes === null
  const quotaAnalyse = analyserQuota(quota)
  const quotaInvalide = quotaAnalyse === 'invalide'
  // Validité **globale** du formulaire : ne sert qu'à (dés)activer l'envoi — l'affichage par champ
  // s'appuie sur les validités propres (`tarifInvalide`, `quotaInvalide`).
  const entreeValide = tarifCentimes !== null && !quotaInvalide

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (tarifCentimes === null || quotaAnalyse === 'invalide') return
    const entree: NouveauDepart = {
      tarif_centimes: tarifCentimes,
      horaire: horaire.trim() || null,
      quota: quotaAnalyse,
    }
    if (enEdition) {
      modifier.mutate({ departId: depart.id, entree }, { onSuccess: onTermine })
    } else {
      // Création : on réinitialise le formulaire pour enchaîner un autre créneau.
      creer.mutate(entree, {
        onSuccess: () => {
          setTarif('')
          setHoraire('')
          setQuota('')
        },
      })
    }
  }

  return (
    <div>
      {enEdition && <h4 className="carte__soustitre">Modifier le départ {depart.numero}</h4>}
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <label className="formulaire__libelle">
          Tarif du créneau
          <input
            className="formulaire__champ"
            inputMode="decimal"
            value={tarif}
            onChange={(e) => setTarif(e.target.value)}
            placeholder="ex. 8,10 — « 0 » pour gratuit"
            aria-label="Tarif du départ en euros"
          />
          {tarifInvalide ? (
            <span className="carte__etat carte__etat--erreur" role="alert">
              Montant en euros attendu, avec au plus 2 décimales (ex. 8,10).
            </span>
          ) : (
            <span className="carte__etat">
              {tarifCentimes !== null
                ? decrireTarif(tarifCentimes)
                : 'Prix obligatoire (« 0 » = gratuit)'}
            </span>
          )}
        </label>
        <label className="formulaire__libelle">
          Horaire (facultatif)
          <input
            className="formulaire__champ"
            value={horaire}
            onChange={(e) => setHoraire(e.target.value)}
            placeholder="ex. 9h00"
            aria-label="Horaire du départ"
          />
        </label>
        <label className="formulaire__libelle">
          Quota d'inscrits (facultatif)
          <input
            className="formulaire__champ"
            inputMode="numeric"
            value={quota}
            onChange={(e) => setQuota(e.target.value)}
            placeholder="ex. 20 — vide = sans plafond"
            aria-label="Quota d'inscrits du départ"
          />
          {quotaInvalide ? (
            <span className="carte__etat carte__etat--erreur" role="alert">
              Nombre entier de places ≥ 1 attendu (ou vide pour aucun plafond).
            </span>
          ) : (
            <span className="carte__etat">
              {quotaAnalyse === null ? 'Aucun plafond' : `${quotaAnalyse} places maximum`}
            </span>
          )}
        </label>
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || !entreeValide}>
            {enEdition ? 'Enregistrer' : 'Ajouter le départ'}
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

function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return (
    <p className="carte__etat carte__etat--erreur" role="alert">
      {message}
    </p>
  )
}
