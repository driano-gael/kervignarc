// Gestion des catégories d'un tournoi (E01US003) — réservée à l'admin.
//
// Tableau, création, édition depuis la ligne (libellé, arme, tranches d'âge, sexe ; E00US016) et
// suppression à confirmation.
// L'arme est en **texte libre** ; les **tranches d'âge** sont une sélection multiple parmi les huit
// tranches FFTA (E01US013 — arc nu « U18 » = U15 + U18). ⚠️ **Le bouton de pré-chargement FFTA a
// quitté cet écran** avec E01US023 : le référentiel alimente la bibliothèque du club, et un tournoi
// en reçoit une copie. Les fiches de recette ont été mises à jour en conséquence.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Blason } from '../blasons/api'
import { useBlasons } from '../blasons/hooks'
import type { Categorie, ModifierCategorie, SexeCategorie, TrancheAge } from './api'
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

// Les huit tranches d'âge FFTA (E01US013), dans l'ordre d'âge croissant. « Scratch » n'y figure
// pas : c'est un **libellé** de regroupement arc nu, pas une tranche.
const TRANCHES_AGE: TrancheAge[] = ['U11', 'U13', 'U15', 'U18', 'U21', 'S1', 'S2', 'S3']

// Hauteur du centre par défaut (FFTA salle 18 m) — miroir de `HAUTEUR_CENTRE_DEFAUT` du domaine.
const HAUTEUR_CENTRE_DEFAUT = 130

// Analyse la saisie de la hauteur : un entier strictement positif (cm). Une valeur vide, non
// entière ou ≤ 0 renvoie `'invalide'` pour bloquer l'envoi (évite un 400 assuré). Le domaine reste
// l'autorité (revalidation à la frontière) ; on ne borne pas par le haut (pas de plafond métier).
function analyserHauteur(saisie: string): number | 'invalide' {
  const texte = saisie.trim()
  if (!/^\d+$/.test(texte)) return 'invalide'
  const valeur = Number(texte)
  return valeur >= 1 ? valeur : 'invalide'
}

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
      <FormulaireCategorie tournoiId={tournoiId} blasons={listeBlasons} />
      {categories.isError && <MessageErreur erreur={categories.error} />}
      {categories.data && categories.data.length > 0 && (
        <div className="table-defilement">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Libellé</th>
                <th scope="col">Arme</th>
                <th scope="col">Tranches d’âge</th>
                <th scope="col">Sexe</th>
                <th scope="col">Blason par défaut</th>
                <th scope="col">Centre</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            {categories.data.map((categorie) => (
              <LigneCategorie
                key={categorie.id}
                tournoiId={tournoiId}
                categorie={categorie}
                blasons={listeBlasons}
              />
            ))}
          </table>
        </div>
      )}
    </section>
  )
}

// Le pré-chargement FFTA **par tournoi** (E01US004) a quitté cet écran avec E01US023 : le
// référentiel alimente désormais la **bibliothèque du club**, une fois pour toutes. Garder les deux
// boutons côte à côte mettait deux chemins concurrents sur le même écran, et celui-ci créait des
// briques fédérales marquées « création du club » — ce qui salit la liste séparée demandée par le
// commanditaire. ⚠️ L'endpoint `precharger-ffta` **reste** : le jeu d'essai (E15US001) s'en sert
// côté serveur pour peupler un tournoi sans passer par l'atelier.

