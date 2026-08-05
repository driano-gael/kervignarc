// Plan de salle d'un tournoi (E01US008) — réservé à l'admin (monté sous `estAdmin`).
//
// Applique un **gabarit modèle** de la bibliothèque à ce tournoi : l'application en crée une
// **copie** propre au tournoi, que l'on peut ensuite **ajuster** (nom, plafond cible par cible)
// **sans altérer** le modèle d'origine. Un tournoi porte au plus un plan à la fois ; en choisir
// un autre remplace le précédent. Ce plan sera la base du placement (EPIC-03).
//
// Vocabulaire (E16US001, ADR-0073) : un **pas de tir** est un groupement de cibles ; la place d'un
// archer devant sa cible est un **couloir de tir** (A, B, C, D). Ce que règle cet écran est un
// **plafond** de couloirs, pas un effectif : le placement en occupe au plus autant, et souvent
// moins (les blasons ont leurs propres budgets — `domain/placement.py`). D'où « **jusqu'à** N
// couloirs » dans les libellés, et l'aperçu des lettres en face de chaque réglage.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Gabarit } from './api'
import { decrire } from './format'
import { useAjusterGabarit, useAppliquerGabarit, useGabaritDuTournoi, useGabarits } from './hooks'

const PLAFONDS = [1, 2, 3, 4]
const PLAFOND_DEFAUT = 4

// La lettre d'un couloir se **dérive** de son rang (0 → A) plutôt que de sortir d'un tableau figé.
// Volontaire : `DETTE-010` prévoit de délester le plafond de 4 (E01US019, lettres au-delà de `D`).
// Un `['A','B','C','D']` de plus ici aurait été un 3ᵉ exemplaire à retrouver ce jour-là — et, pire,
// l'aperçu aurait affiché quatre cases pleines en face de « jusqu'à 6 couloirs » sans rien signaler.
// Ici, l'aperçu suit `PLAFONDS` : il n'y a plus qu'un seul endroit à changer.
const lettreCouloir = (rang: number) => String.fromCharCode(65 + rang)

export function PlanDeSalle({ tournoiId }: { tournoiId: number }) {
  const plan = useGabaritDuTournoi(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Plan de salle de ce tournoi</h3>
      {plan.isPending && <p className="carte__etat">Chargement…</p>}
      {plan.isError && <MessageErreur erreur={plan.error} />}
      {plan.isSuccess &&
        (plan.data === null ? (
          <SansGabarit tournoiId={tournoiId} />
        ) : (
          <GabaritApplique key={plan.data.id} tournoiId={tournoiId} gabarit={plan.data} />
        ))}
    </section>
  )
}

// Aucun gabarit appliqué : on invite à en choisir un dans la bibliothèque.
function SansGabarit({ tournoiId }: { tournoiId: number }) {
  return (
    <>
      <p className="carte__etat">
        Aucun gabarit n'est appliqué à ce tournoi. Choisissez-en un pour définir le plan de cibles.
      </p>
      <SelecteurModele tournoiId={tournoiId} libelleBouton="Appliquer à ce tournoi" />
    </>
  )
}

// Un gabarit est appliqué : résumé, ajustement cible par cible, et remplacement par un autre.
function GabaritApplique({ tournoiId, gabarit }: { tournoiId: number; gabarit: Gabarit }) {
  const [remplacement, setRemplacement] = useState(false)

  return (
    <>
      <div className="gabarit__ligne">
        <span className="gabarit__nom">{gabarit.nom}</span>
        <span className="gabarit__attributs">{decrire(gabarit)}</span>
        <span className="gabarit__actions">
          <button
            type="button"
            className="bouton--discret"
            onClick={() => setRemplacement((v) => !v)}
          >
            {remplacement ? 'Annuler le remplacement' : 'Remplacer par un autre gabarit'}
          </button>
        </span>
      </div>

      {remplacement && (
        <SelecteurModele
          tournoiId={tournoiId}
          libelleBouton="Remplacer"
          onApplique={() => setRemplacement(false)}
        />
      )}

      <FormulaireAjustement tournoiId={tournoiId} gabarit={gabarit} />
    </>
  )
}

// Sélecteur d'un modèle de la bibliothèque + bouton d'application/remplacement.
function SelecteurModele({
  tournoiId,
  libelleBouton,
  onApplique,
}: {
  tournoiId: number
  libelleBouton: string
  onApplique?: () => void
}) {
  const modeles = useGabarits()
  const appliquer = useAppliquerGabarit(tournoiId)
  const [modeleId, setModeleId] = useState<number | ''>('')

  // Seuls les modèles de bibliothèque sont proposés (l'API ne renvoie qu'eux ici).
  const disponibles = modeles.data ?? []
  const choix = modeleId === '' ? (disponibles[0]?.id ?? '') : modeleId

  if (modeles.isSuccess && disponibles.length === 0) {
    return (
      <p className="carte__etat">
        Créez d'abord un gabarit dans « Gabarits (modèles) », dans l'axe Atelier, puis revenez
        l'appliquer.
      </p>
    )
  }

  const appliquerChoix = () => {
    if (choix === '') return
    appliquer.mutate(choix, { onSuccess: onApplique })
  }

  return (
    <div>
      <form
        className="formulaire"
        onSubmit={(e) => {
          e.preventDefault()
          appliquerChoix()
        }}
      >
        <select
          className="formulaire__champ"
          value={choix}
          onChange={(e) => setModeleId(Number(e.target.value))}
          aria-label="Gabarit à appliquer"
        >
          {disponibles.map((modele) => (
            <option key={modele.id} value={modele.id}>
              {modele.nom} ({decrire(modele)})
            </option>
          ))}
        </select>
        <button type="submit" disabled={appliquer.isPending || choix === ''}>
          {libelleBouton}
        </button>
      </form>
      <MessageErreur erreur={appliquer.error} />
    </div>
  )
}

