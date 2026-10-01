// Composition des équipes d'un tournoi (E13US002) — réservé à l'admin.
// ⚠️ L'écran **signale** la non-conformité, il ne bloque rien (CA 4) : le serveur est seul juge,
// y compris de « une équipe par type » (409 affiché tel quel).

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useArchers } from '../archers/hooks'
import { useCategories } from '../categories/hooks'
import type { Equipe, TypeEquipe } from './api'
import {
  useAjouterMembre,
  useCreerEquipe,
  useEquipes,
  useModifierEquipe,
  useRetirerMembre,
  useSupprimerEquipe,
} from './hooks'
import { libelleEcart, TYPES_EQUIPE } from './presentation'
import './equipes.css'

export function Equipes({ tournoiId }: { tournoiId: number }) {
  const equipes = useEquipes(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Équipes</h3>
      <p className="carte__etat">
        Composez les équipes membre par membre. Une équipe incomplète ou non conforme s’enregistre
        quand même : l’écran vous dit ce qui manque.
      </p>
      <FormulaireEquipe tournoiId={tournoiId} />
      {equipes.isError && <MessageErreur erreur={equipes.error} />}
      {equipes.data && equipes.data.length === 0 && (
        <p className="carte__etat">Aucune équipe pour ce tournoi.</p>
      )}
      {equipes.data && equipes.data.length > 0 && (
        <div className="table-defilement">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Équipe</th>
                <th scope="col">Membres</th>
                <th scope="col">Conformité</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            {equipes.data.map((equipe) => (
              // ⚠️ Le nom dans la `key` : SQLite réattribue les `id`, et l'état local d'une ligne
              // (suppression armée) ne doit pas passer à l'équipe qui hérite de l'id.
              <LigneEquipe
                key={`${equipe.id}:${equipe.nom}`}
                tournoiId={tournoiId}
                equipe={equipe}
                toutes={equipes.data}
              />
            ))}
          </table>
        </div>
      )}
    </section>
  )
}

// Équipe, membres, conformité, actions.
const COLONNES = 4

