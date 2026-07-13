// Gestion des catégories d'un tournoi (E01US003) — réservée à l'admin (montée sous `estAdmin`).
//
// Liste + création + édition des métadonnées (libellé, arme, tranche d'âge, sexe) + suppression
// à confirmation. L'arme et la tranche d'âge sont en **texte libre** (les presets FFTA officiels
// viendront en E01US004) ; le sexe est un choix facultatif (Homme / Femme / Mixte).

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import type { Categorie, NouvelleCategorie, SexeCategorie } from './api'
import {
  useCategories,
  useCreerCategorie,
  useModifierCategorie,
  useSupprimerCategorie,
} from './hooks'

const OPTIONS_SEXE: { valeur: SexeCategorie; libelle: string }[] = [
  { valeur: 'H', libelle: 'Homme' },
  { valeur: 'F', libelle: 'Femme' },
  { valeur: 'mixte', libelle: 'Mixte' },
]

const LIBELLE_SEXE: Record<SexeCategorie, string> = {
  H: 'Homme',
  F: 'Femme',
  mixte: 'Mixte',
}

export function Categories({ tournoiId }: { tournoiId: number }) {
  const categories = useCategories(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Catégories</h3>
      <FormulaireCategorie tournoiId={tournoiId} />
      {categories.isError && <MessageErreur erreur={categories.error} />}
      {categories.data && categories.data.length > 0 && (
        <ul className="liste-categories">
          {categories.data.map((categorie) => (
            <LigneCategorie key={categorie.id} tournoiId={tournoiId} categorie={categorie} />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneCategorie({ tournoiId, categorie }: { tournoiId: number; categorie: Categorie }) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerCategorie(tournoiId)

  if (edition) {
    return (
      <li>
        <FormulaireCategorie
          tournoiId={tournoiId}
          categorie={categorie}
          onTermine={() => setEdition(false)}
        />
      </li>
    )
  }

  return (
    <li className="categorie">
      <div className="categorie__ligne">
        <span className="categorie__libelle">{categorie.libelle}</span>
        <span className="categorie__attributs">{decrire(categorie)}</span>
        <span className="categorie__actions">
          <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
            Éditer
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate(categorie.id)}
              >
                Confirmer la suppression
              </button>
              <button
                type="button"
                className="bouton--discret"
                onClick={() => setConfirmationSuppression(false)}
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
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

// Concatène les attributs facultatifs d'une catégorie pour l'affichage (arme · âge · sexe).
function decrire(categorie: Categorie): string {
  const parties = [
    categorie.arme,
    categorie.tranche_age,
    categorie.sexe ? LIBELLE_SEXE[categorie.sexe] : null,
  ].filter((partie): partie is string => partie !== null)
  return parties.join(' · ')
}

// Formulaire partagé création / édition : sans `categorie` il crée, avec il édite.
function FormulaireCategorie({
  tournoiId,
  categorie,
  onTermine,
}: {
  tournoiId: number
  categorie?: Categorie
  onTermine?: () => void
}) {
  const enEdition = categorie !== undefined
  const [libelle, setLibelle] = useState(categorie?.libelle ?? '')
  const [arme, setArme] = useState(categorie?.arme ?? '')
  const [trancheAge, setTrancheAge] = useState(categorie?.tranche_age ?? '')
  const [sexe, setSexe] = useState<SexeCategorie | ''>(categorie?.sexe ?? '')

  const creer = useCreerCategorie(tournoiId)
  const modifier = useModifierCategorie(tournoiId)
  const mutation = enEdition ? modifier : creer

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (libelle.trim() === '') return
    const entree: NouvelleCategorie = {
      libelle,
      arme: arme.trim() || null,
      tranche_age: trancheAge.trim() || null,
      sexe: sexe || null,
    }
    if (enEdition) {
      modifier.mutate({ id: categorie.id, entree }, { onSuccess: onTermine })
    } else {
      // Création : on vide le formulaire pour enchaîner une autre saisie.
      creer.mutate(entree, {
        onSuccess: () => {
          setLibelle('')
          setArme('')
          setTrancheAge('')
          setSexe('')
        },
      })
    }
  }

  return (
    <div>
      {enEdition && <h4 className="carte__soustitre">Modifier la catégorie</h4>}
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          placeholder="Libellé (ex. Senior Homme Arc Classique)"
          aria-label="Libellé de la catégorie"
        />
        <input
          className="formulaire__champ"
          value={arme}
          onChange={(e) => setArme(e.target.value)}
          placeholder="Arme (facultatif — ex. classique)"
          aria-label="Arme de la catégorie"
        />
        <input
          className="formulaire__champ"
          value={trancheAge}
          onChange={(e) => setTrancheAge(e.target.value)}
          placeholder="Tranche d'âge (facultatif — ex. senior)"
          aria-label="Tranche d'âge de la catégorie"
        />
        <select
          className="formulaire__champ"
          value={sexe}
          onChange={(e) => setSexe(e.target.value as SexeCategorie | '')}
          aria-label="Sexe de la catégorie"
        >
          <option value="">Sexe (facultatif)</option>
          {OPTIONS_SEXE.map((option) => (
            <option key={option.valeur} value={option.valeur}>
              {option.libelle}
            </option>
          ))}
        </select>
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || libelle.trim() === ''}>
            {enEdition ? 'Enregistrer' : 'Ajouter la catégorie'}
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
