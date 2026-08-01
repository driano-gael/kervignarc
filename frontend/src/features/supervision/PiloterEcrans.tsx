// Pilotage des écrans de salle depuis la console (E07US004, ADR-0064).
//
// Le motif du CA, mot pour mot : *« basculer sur le podium à 17 h et partir serrer des mains, c'est
// un écran figé sur le podium à 18 h pendant que les gens cherchent leur classement »*. Tout ce
// fichier découle de cette phrase.
//
// **L'arbitrage Q-UX7 (01/08/2026) vit ici** : une prise de contrôle se termine par une **durée**
// *ou* par un **retour explicite**, et les deux sont offerts. Concrètement :
//
// - le choix de durée propose des valeurs bornées **et** « jusqu'à ce que je rende la main » ;
// - une prise sans échéance déclenche un **rappel très visible** (`exige_rappel`, remonté par le
//   domaine — le drapeau n'est pas une décoration d'UI, c'est une règle nommée côté serveur) ;
// - « Rendre la main » est toujours disponible, y compris sur une prise à durée.
//
// L'écran, lui, ne reçoit **aucun ordre** : il lit sa consigne et décompte en local (ADR-0064). Ce
// panneau ne « pousse » donc rien — il pose un état.

import { useState } from 'react'

import { ErreurApi } from '../../shared/api/client'
import { LIBELLE_VUE, TOUTES_LES_VUES, type VueEcran } from '../ecrans/api'
import { usePrendreLeControle, useRendreLaMain } from '../ecrans/hooks'
import { formaterReste } from '../salle/rotation'
import type { PosteSupervision } from './api'
import { afficheEtat } from './etat'

/** Les durées proposées. `null` = « jusqu'à ce que je rende la main » — licite (Q-UX7), mais c'est
 * précisément celle qui déclenche le rappel. Bornées et peu nombreuses : à la table de
 * l'organisation, on choisit, on ne saisit pas. */
const DUREES: { valeur: number | null; libelle: string }[] = [
  { valeur: 300, libelle: '5 min' },
  { valeur: 600, libelle: '10 min' },
  { valeur: 1800, libelle: '30 min' },
  { valeur: null, libelle: 'jusqu’à ce que je rende la main' },
]

export function PiloterEcrans({
  tournoiId,
  ecrans,
  nbEnLigne,
}: {
  tournoiId: number
  ecrans: PosteSupervision[]
  nbEnLigne: number
}) {
  if (ecrans.length === 0) {
    return (
      <>
        <h3 className="carte__soustitre">Écrans de salle</h3>
        <p className="carte__etat">
          Aucun écran de salle pour ce tournoi (créez-en un dans «&nbsp;Écrans de salle&nbsp;»).
        </p>
      </>
    )
  }

  return (
    <>
      <h3 className="carte__soustitre">Écrans de salle</h3>
      <p className="supervision__compteur" role="status">
        <strong>
          {nbEnLigne}/{ecrans.length}
        </strong>{' '}
        écran(s) en ligne
      </p>
      <table className="table supervision__table">
        <thead>
          <tr>
            <th scope="col">Écran</th>
            <th scope="col">État</th>
            <th scope="col">Affiche</th>
            <th scope="col">Imposer une vue</th>
            <th scope="col">
              <span className="sr-only">Action</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {ecrans.map((ecran) => (
            <LigneEcran key={ecran.poste_id} ecran={ecran} tournoiId={tournoiId} />
          ))}
        </tbody>
      </table>
    </>
  )
}

function LigneEcran({ ecran, tournoiId }: { ecran: PosteSupervision; tournoiId: number }) {
  const prendre = usePrendreLeControle(tournoiId)
  const rendre = useRendreLaMain(tournoiId)
  const [vue, setVue] = useState<VueEcran>('classement')
  const [duree, setDuree] = useState<string>('600')
  const { classe, libelle } = afficheEtat(ecran.etat)
  const prise = ecran.prise

  const imposer = () => {
    const choisie = DUREES.find((d) => String(d.valeur) === duree)
    prendre.mutate({ posteId: ecran.poste_id, vue, dureeS: choisie?.valeur ?? null })
  }

  const erreur = prendre.error ?? rendre.error

  return (
    <tr>
      <td>{ecran.libelle ?? `Écran ${ecran.poste_id}`}</td>
      <td>
        <span className={`supervision__etat supervision__etat--${classe}`}>
          <span className="indicateur__pastille" aria-hidden="true" />
          {libelle}
        </span>
      </td>
      <td>
        {prise === null ? (
          <span>son déroulé</span>
        ) : (
          <span className="ecrans__ligne-prise">
            {prise.vue_figee === null ? 'séquence imposée' : LIBELLE_VUE[prise.vue_figee]}
            {prise.reste_s === null ? '' : ` · reprise dans ${formaterReste(prise.reste_s)}`}
            {/* Le CA « jamais un état forcé qu'on oublie » : sans échéance, la console **alarme**
                — c'est le seul endroit du produit qui puisse le faire. */}
            {prise.exige_rappel && (
              <>
                {' '}
                <span className="ecrans__rappel" role="status">
                  ⚠ sans échéance — pensez à rendre la main
                </span>
              </>
            )}
          </span>
        )}
      </td>
      <td>
        <div className="ecrans__deroule">
          <label className="sr-only" htmlFor={`vue-${ecran.poste_id}`}>
            Vue à imposer
          </label>
          <select
            id={`vue-${ecran.poste_id}`}
            value={vue}
            onChange={(e) => setVue(e.target.value as VueEcran)}
          >
            {TOUTES_LES_VUES.map((v) => (
              <option key={v} value={v}>
                {LIBELLE_VUE[v]}
              </option>
            ))}
          </select>
          <label className="sr-only" htmlFor={`duree-${ecran.poste_id}`}>
            Durée de la prise de contrôle
          </label>
          <select
            id={`duree-${ecran.poste_id}`}
            value={duree}
            onChange={(e) => setDuree(e.target.value)}
          >
            {DUREES.map((d) => (
              <option key={d.libelle} value={String(d.valeur)}>
                {d.libelle}
              </option>
            ))}
          </select>
          <button type="button" disabled={prendre.isPending} onClick={imposer}>
            Imposer
          </button>
        </div>
      </td>
      <td>
        {prise !== null && (
          <button
            type="button"
            className="lien"
            disabled={rendre.isPending}
            onClick={() => rendre.mutate(ecran.poste_id)}
          >
            Rendre la main
          </button>
        )}
        {erreur !== null && (
          <span className="carte__etat--erreur" role="alert">
            {erreur instanceof ErreurApi ? erreur.message : 'Échec du pilotage de l’écran.'}
          </span>
        )}
      </td>
    </tr>
  )
}