function LigneEquipe({
  tournoiId,
  equipe,
  toutes,
}: {
  tournoiId: number
  equipe: Equipe
  toutes: Equipe[]
}) {
  const [edition, setEdition] = useState(false)
  const [ajout, setAjout] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerEquipe(tournoiId)
  const retirer = useRetirerMembre(tournoiId)

  if (edition) {
    return (
      <tbody>
        <tr>
          <td colSpan={COLONNES}>
            <FormulaireEquipe
              tournoiId={tournoiId}
              equipe={equipe}
              onTermine={() => setEdition(false)}
            />
          </td>
        </tr>
      </tbody>
    )
  }

  const detail =
    ajout || confirmationSuppression || supprimer.error !== null || retirer.error !== null
  return (
    <tbody>
      <tr>
        <td>
          <span className="equipe__nom">{equipe.nom}</span>
          <span className="equipe__type">
            {TYPES_EQUIPE[equipe.type].libelle} · {equipe.effectif_attendu} attendu
            {equipe.effectif_attendu > 1 ? 's' : ''}
          </span>
        </td>
        <td>
          {equipe.membres.length === 0 ? (
            <span className="carte__etat">Aucun membre</span>
          ) : (
            <ul className="equipe__membres">
              {equipe.membres.map((membre) => {
                const nomMembre = `${membre.prenom} ${membre.nom}`
                return (
                  <li key={membre.archer_id} className="equipe__membre">
                    <span>
                      {nomMembre} <span className="equipe__categorie">· {membre.categorie}</span>
                    </span>
                    <button
                      type="button"
                      className="bouton--discret"
                      disabled={retirer.isPending}
                      aria-label={`Retirer ${nomMembre} de l’équipe ${equipe.nom}`}
                      onClick={() =>
                        retirer.mutate({ equipeId: equipe.id, archerId: membre.archer_id })
                      }
                    >
                      Retirer
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </td>
        <td>
          {equipe.conforme ? (
            <span className="badge equipe__conforme">CONFORME</span>
          ) : (
            <ul className="equipe__ecarts" aria-label={`Écarts de l’équipe ${equipe.nom}`}>
              {equipe.ecarts.map((ecart) => (
                <li key={ecart}>{libelleEcart(ecart, equipe)}</li>
              ))}
            </ul>
          )}
        </td>
        <td>
          <span className="equipe__actions">
            <button
              type="button"
              className="bouton--discret"
              aria-expanded={ajout}
              aria-label={`Ajouter un membre à l’équipe ${equipe.nom}`}
              onClick={() => setAjout(!ajout)}
            >
              {ajout ? 'Fermer' : 'Ajouter un membre'}
            </button>
            <button
              type="button"
              className="bouton--discret"
              aria-label={`Modifier l’équipe ${equipe.nom}`}
              onClick={() => setEdition(true)}
            >
              Modifier
            </button>
            {confirmationSuppression ? (
              <>
                <button
                  type="button"
                  className="bouton--danger"
                  disabled={supprimer.isPending}
                  aria-label={`Confirmer la suppression de l’équipe ${equipe.nom}`}
                  onClick={() => supprimer.mutate(equipe.id)}
                >
                  Confirmer la suppression
                </button>
                <button
                  type="button"
                  className="bouton--discret"
                  aria-label={`Annuler la suppression de l’équipe ${equipe.nom}`}
                  onClick={() => setConfirmationSuppression(false)}
                >
                  Annuler
                </button>
              </>
            ) : (
              <button
                type="button"
                className="bouton--danger"
                aria-label={`Supprimer l’équipe ${equipe.nom}`}
                onClick={() => setConfirmationSuppression(true)}
              >
                Supprimer
              </button>
            )}
          </span>
        </td>
      </tr>
      {detail && (
        <tr>
          <td colSpan={COLONNES}>
            {ajout && <ChoixMembre tournoiId={tournoiId} equipe={equipe} toutes={toutes} />}
            {confirmationSuppression && (
              <p className="carte__etat">
                Ses archers restent inscrits : seule l’équipe disparaît.
              </p>
            )}
            <MessageErreur erreur={supprimer.error} />
            <MessageErreur erreur={retirer.error} />
          </td>
        </tr>
      )}
    </tbody>
  )
}

// Au-delà, la liste ne tient plus au doigt : on demande d'affiner la recherche.
const RESULTATS_MAX = 12

function ChoixMembre({
  tournoiId,
  equipe,
  toutes,
}: {
  tournoiId: number
  equipe: Equipe
  toutes: Equipe[]
}) {
  const [recherche, setRecherche] = useState('')
  const archers = useArchers(tournoiId)
  const categories = useCategories(tournoiId)
  const ajouter = useAjouterMembre(tournoiId)

  const libelleCategorie = new Map((categories.data ?? []).map((c) => [c.id, c.libelle]))
  // Indicatif seulement : le serveur reste juge de « une équipe par type » (CA 3).
  const equipeDuMemeType = new Map<number, string>()
  for (const autre of toutes) {
    if (autre.type !== equipe.type || autre.id === equipe.id) continue
    for (const membre of autre.membres) equipeDuMemeType.set(membre.archer_id, autre.nom)
  }
  const dejaMembres = new Set(equipe.membres.map((m) => m.archer_id))
  const terme = recherche.trim().toLowerCase()
  const candidats = (archers.data ?? []).filter(
    (a) => !dejaMembres.has(a.id) && `${a.prenom} ${a.nom}`.toLowerCase().includes(terme),
  )
  const affiches = candidats.slice(0, RESULTATS_MAX)

  return (
    <div className="equipe__choix">
      <input
        className="formulaire__champ"
        type="search"
        value={recherche}
        onChange={(e) => setRecherche(e.target.value)}
        placeholder="Rechercher un archer"
        aria-label={`Rechercher un archer à ajouter à l’équipe ${equipe.nom}`}
      />
      {archers.isError && <MessageErreur erreur={archers.error} />}
      {archers.data && candidats.length === 0 && (
        <p className="carte__etat">Aucun archer ne correspond.</p>
      )}
      <ul className="equipe__candidats">
        {affiches.map((archer) => {
          const nomArcher = `${archer.prenom} ${archer.nom}`
          const autreEquipe = equipeDuMemeType.get(archer.id)
          return (
            <li key={archer.id}>
              <button
                type="button"
                className="equipe__candidat"
                disabled={ajouter.isPending}
                aria-label={`Ajouter ${nomArcher} à l’équipe ${equipe.nom}`}
                onClick={() => ajouter.mutate({ equipeId: equipe.id, archerId: archer.id })}
              >
                <span>{nomArcher}</span>
                <span className="equipe__categorie">
                  {libelleCategorie.get(archer.categorie_id) ?? ''}
                </span>
                {autreEquipe !== undefined && (
                  <span className="equipe__deja">Déjà dans « {autreEquipe} »</span>
                )}
              </button>
            </li>
          )
        })}
      </ul>
      {candidats.length > RESULTATS_MAX && (
        <p className="carte__etat">
          {candidats.length - RESULTATS_MAX} autres archers : affinez la recherche.
        </p>
      )}
      <MessageErreur erreur={ajouter.error} />
    </div>
  )
}

// Formulaire partagé création / modification : sans `equipe` il crée, avec il modifie.
function FormulaireEquipe({
  tournoiId,
  equipe,
  onTermine,
}: {
  tournoiId: number
  equipe?: Equipe
  onTermine?: () => void
}) {
  const enEdition = equipe !== undefined
  const [nom, setNom] = useState(equipe?.nom ?? '')
  const [type, setType] = useState<TypeEquipe>(equipe?.type ?? 'standard')
  const [effectif, setEffectif] = useState(
    String(equipe?.effectif_attendu ?? TYPES_EQUIPE.standard.effectifParDefaut),
  )

  const creer = useCreerEquipe(tournoiId)
  const modifier = useModifierEquipe(tournoiId)
  const mutation = enEdition ? modifier : creer

  const effectifNombre = Number(effectif)
  // Reprend les règles du domaine (CA 1) pour éviter un 422 certain ; le serveur reste l'autorité.
  const entreeValide = nom.trim() !== '' && Number.isInteger(effectifNombre) && effectifNombre >= 1

  // Changer de type remet l'effectif FFTA du nouveau type : celui de l'ancien n'a plus de sens.
  const changerType = (nouveau: TypeEquipe) => {
    setType(nouveau)
    setEffectif(String(TYPES_EQUIPE[nouveau].effectifParDefaut))
  }

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!entreeValide) return
    const entree = { nom, type, effectif_attendu: effectifNombre }
    if (enEdition) {
      modifier.mutate({ equipeId: equipe.id, entree }, { onSuccess: onTermine })
    } else {
      creer.mutate(entree, {
        onSuccess: () => {
          setNom('')
          changerType('standard')
        },
      })
    }
  }

  return (
    <div>
      {enEdition && <h4 className="carte__soustitre">Modifier l’équipe</h4>}
      {/* Nommé pour distinguer, au lecteur d'écran, ses champs de ceux du formulaire de création. */}
      <form
        className="formulaire"
        onSubmit={soumettre}
        aria-label={enEdition ? `Modifier l’équipe ${equipe.nom}` : 'Créer une équipe'}
      >
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom de l’équipe"
          aria-label="Nom de l’équipe"
        />
        <select
          className="formulaire__champ"
          value={type}
          onChange={(e) => changerType(e.target.value as TypeEquipe)}
          aria-label="Type d’équipe"
        >
          {(Object.keys(TYPES_EQUIPE) as TypeEquipe[]).map((t) => (
            <option key={t} value={t}>
              {TYPES_EQUIPE[t].libelle}
            </option>
          ))}
        </select>
        <label className="formulaire__libelle">
          Effectif attendu
          <input
            className="formulaire__champ"
            type="number"
            min={1}
            step={1}
            value={effectif}
            onChange={(e) => setEffectif(e.target.value)}
          />
        </label>
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || !entreeValide}>
            {enEdition ? 'Enregistrer' : 'Créer l’équipe'}
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
