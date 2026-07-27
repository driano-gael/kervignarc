// Configuration des départs (créneaux) d'un tournoi (E02US004, ADR-0017) — réservée à l'admin
// (montée sous `estAdmin`).
//
// Un départ est un créneau du tournoi (le tournoi rejoué plusieurs fois dans la journée) : il porte
// un **numéro** (attribué par le serveur), un **horaire** `HH:MM` obligatoire et un **tarif** obligatoire, en
// euros à l'écran mais transmis en **centimes** (ADR-0012). L'inscription d'un archer sur des départs
// est une autre US (E02US009) : ici on ne fait que **définir** les créneaux et leur prix.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import {
  centimesVersSaisieEuros,
  decrireTarif,
  saisieEurosVersCentimes,
} from '../competition/format'
import type { Depart, EtatDepart, NouveauDepart } from './api'
import { useCreerDepart, useDeparts, useModifierDepart, useSupprimerDepart } from './hooks'

// Libellé humain de l'état de cycle d'un créneau (E12US008), pour le badge.
const LIBELLE_ETAT: Record<EtatDepart, string> = {
  ouvert: 'Ouvert',
  lance: 'Lancé',
  clos: 'Clos',
}

// Horaire du jour `HH:MM` (24 h), **obligatoire** depuis E02US010 : miroir de la règle serveur
// (`domain.depart`). Le front ne fait que **prévenir** (masque + garde d'envoi) ; le serveur reste
// l'autorité (422 si le format ne convient pas).
const HORAIRE_HHMM = /^([01]\d|2[0-3]):[0-5]\d$/

// Masque de saisie : ne garde que les chiffres (max 4) et insère le `:` après l'heure — « 0900 »
// comme « 09:00 » aboutissent à « 09:00 ». Prévention de confort ; la validité finale reste jugée
// par `HORAIRE_HHMM` (et par le serveur).
function masquerHoraire(saisie: string): string {
  const chiffres = saisie.replace(/\D/g, '').slice(0, 4)
  if (chiffres.length <= 2) return chiffres
  return `${chiffres.slice(0, 2)}:${chiffres.slice(2)}`
}

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
  // `depart_en_cours_non_confirme` (E12US008) : le créneau est *lancé* ou *clos* — une session de
  // tir a eu lieu. Signalement chiffré (le message serveur dit combien d'archers ont tiré) ;
  // confirmer **subsume** le garde-fou d'inscriptions (inutile d'envoyer les deux). Exclusif du
  // précédent : un créneau lancé lève celui-ci, un créneau ouvert à inscriptions lève l'autre.
  const cycleSignale =
    supprimer.error instanceof ErreurApi && supprimer.error.code === 'depart_en_cours_non_confirme'

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
        <span className={`badge badge--${depart.etat}`} title="État du créneau">
          {LIBELLE_ETAT[depart.etat]}
        </span>
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
      {cycleSignale ? (
        <div className="carte__etat" role="alert">
          <p>{supprimer.error?.message}</p>
          <button
            type="button"
            className="bouton--danger"
            disabled={supprimer.isPending}
            onClick={() => supprimer.mutate({ departId: depart.id, confirmeCycle: true })}
          >
            Supprimer quand même (session de tir)
          </button>
        </div>
      ) : inscriptionsSignalees ? (
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

// Décrit un départ pour l'affichage : horaire (HH:MM, toujours présent) · tarif · quota (si
// plafonné). Le ` · ` sépare nettement l'horaire du numéro affiché à côté (bug démo « n° collé à
// l'horaire » : « Départ 1 » suivi de « 8h00 » se lisait « 18h00 » — le vrai HH:MM « 08:00 » et le
// séparateur lèvent l'ambiguïté).
function decrire(depart: Depart): string {
  const base = `${depart.horaire} · ${decrireTarif(depart.tarif_centimes)}`
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
// est **obligatoire** au format HH:MM (E02US010).
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
  // Horaire **obligatoire** (E02US010) : `HH:MM` valide requis. On n'affiche l'erreur qu'une fois
  // quelque chose saisi (comme le tarif) ; un champ vide bloque simplement l'envoi.
  const horaireValide = HORAIRE_HHMM.test(horaire)
  const horaireInvalide = horaire.trim() !== '' && !horaireValide
  const quotaAnalyse = analyserQuota(quota)
  const quotaInvalide = quotaAnalyse === 'invalide'
  // Validité **globale** du formulaire : ne sert qu'à (dés)activer l'envoi — l'affichage par champ
  // s'appuie sur les validités propres (`tarifInvalide`, `horaireInvalide`, `quotaInvalide`).
  const entreeValide = tarifCentimes !== null && horaireValide && !quotaInvalide

  // Construit l'entrée depuis l'état courant du formulaire, ou `null` si une saisie est invalide
  // (le garde d'envoi l'empêche déjà ; ce garde-ci rend la fonction sûre à réutiliser).
  const construireEntree = (): NouveauDepart | null => {
    if (tarifCentimes === null || quotaAnalyse === 'invalide' || !horaireValide) return null
    return {
      tarif_centimes: tarifCentimes,
      horaire,
      quota: quotaAnalyse,
    }
  }

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    const entree = construireEntree()
    if (entree === null) return
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

  // `depart_en_cours_non_confirme` (E12US008) : éditer un créneau *lancé*/*clos* est signalé (le
  // message serveur chiffre l'état et les tireurs). L'admin confirme, et l'on rejoue l'édition avec
  // `confirmeCycle` — mêmes valeurs de formulaire.
  const cycleSignale =
    enEdition &&
    modifier.error instanceof ErreurApi &&
    modifier.error.code === 'depart_en_cours_non_confirme'

  const confirmerEdition = () => {
    const entree = construireEntree()
    if (entree === null || depart === undefined) return
    modifier.mutate({ departId: depart.id, entree, confirmeCycle: true }, { onSuccess: onTermine })
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
          Horaire (HH:MM)
          <input
            className="formulaire__champ"
            inputMode="numeric"
            maxLength={5}
            value={horaire}
            onChange={(e) => setHoraire(masquerHoraire(e.target.value))}
            placeholder="ex. 09:00"
            aria-label="Horaire du départ, au format HH:MM"
          />
          {horaireInvalide ? (
            <span className="carte__etat carte__etat--erreur" role="alert">
              Horaire du jour attendu, au format HH:MM (ex. 09:00, entre 00:00 et 23:59).
            </span>
          ) : (
            <span className="carte__etat">
              {horaireValide ? `Départ à ${horaire}` : 'Horaire obligatoire (ex. 09:00)'}
            </span>
          )}
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
      {cycleSignale ? (
        <div className="carte__etat" role="alert">
          <p>{modifier.error?.message}</p>
          <button
            type="button"
            className="bouton--danger"
            disabled={modifier.isPending || !entreeValide}
            onClick={confirmerEdition}
          >
            Enregistrer quand même (session de tir)
          </button>
        </div>
      ) : (
        <MessageErreur erreur={mutation.error} />
      )}
    </div>
  )
}
