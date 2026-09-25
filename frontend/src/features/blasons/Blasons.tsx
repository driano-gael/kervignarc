// Gestion des blasons d'un tournoi (E01US005 ; zones : E01US014) — admin (sous `estAdmin`).
//
// Liste + panneau latéral d'édition (nom, taille, capacité, zones) + suppression à confirmation. Un blason
// modélise l'occupation d'une cible : la **taille** est une fraction de place et la **capacité** le
// nombre d'archers admis. Les **zones** sont les valeurs de score admises, qui pilotent le pavé de
// saisie (EPIC-04) : un triple 40 n'a pas les zones 5 → 1. Les bornes sont validées côté serveur.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Blason, NouveauBlason, Zone } from './api'
import { ZONE_MANQUE, ZONES_CANONIQUES } from './api'
import { useBlasons, useCreerBlason, useModifierBlason, useSupprimerBlason } from './hooks'
import { groupesParOrigine, selectionCourante, type Selection } from './panneau'
import { ZONES_DEFAUT, aUneZoneMarquante, basculerZone, estVerrouillee } from './zones'

// A06, variante B retenue le 04/08 — « la liste reste, l'édition s'ouvre à droite » (E17US007).
// Avant, « Éditer » remplaçait la ligne par le formulaire : la variante A, **écartée**.
export function Blasons({ tournoiId }: { tournoiId: number }) {
  const blasons = useBlasons(tournoiId)
  const [selection, setSelection] = useState<Selection | null>(null)
  const liste = blasons.data ?? []
  const panneau = selectionCourante(selection, liste)
  const fermer = () => setSelection(null)

  return (
    <section>
      <div className="blasons__entete">
        <h3 className="carte__soustitre">Blasons</h3>
        <span className="blasons__compte">
          {liste.length} blason{liste.length > 1 ? 's' : ''}
        </span>
        <button type="button" onClick={() => setSelection({ mode: 'creation' })}>
          Ajouter un blason
        </button>
      </div>
      {blasons.isError && <MessageErreur erreur={blasons.error} />}
      <div className={panneau === null ? 'avec-panneau' : 'avec-panneau avec-panneau--ouvert'}>
        {liste.length > 0 && (
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Blason</th>
                <th scope="col">Taille</th>
                <th scope="col">Capacité</th>
                <th scope="col">Zones</th>
              </tr>
            </thead>
            {groupesParOrigine(liste).map((groupe) => (
              <tbody key={groupe.origine}>
                <tr>
                  <th scope="rowgroup" colSpan={4} className="blasons__groupe">
                    {groupe.libelle}
                  </th>
                </tr>
                {groupe.blasons.map((blason) => (
                  <LigneBlason
                    key={blason.id}
                    blason={blason}
                    choisi={panneau?.mode === 'edition' && panneau.blason.id === blason.id}
                    onChoisir={() => setSelection({ mode: 'edition', id: blason.id })}
                  />
                ))}
              </tbody>
            ))}
          </table>
        )}
        {panneau !== null && (
          <aside className="panneau-edition" aria-label="Édition du blason">
            {/* `key` : changer de ligne **remonte** le formulaire — ses champs sont des `useState`
                initialisés au montage, ils garderaient sinon le blason précédent. */}
            <FormulaireBlason
              key={panneau.mode === 'edition' ? panneau.blason.id : 'creation'}
              tournoiId={tournoiId}
              blason={panneau.mode === 'edition' ? panneau.blason : undefined}
              onTermine={fermer}
            />
            {panneau.mode === 'edition' && (
              <SuppressionBlason
                tournoiId={tournoiId}
                blason={panneau.blason}
                onSupprime={fermer}
              />
            )}
          </aside>
        )}
      </div>
    </section>
  )
}

// Une ligne : choisir le blason ouvre le panneau. Le nom est un bouton — une ligne de tableau
// cliquable n'est ni atteignable au clavier ni annoncée par un lecteur d'écran.
function LigneBlason({
  blason,
  choisi,
  onChoisir,
}: {
  blason: Blason
  choisi: boolean
  onChoisir: () => void
}) {
  const capacite = blason.capacite > 1 ? `${blason.capacite} archers` : '1 archer'
  return (
    <tr className={choisi ? 'blasons__ligne blasons__ligne--choisie' : 'blasons__ligne'}>
      <td>
        <button
          type="button"
          className="lien blasons__nom"
          aria-current={choisi ? 'true' : undefined}
          onClick={onChoisir}
        >
          {blason.nom}
        </button>
      </td>
      <td>{blason.taille.toLocaleString('fr-FR')}</td>
      <td>{capacite}</td>
      <td>{blason.zones.join(' ')}</td>
    </tr>
  )
}

