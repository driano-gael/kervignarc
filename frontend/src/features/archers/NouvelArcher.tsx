// Création d'un archer (E02US002) — feature extraite de `competition/TrancheVerticale.tsx` lors de
// la coquille admin (E00US015). Ce formulaire était enfoui dans l'écran monolithique (guide §8 :
// « aucune fonction n'est enfouie dans le fichier d'une autre ») ; il rejoint la feature `archers`,
// où vivent déjà la liste et l'édition — la destination « Inscriptions » les présente ensemble.
//
// À ne pas confondre avec `inscriptions/InscriptionsArcher.tsx` (pluriel) : celui-ci **crée** un
// archer, l'autre **inscrit** un archer déjà créé sur des départs (créneaux, E02US009).
//
// Deux asymétries à ne pas « corriger » par mégarde :
//  - la **catégorie est obligatoire** (sans elle, l'archer n'est ni classable ni plaçable) tandis
//    que le **club ne l'est pas** : « Club inconnu » veut dire « pas encore su », jamais « aucun
//    club » — en FFTA tout licencié en a un (ADR-0014). On inscrit quand même, et on le signale ;
//  - un homonyme est **signalé, pas refusé** : le backend rend 409 `homonyme_archer`, l'admin
//    tranche (père et fils portent les mêmes nom, prénom et club). Le second envoi porte la
//    confirmation. C'est le serveur qui arbitre — un simple avertissement d'UI se contournerait.

import { useState } from 'react'
import { useCategories } from '../categories/hooks'
import { useClubs } from '../clubs/hooks'
import { ErreurApi } from '../../shared/api/client'
import { useAjouterArcher } from '../competition/hooks'
import { MessageErreur } from '../../shared/ui/MessageErreur'

export function NouvelArcher({ tournoiId }: { tournoiId: number }) {
  const [nomArcher, setNomArcher] = useState('')
  const [prenomArcher, setPrenomArcher] = useState('')
  const [clubId, setClubId] = useState('')
  const [categorieId, setCategorieId] = useState('')
  const clubs = useClubs()
  const categories = useCategories(tournoiId)
  const ajouter = useAjouterArcher(tournoiId)

  const incomplet = nomArcher.trim() === '' || prenomArcher.trim() === '' || categorieId === ''
  const homonymeSignale =
    ajouter.error instanceof ErreurApi && ajouter.error.code === 'homonyme_archer'

  // Le 409 porte sur **une identité précise** (nom, prénom, club). Dès que l'un des trois change,
  // le signalement ne s'y applique plus : on l'efface, sinon « Inscrire quand même » confirmerait
  // un archer que le serveur n'a jamais examiné — et le doublon que cette US refuse passerait
  // justement par le bouton prévu pour l'autoriser.
  //
  // `reset()` plutôt que de comparer à la clé signalée : comparer exigerait de réimplémenter en TS
  // le repli casse/accents de `domain.club.cle_nom`, soit une 2ᵉ implémentation d'une règle de
  // domaine — précisément ce que `cle_identite` refuse côté backend en réutilisant `cle_nom`.
  // Ici, savoir « est-ce que ça a changé » suffit ; nul besoin de savoir « est-ce la même clé ».
  const surIdentite = (poser: (valeur: string) => void) => (valeur: string) => {
    if (ajouter.error !== null) ajouter.reset()
    poser(valeur)
  }

  const inscrire = (autoriserHomonyme: boolean) => {
    ajouter.mutate(
      {
        nom: nomArcher,
        prenom: prenomArcher,
        categorie_id: Number(categorieId),
        club_id: clubId === '' ? null : Number(clubId),
        autoriser_homonyme: autoriserHomonyme,
      },
      // Ni le club ni la catégorie ne sont réinitialisés : on inscrit souvent plusieurs archers
      // du même club et de la même catégorie à la suite, à la table d'inscription.
      {
        onSuccess: () => {
          setNomArcher('')
          setPrenomArcher('')
        },
      },
    )
  }

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (incomplet) return
    inscrire(false)
  }

  return (
    <>
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nomArcher}
          onChange={(e) => surIdentite(setNomArcher)(e.target.value)}
          placeholder="Nom de l'archer"
          aria-label="Nom de l'archer"
        />
        <input
          className="formulaire__champ"
          value={prenomArcher}
          onChange={(e) => surIdentite(setPrenomArcher)(e.target.value)}
          placeholder="Prénom de l'archer"
          aria-label="Prénom de l'archer"
        />
        <select
          className="formulaire__champ"
          value={categorieId}
          onChange={(e) => setCategorieId(e.target.value)}
          aria-label="Catégorie de l'archer"
        >
          <option value="">Choisir une catégorie…</option>
          {(categories.data ?? []).map((categorie) => (
            <option key={categorie.id} value={categorie.id}>
              {categorie.libelle}
            </option>
          ))}
        </select>
        <select
          className="formulaire__champ"
          value={clubId}
          onChange={(e) => surIdentite(setClubId)(e.target.value)}
          aria-label="Club de l'archer"
        >
          <option value="">Club inconnu</option>
          {(clubs.data ?? []).map((club) => (
            <option key={club.id} value={club.id}>
              {club.nom}
            </option>
          ))}
        </select>
        <button type="submit" disabled={ajouter.isPending || incomplet}>
          Inscrire
        </button>
      </form>
      {/* `isSuccess` et non `data ?? []` : tant que la requête court, `data` est `undefined` et le
          message s'afficherait à tort sur un tournoi qui a bel et bien des catégories. */}
      {categories.isSuccess && categories.data.length === 0 && (
        <p className="carte__etat">
          Aucune catégorie dans ce tournoi : créez-en une avant d'inscrire un archer.
        </p>
      )}
      {/* Rendu **hors** `MessageErreur`, délibérément : ce bloc porte une action et un ton neutre
          (un doublon probable n'est pas une erreur — l'inscription reste possible). C'est pourquoi
          il n'a pas le modificateur `--erreur`. Examiné en E00US013 (factorisation de `MessageErreur`)
          et laissé tel quel : une confirmation à action n'est pas un affichage d'erreur. */}
      {homonymeSignale ? (
        <div className="carte__etat" role="alert">
          <p>{ajouter.error?.message}</p>
          <button
            type="button"
            onClick={() => inscrire(true)}
            disabled={ajouter.isPending || incomplet}
          >
            Inscrire quand même
          </button>
        </div>
      ) : (
        <MessageErreur erreur={ajouter.error} />
      )}
    </>
  )
}
