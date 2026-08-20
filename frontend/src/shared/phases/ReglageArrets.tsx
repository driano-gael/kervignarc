// La fiche des **pauses programmées** d'une étape (E05US033, ADR-0091).
//
// Partagée par les **deux** écrans qui composent des phases — « Composer un déroulé » (un modèle de
// bibliothèque) et « Phases » (le déroulé d'un tournoi) —, comme `ReglageSuisse`, `ReglagePoules` et
// `ReglageBigShootOff` avant elle.
//
// ⚠️ **Ce composant ne détient AUCUN état** (leçon de la revue d'E06US006, reprise telle quelle) :
// monté sous condition, un état dérivé d'une prop diverge dès que la condition bascule.
//
// ⚠️ **La fiche est montée sur TOUS les types, y compris ceux qui n'admettent pas d'arrêt.** Elle
// n'offre alors aucun champ, mais elle **dit pourquoi** — c'est le tout l'intérêt de la monter quand
// même. La cacher laisserait l'organisateur chercher un réglage qu'il a vu sur la phase voisine, sans
// jamais apprendre qu'il n'existe pas ici.

import type { EtatArrets, LigneArret, PorteeArret } from './arrets'
import { TOURS_MAX_REGLABLES, decrire, ligneNeuve, toursEnDoublon, versArrets } from './arrets'

/**
 * Rend la fiche des pauses programmées. Aucun état : l'unique source est `etat`, détenu par le parent.
 *
 * `arretable` dit si le **type** de cette étape annonce ses tours, donc si une pause peut s'y poser
 * (`TYPES_ARRETABLES`). C'est le parent qui le sait — il connaît le type choisi. Quand c'est faux, la
 * fiche n'offre aucun champ et explique le refus : l'API rejette l'arrêt (`ArretProgrammeInvalide`,
 * 422) et, le `PUT` étant une édition **totale**, c'est l'étape entière qui serait refusée.
 */
export function ReglageArrets({
  etat,
  surChangement,
  arretable,
}: {
  etat: EtatArrets
  surChangement: (etat: EtatArrets) => void
  arretable: boolean
}) {
  const doublons = toursEnDoublon(etat)
  const illisible = versArrets(etat) === undefined

  function changerLigne(cle: string, champs: Partial<LigneArret>) {
    surChangement({
      ...etat,
      lignes: etat.lignes.map((ligne) => (ligne.cle === cle ? { ...ligne, ...champs } : ligne)),
    })
  }

  function retirer(cle: string) {
    surChangement({ ...etat, lignes: etat.lignes.filter((ligne) => ligne.cle !== cle) })
  }

  return (
    <fieldset className="deroule__sources">
      <legend>Pauses programmées</legend>

      <p className="carte__aide">
        Par défaut, la salle enchaîne les tours toute seule. Programmez une pause pour l’arrêter à
        un moment choisi — le repas, une réorganisation, une annonce. Un admin la relance d’un
        geste, et la phase repart en automatique jusqu’à la pause suivante.
      </p>

      {/* Le type ne dit pas ses tours : aucun champ, mais le motif. Écrit en clair et **sans**
          `role="status"` — c'est une explication statique, pas l'annonce d'un changement (même
          raison que le paragraphe « aucune pause programmée » ci-dessous). */}
      {!arretable ? (
        <p className="carte__aide">
          Ce type de phase n’annonce pas ses tours&nbsp;: l’application ne saurait pas à quel moment
          y appliquer la pause. Les pauses se programment sur une élimination directe, des poules,
          un système suisse ou un Big Shoot Off.
        </p>
      ) : etat.lignes.length === 0 ? (
        /* ⚠️ **Pas de `role="status"` ici**, à la différence des deux alertes en bas de fiche. Ce
           texte est **statique** : il décrit le défaut, il n'annonce aucun changement. Le lui donner
           a fait tomber deux tests de `Profondeur.test.tsx`, qui gardent l'invariant « bouton bloqué
           ⟺ un message dit pourquoi » en cherchant `queryByRole('status')` — un état vivant
           permanent rendait la garde inopérante. Le test avait raison, pas la fiche. */
        <p className="carte__aide">
          Aucune pause programmée&nbsp;: la phase se déroulera d’un bout à l’autre sans s’arrêter.
        </p>
      ) : (
        <ul className="deroule__liste">
          {etat.lignes.map((ligne) => (
            <li key={ligne.cle}>
              <label className="formulaire__libelle">
                Après le tour
                <input
                  inputMode="numeric"
                  placeholder="3"
                  value={ligne.apresTour}
                  onChange={(e) => changerLigne(ligne.cle, { apresTour: e.target.value })}
                />
              </label>

              <label className="formulaire__libelle">
                Portée
                <select
                  value={ligne.portee}
                  onChange={(e) =>
                    changerLigne(ligne.cle, { portee: e.target.value as PorteeArret })
                  }
                >
                  <option value="phase">Cette phase seule</option>
                  <option value="depart">Tout le créneau</option>
                </select>
              </label>

              {/* La relecture en clair. L'écran ne peut pas dire **quand** la pause tombera (il
                  ignore le nombre de tours et l'heure) mais il peut dire **ce qu'elle coupera**, et
                  c'est ce que l'organisateur relit avant de valider son planning. */}
              <p className="carte__aide">{decrire(ligne)}</p>

              <button
                type="button"
                className="bouton bouton--discret"
                onClick={() => retirer(ligne.cle)}
              >
                Retirer cette pause
              </button>
            </li>
          ))}
        </ul>
      )}

      {arretable && (
        <button
          type="button"
          className="bouton bouton--discret"
          onClick={() => surChangement({ ...etat, lignes: [...etat.lignes, ligneNeuve()] })}
        >
          Ajouter une pause
        </button>
      )}

      {doublons.length > 0 && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Deux pauses sont posées après le même tour ({doublons.join(', ')})&nbsp;: la phase ne peut
          pas s’arrêter deux fois au même endroit.
        </span>
      )}

      {illisible && doublons.length === 0 && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Indiquez pour chaque pause un numéro de tour entier, entre 1 et {TOURS_MAX_REGLABLES}.
        </span>
      )}
    </fieldset>
  )
}