// Ajustement de la copie du tournoi : nom + plafond **cible par cible**. Le nombre de cibles se
// règle par le champ dédié (les cibles ajoutées démarrent au plafond par défaut). L'état local
// part de l'instance appliquée ; le composant est remonté (clé sur l'id) quand elle change.
export function FormulaireAjustement({
  tournoiId,
  gabarit,
}: {
  tournoiId: number
  gabarit: Gabarit
}) {
  const [nom, setNom] = useState(gabarit.nom)
  const [capacites, setCapacites] = useState<number[]>(gabarit.cibles.map((c) => c.capacite))
  const ajuster = useAjusterGabarit(tournoiId)

  const reglerNbCibles = (valeur: string) => {
    const cible = Number(valeur)
    if (!Number.isInteger(cible) || cible < 1) return
    setCapacites((actuelles) => {
      if (cible <= actuelles.length) return actuelles.slice(0, cible)
      return [...actuelles, ...Array<number>(cible - actuelles.length).fill(PLAFOND_DEFAUT)]
    })
  }

  const reglerCapacite = (index: number, plafond: number) => {
    setCapacites((actuelles) => actuelles.map((c, i) => (i === index ? plafond : c)))
  }

  const soumissionPossible = nom.trim() !== '' && capacites.length >= 1
  const inchange =
    nom === gabarit.nom &&
    capacites.length === gabarit.cibles.length &&
    capacites.every((c, i) => c === gabarit.cibles[i]?.capacite)

  const reinitialiser = () => {
    setNom(gabarit.nom)
    setCapacites(gabarit.cibles.map((c) => c.capacite))
  }

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    ajuster.mutate({ nom, capacites })
  }

  return (
    <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
      <h4 className="carte__soustitre">Ajuster ce plan (sans modifier le modèle d'origine)</h4>
      <input
        className="formulaire__champ"
        value={nom}
        onChange={(e) => setNom(e.target.value)}
        placeholder="Nom du plan"
        aria-label="Nom du plan de salle"
      />
      <label className="formulaire__libelle">
        Nombre de cibles
        <input
          className="formulaire__champ"
          type="number"
          min={1}
          value={capacites.length}
          onChange={(e) => reglerNbCibles(e.target.value)}
          aria-label="Nombre de cibles"
        />
      </label>

      <p className="plan-cibles__legende">
        Un <strong>pas de tir</strong> regroupe des cibles. Devant chaque cible, chaque archer tire
        depuis son <strong>couloir de tir</strong>, repéré par une lettre. Le nombre réglé ici est
        un <strong>plafond</strong> : les <strong>blasons</strong> posés sur la cible s'y
        répartissent — deux blasons admettant deux archers chacun remplissent quatre couloirs A, B,
        C, D — mais un blason encombrant peut en occuper moins. Le placement ne dépassera jamais ce
        plafond ; il peut installer moins d'archers que de couloirs.
      </p>

      <ul className="plan-cibles">
        {capacites.map((plafond, index) => (
          // Les cibles sont numérotées par rang, sans identité propre : l'index fait la clé.
          <li key={index} className="plan-cible">
            <span className="plan-cible__nom">Cible {index + 1}</span>
            <select
              className="formulaire__champ"
              value={plafond}
              onChange={(e) => reglerCapacite(index, Number(e.target.value))}
              aria-label={`Couloirs de tir de la cible ${index + 1}`}
            >
              {PLAFONDS.map((valeur) => (
                <option key={valeur} value={valeur}>
                  Jusqu'à {valeur} couloir{valeur > 1 ? 's' : ''} de tir
                </option>
              ))}
            </select>
            {/* Aperçu des lettres. `aria-hidden` parce que l'état occupable/inoccupable n'est
                porté que par le **style** (pointillés, opacité) : l'exposer ferait énoncer « A B C
                D » à l'identique quel que soit le réglage — une information fausse plutôt
                qu'absente. Le nombre, lui, est déjà annoncé par le sélecteur. */}
            <span className="plan-cible__couloirs" aria-hidden="true">
              {PLAFONDS.map((_, rang) => (
                <span
                  key={rang}
                  className={
                    rang < plafond
                      ? 'plan-cible__couloir'
                      : 'plan-cible__couloir plan-cible__couloir--inactif'
                  }
                >
                  {lettreCouloir(rang)}
                </span>
              ))}
            </span>
          </li>
        ))}
      </ul>

      <div className="formulaire__actions">
        <button type="submit" disabled={ajuster.isPending || !soumissionPossible || inchange}>
          Enregistrer les ajustements
        </button>
        <button
          type="button"
          className="bouton--discret"
          onClick={reinitialiser}
          disabled={inchange}
        >
          Réinitialiser
        </button>
      </div>
      <MessageErreur erreur={ajuster.error} />
    </form>
  )
}