function SuppressionBlason({
  tournoiId,
  blason,
  onSupprime,
}: {
  tournoiId: number
  blason: Blason
  onSupprime: () => void
}) {
  const [confirmation, setConfirmation] = useState(false)
  const supprimer = useSupprimerBlason(tournoiId)
  return (
    <div className="panneau-edition__danger">
      {confirmation ? (
        <>
          <button
            type="button"
            className="bouton--danger"
            disabled={supprimer.isPending}
            onClick={() => supprimer.mutate(blason.id, { onSuccess: onSupprime })}
          >
            Confirmer la suppression
          </button>
          <button type="button" className="bouton--discret" onClick={() => setConfirmation(false)}>
            Annuler
          </button>
        </>
      ) : (
        <button type="button" className="bouton--danger" onClick={() => setConfirmation(true)}>
          Supprimer ce blason
        </button>
      )}
      <MessageErreur erreur={supprimer.error} />
    </div>
  )
}

// Formulaire partagé création / édition : sans `blason` il crée, avec il édite.
function FormulaireBlason({
  tournoiId,
  blason,
  onTermine,
}: {
  tournoiId: number
  blason?: Blason
  onTermine?: () => void
}) {
  const enEdition = blason !== undefined
  const [nom, setNom] = useState(blason?.nom ?? '')
  const [taille, setTaille] = useState(blason ? String(blason.taille) : '1')
  const [capacite, setCapacite] = useState(blason ? String(blason.capacite) : '1')
  // À la création, le défaut est le jeu complet d'un blason simple — miroir de `ZONES_DEFAUT`
  // du domaine, et non de `ZONES_CANONIQUES` : c'est un sur-ensemble, à restreindre pour un
  // triple 40. Le serveur appliquerait le même s'il était omis ; on l'affiche pour que l'admin
  // voie ce qu'il enregistre.
  const [zones, setZones] = useState<Zone[]>(blason ? blason.zones : [...ZONES_DEFAUT])

  const creer = useCreerBlason(tournoiId)
  const modifier = useModifierBlason(tournoiId)
  const mutation = enEdition ? modifier : creer

  // Reprend les bornes du domaine (taille ]0, 1], capacité entière >= 1, au moins une zone
  // marquante) pour éviter d'envoyer une requête vouée au 422 ; le serveur reste l'autorité
  // (revalidation à la frontière). Les règles de zones vivent dans `zones.ts` — pures, testées.
  const tailleNombre = Number(taille)
  const capaciteNombre = Number(capacite)
  const entreeValide =
    nom.trim() !== '' &&
    Number.isFinite(tailleNombre) &&
    tailleNombre > 0 &&
    tailleNombre <= 1 &&
    Number.isInteger(capaciteNombre) &&
    capaciteNombre >= 1 &&
    aUneZoneMarquante(zones)

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!entreeValide) return
    const entree: NouveauBlason = {
      nom,
      taille: tailleNombre,
      capacite: capaciteNombre,
      zones,
    }
    if (enEdition) {
      modifier.mutate({ id: blason.id, entree }, { onSuccess: onTermine })
    } else {
      // Création : le panneau se referme, le blason apparaît dans la liste.
      creer.mutate(entree, { onSuccess: onTermine })
    }
  }

  return (
    <div>
      <h4 className="carte__soustitre">{enEdition ? blason.nom : 'Nouveau blason'}</h4>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom (ex. Trispot 40)"
          aria-label="Nom du blason"
        />
        <label className="formulaire__libelle">
          Taille (fraction de place, de 0 à 1)
          <input
            className="formulaire__champ"
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={taille}
            onChange={(e) => setTaille(e.target.value)}
            aria-label="Taille du blason (fraction de place)"
          />
        </label>
        <label className="formulaire__libelle">
          Capacité (nombre d'archers)
          <input
            className="formulaire__champ"
            type="number"
            min="1"
            step="1"
            value={capacite}
            onChange={(e) => setCapacite(e.target.value)}
            aria-label="Capacité du blason (nombre d'archers)"
          />
        </label>
        <fieldset className="zones">
          <legend className="formulaire__libelle">Valeurs de score admises</legend>
          <p className="zones__aide">
            Décochez ce qui n’est pas tirable sur ce blason — un triple 40 s’arrête à 6. Le pavé de
            saisie ne proposera que ces valeurs.
          </p>
          <div className="zones__cases">
            {ZONES_CANONIQUES.map((zone) => (
              <label key={zone} className="zones__case">
                <input
                  type="checkbox"
                  checked={zones.includes(zone)}
                  disabled={estVerrouillee(zones, zone)}
                  onChange={() => setZones((actuelles) => basculerZone(actuelles, zone))}
                  aria-label={zone === ZONE_MANQUE ? 'Manqué (toujours admis)' : `Zone ${zone}`}
                />
                {zone}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || !entreeValide}>
            {enEdition ? 'Enregistrer' : 'Ajouter le blason'}
          </button>
          <button type="button" className="bouton--discret" onClick={onTermine}>
            {enEdition ? 'Fermer' : 'Annuler'}
          </button>
        </div>
      </form>
      <MessageErreur erreur={mutation.error} />
    </div>
  )
}