// Les sept colonnes du tableau — la largeur d'une ligne de détail ou du formulaire d'édition.
const COLONNES = 7
const VIDE = '—'

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

  // Un `<tbody>` par catégorie : la ligne et son erreur de suppression se tiennent ensemble.
  if (edition) {
    return (
      <tbody>
        <tr>
          <td colSpan={COLONNES}>
            <FormulaireCategorie
              tournoiId={tournoiId}
              categorie={categorie}
              blasons={blasons}
              onTermine={() => setEdition(false)}
            />
          </td>
        </tr>
      </tbody>
    )
  }

  const nomBlason = blasons.find((blason) => blason.id === categorie.blason_id)?.nom
  return (
    <tbody>
      <tr>
        <td className="categorie__libelle">{categorie.libelle}</td>
        <td>{categorie.arme ?? VIDE}</td>
        <td>{categorie.ages.length > 0 ? categorie.ages.join(', ') : VIDE}</td>
        <td>{categorie.sexe ? LIBELLE_SEXE[categorie.sexe] : VIDE}</td>
        {/* « — » dit « aucun blason » : jamais pendant que la liste des blasons se charge. */}
        <td>{categorie.blason_id === null ? VIDE : (nomBlason ?? '…')}</td>
        <td>{categorie.hauteur_cm} cm</td>
        <td>
          <span className="categorie__actions">
            <button
              type="button"
              className="bouton--discret"
              aria-label={`Éditer ${categorie.libelle}`}
              onClick={() => setEdition(true)}
            >
              Éditer
            </button>
            {confirmationSuppression ? (
              <>
                <button
                  type="button"
                  className="bouton--danger"
                  disabled={supprimer.isPending}
                  aria-label={`Confirmer la suppression de ${categorie.libelle}`}
                  onClick={() => supprimer.mutate(categorie.id)}
                >
                  Confirmer la suppression
                </button>
                <button
                  type="button"
                  className="bouton--discret"
                  aria-label={`Annuler la suppression de ${categorie.libelle}`}
                  onClick={() => setConfirmationSuppression(false)}
                >
                  Annuler
                </button>
              </>
            ) : (
              <button
                type="button"
                className="bouton--danger"
                aria-label={`Supprimer ${categorie.libelle}`}
                onClick={() => setConfirmationSuppression(true)}
              >
                Supprimer
              </button>
            )}
          </span>
        </td>
      </tr>
      {supprimer.error !== null && (
        <tr>
          <td colSpan={COLONNES}>
            <MessageErreur erreur={supprimer.error} />
          </td>
        </tr>
      )}
    </tbody>
  )
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
  const [ages, setAges] = useState<TrancheAge[]>(categorie?.ages ?? [])
  const [sexe, setSexe] = useState<SexeCategorie | ''>(categorie?.sexe ?? '')
  // Hauteur du centre (E03US001, DETTE-009) : pré-remplie à la valeur courante en édition, sinon au
  // défaut FFTA (130). Toujours envoyée pour lever la dette (cf. `NouvelleCategorie.hauteur_cm`).
  const [hauteur, setHauteur] = useState(String(categorie?.hauteur_cm ?? HAUTEUR_CENTRE_DEFAUT))

  // Coche / décoche une tranche ; l'ordre d'envoi est libre (le backend dédoublonne et remet en
  // ordre d'âge canonique).
  const basculerTranche = (tranche: TrancheAge) =>
    setAges((actuelles) =>
      actuelles.includes(tranche)
        ? actuelles.filter((valeur) => valeur !== tranche)
        : [...actuelles, tranche],
    )
  // Blason par défaut (E01US006) : '' = aucun ; sinon l'identifiant du blason (chaîne dans le
  // <select>, reconverti en nombre à la soumission).
  const [blasonId, setBlasonId] = useState<string>(
    categorie?.blason_id != null ? String(categorie.blason_id) : '',
  )

  const creer = useCreerCategorie(tournoiId)
  const modifier = useModifierCategorie(tournoiId)
  const mutation = enEdition ? modifier : creer

  const hauteurAnalysee = analyserHauteur(hauteur)
  const hauteurInvalide = hauteurAnalysee === 'invalide'
  const soumissionPossible = libelle.trim() !== '' && !hauteurInvalide

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (libelle.trim() === '' || hauteurAnalysee === 'invalide') return
    // Annoté `ModifierCategorie` (tous champs requis) et non `NouvelleCategorie` : le PUT est
    // **total**, et c'est le compilateur qui doit refuser un objet incomplet. `Required<X>` reste
    // assignable à `X`, donc la création s'en accommode — l'annotation la plus stricte des deux
    // sert les deux appels.
    const entree: ModifierCategorie = {
      libelle,
      arme: arme.trim() || null,
      ages,
      sexe: sexe || null,
      blason_id: blasonId === '' ? null : Number(blasonId),
      hauteur_cm: hauteurAnalysee,
    }
    if (enEdition) {
      modifier.mutate({ id: categorie.id, entree }, { onSuccess: onTermine })
    } else {
      // Création : on vide le formulaire pour enchaîner une autre saisie.
      creer.mutate(entree, {
        onSuccess: () => {
          setLibelle('')
          setArme('')
          setAges([])
          setSexe('')
          setBlasonId('')
          setHauteur(String(HAUTEUR_CENTRE_DEFAUT))
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
        <fieldset className="formulaire__champ formulaire__tranches">
          <legend>Tranches d'âge (facultatif — plusieurs possibles)</legend>
          {TRANCHES_AGE.map((tranche) => (
            <label key={tranche} className="formulaire__tranche">
              <input
                type="checkbox"
                checked={ages.includes(tranche)}
                onChange={() => basculerTranche(tranche)}
              />
              {tranche}
            </label>
          ))}
        </fieldset>
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
        <label className="formulaire__libelle">
          Hauteur du centre (cm)
          <input
            className="formulaire__champ"
            inputMode="numeric"
            value={hauteur}
            onChange={(e) => setHauteur(e.target.value)}
            placeholder="ex. 130 — 110 pour les U11"
            aria-label="Hauteur du centre de la cible en centimètres"
          />
          {hauteurInvalide ? (
            <span className="carte__etat carte__etat--erreur" role="alert">
              Hauteur en centimètres attendue : un entier ≥ 1 (ex. 130).
            </span>
          ) : (
            <span className="carte__etat">
              Pilote la contrainte « une butte, une seule hauteur » au placement.
            </span>
          )}
        </label>
        <div className="formulaire__actions">
          <button type="submit" disabled={mutation.isPending || !soumissionPossible}>
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
