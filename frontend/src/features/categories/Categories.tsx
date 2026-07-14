// Gestion des catégories d'un tournoi (E01US003) — réservée à l'admin (montée sous `estAdmin`).
//
// Liste + création + édition des métadonnées (libellé, arme, tranche d'âge, sexe) + suppression
// à confirmation. L'arme et la tranche d'âge sont en **texte libre** ; le sexe est un choix
// facultatif (Homme / Femme / Mixte). Un bouton **pré-charge le jeu de catégories FFTA salle
// (18 m)** officiel (E01US004) : les catégories ainsi ajoutées sont ordinaires (modifiables et
// supprimables comme les autres).

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import type { Blason } from '../blasons/api'
import { useBlasons } from '../blasons/hooks'
import type { Categorie, NouvelleCategorie, SexeCategorie } from './api'
import {
  useCategories,
  useCreerCategorie,
  useModifierCategorie,
  usePrechargerCategoriesFFTA,
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
  // Les blasons du tournoi alimentent le sélecteur « blason par défaut » et l'affichage du nom
  // sur chaque ligne (E01US006). Liste partagée pour éviter une requête par ligne.
  const blasons = useBlasons(tournoiId)
  const listeBlasons = blasons.data ?? []

  return (
    <section>
      <h3 className="carte__soustitre">Catégories</h3>
      <PrechargementFFTA tournoiId={tournoiId} />
      <FormulaireCategorie tournoiId={tournoiId} blasons={listeBlasons} />
      {categories.isError && <MessageErreur erreur={categories.error} />}
      {categories.data && categories.data.length > 0 && (
        <ul className="liste-categories">
          {categories.data.map((categorie) => (
            <LigneCategorie
              key={categorie.id}
              tournoiId={tournoiId}
              categorie={categorie}
              blasons={listeBlasons}
            />
          ))}
        </ul>
      )}
    </section>
  )
}

// Pré-chargement du jeu FFTA salle (18 m) : un clic ajoute les catégories officielles absentes.
// L'action est rejouable sans doublon (le serveur ignore les libellés déjà présents) ; on annonce
// le nombre réellement ajouté.
function PrechargementFFTA({ tournoiId }: { tournoiId: number }) {
  const precharger = usePrechargerCategoriesFFTA(tournoiId)

  return (
    <div className="prechargement-ffta">
      <button
        type="button"
        className="bouton--discret"
        disabled={precharger.isPending}
        onClick={() => precharger.mutate()}
      >
        {precharger.isPending ? 'Pré-chargement…' : 'Pré-charger les catégories FFTA salle (18 m)'}
      </button>
      {precharger.isSuccess && (
        <p className="carte__etat" role="status">
          {messageResultatFFTA(precharger.data.length)}
        </p>
      )}
      <MessageErreur erreur={precharger.error} />
    </div>
  )
}

function messageResultatFFTA(nombreAjoutees: number): string {
  if (nombreAjoutees === 0) return 'Les catégories FFTA sont déjà présentes.'
  if (nombreAjoutees === 1) return '1 catégorie FFTA ajoutée.'
  return `${nombreAjoutees} catégories FFTA ajoutées.`
}

function LigneCategorie({
  tournoiId,
  categorie,
  blasons,
}: {
  tournoiId: number
  categorie: Categorie
  blasons: Blason[]
}) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerCategorie(tournoiId)

  if (edition) {
    return (
      <li>
        <FormulaireCategorie
          tournoiId={tournoiId}
          categorie={categorie}
          blasons={blasons}
          onTermine={() => setEdition(false)}
        />
      </li>
    )
  }

  return (
    <li className="categorie">
      <div className="categorie__ligne">
        <span className="categorie__libelle">{categorie.libelle}</span>
        <span className="categorie__attributs">{decrire(categorie, blasons)}</span>
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

// Concatène les attributs facultatifs d'une catégorie pour l'affichage (arme · âge · sexe · blason).
function decrire(categorie: Categorie, blasons: Blason[]): string {
  const nomBlason = blasons.find((blason) => blason.id === categorie.blason_id)?.nom ?? null
  const parties = [
    categorie.arme,
    categorie.tranche_age,
    categorie.sexe ? LIBELLE_SEXE[categorie.sexe] : null,
    nomBlason ? `blason ${nomBlason}` : null,
  ].filter((partie): partie is string => partie !== null)
  return parties.join(' · ')
}

// Formulaire partagé création / édition : sans `categorie` il crée, avec il édite.
function FormulaireCategorie({
  tournoiId,
  categorie,
  blasons,
  onTermine,
}: {
  tournoiId: number
  categorie?: Categorie
  blasons: Blason[]
  onTermine?: () => void
}) {
  const enEdition = categorie !== undefined
  const [libelle, setLibelle] = useState(categorie?.libelle ?? '')
  const [arme, setArme] = useState(categorie?.arme ?? '')
  const [trancheAge, setTrancheAge] = useState(categorie?.tranche_age ?? '')
  const [sexe, setSexe] = useState<SexeCategorie | ''>(categorie?.sexe ?? '')
  // Blason par défaut (E01US006) : '' = aucun ; sinon l'identifiant du blason (chaîne dans le
  // <select>, reconverti en nombre à la soumission).
  const [blasonId, setBlasonId] = useState<string>(
    categorie?.blason_id != null ? String(categorie.blason_id) : '',
  )

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
      blason_id: blasonId === '' ? null : Number(blasonId),
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
          setBlasonId('')
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
        <select
          className="formulaire__champ"
          value={blasonId}
          onChange={(e) => setBlasonId(e.target.value)}
          aria-label="Blason par défaut de la catégorie"
        >
          <option value="">Blason par défaut (facultatif)</option>
          {blasons.map((blason) => (
            <option key={blason.id} value={String(blason.id)}>
              {blason.nom}
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
