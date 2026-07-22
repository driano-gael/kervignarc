// Recherche d'archer depuis la sidebar admin (E12US006) — le **4ᵉ canal de routage** (`D-09`).
//
// La table de l'organisation tape un nom → l'appli répond **immédiatement** « il tire là » :
// départ, cible, position, pour chaque créneau où l'archer est posé. Le champ est présent **en
// permanence en tête de la sidebar** (`D-19`), quel que soit l'écran admin affiché, et accessible
// **au clavier** (un simple `<input>` + liste). C'est la table d'organisation qui l'utilise, un
// humain — pas de borne en libre-service (`D-10`), donc pas de « retour à l'accueil » comme côté
// public.
//
// **Réutilise la logique pure de la feature publique « suivi »** (`filtrerArchers` / `construireJournee`) :
// c'est le même geste (nom → place), donc une source unique, déjà **testée depuis le CA** dans
// `suivi.test.ts` (recherche tolérante à la casse et aux accents, place = cible/position/départ).
// L'alternative — dupliquer ces fonctions — divergerait ; les remonter dans `shared/` attendra un
// 3ᵉ consommateur (discipline « attendre le 3ᵉ cas » ; `shared/` reste sans dépendance vers `features/`).
//
// **« Prochaine affectation » (tour/duel suivant, `D-09`) séquencée vers EPIC-05** : le moteur de
// phases n'est pas livré (aucun agrégat `Duel`), un archer n'a aujourd'hui que ses créneaux de
// **qualification** — la journée affichée les couvre déjà tous. La ligne « prochaine affectation »
// s'ajoutera quand EPIC-05 livrera, comme la complétude des duels dans E12US005. Rien de perdu,
// seulement séquencé.
//
// **Chargement paresseux** : la sidebar est montée sur *tout* écran admin ; on ne fetche archers /
// départs / plans que lorsqu'un tournoi est courant **et** que l'admin a tapé quelque chose
// (`actif`) — pas de rafale de requêtes sur un écran où personne ne cherche (idiome de
// `useImpactRegeneration`). React Query partage les plans par `clePlan` avec les autres écrans.

import { useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { useArchers } from '../archers/hooks'
import { useDeparts } from '../departs/hooks'
import { getPlanDeCibles, type PlanDeCibles } from '../placement/api'
import { clePlan } from '../placement/hooks'
import { construireJournee, filtrerArchers } from '../suivi/suivi'

// Borne l'affichage : au-delà, on invite à préciser plutôt que de dérouler tout un club dans la
// sidebar (et de risquer de cacher l'archer cherché en silence).
const MAX_RESULTATS = 8

export function RechercheArcher({ tournoiId }: { tournoiId: number | null }) {
  const [requete, setRequete] = useState('')
  // On ne cherche — et ne fetche — qu'avec un tournoi courant ET une requête non vide.
  const actif = requete.trim() !== '' && tournoiId !== null
  // Clé neutre quand aucun tournoi n'est choisi : `enabled=false` empêche tout fetch, la clé `0`
  // n'est jamais peuplée.
  const idActif = tournoiId ?? 0

  const archersQuery = useArchers(idActif, actif)
  const archers = archersQuery.data ?? []
  const departsQuery = useDeparts(idActif, actif)
  const departs = departsQuery.data ?? []

  // Les plans de tous les départs : la source de « où tire l'archer » (autorité du placement,
  // ADR-0033). Fetchés seulement quand `actif`, et partagés par clé avec les écrans placement/suivi.
  const plansResults = useQueries({
    queries: actif
      ? departs.map((d) => ({
          queryKey: clePlan(idActif, d.id),
          queryFn: () => getPlanDeCibles(idActif, d.id),
        }))
      : [],
  })
  const plansParDepart = new Map<number, PlanDeCibles>()
  departs.forEach((d, i) => {
    const data = plansResults[i]?.data
    if (data) plansParDepart.set(d.id, data)
  })

  const correspondances = filtrerArchers(archers, requete)
  const resultats = correspondances.slice(0, MAX_RESULTATS)
  const tropDeResultats = correspondances.length > resultats.length
  const requeteVide = requete.trim() === ''

  // La **liste** (ce que la recherche filtre) et la **place** (départs + plans) sont deux sources
  // distinctes : un plan momentanément indisponible ne doit pas cacher les noms trouvés, seulement
  // dégrader la place de la ligne (leçon de revue de VueSuivi — ne jamais présenter une erreur ou un
  // chargement comme un « aucun archer »).
  const placesEnChargement = departsQuery.isLoading || plansResults.some((r) => r.isLoading)
  const placesEnErreur = departsQuery.isError || plansResults.some((r) => r.isError)

  return (
    <div className="coquille__recherche recherche-archer">
      <label className="formulaire__libelle" htmlFor="recherche-archer">
        Rechercher un archer
      </label>
      <input
        id="recherche-archer"
        className="formulaire__champ"
        value={requete}
        onChange={(e) => setRequete(e.target.value)}
        placeholder="Nom de l’archer…"
        aria-label="Rechercher un archer par son nom"
        autoComplete="off"
      />

      {!requeteVide &&
        // Ordre : tournoi manquant → erreur de liste → résultats → chargement → « aucun » en dernier.
        (tournoiId === null ? (
          <p className="carte__etat">Sélectionnez un tournoi pour rechercher.</p>
        ) : archersQuery.isError ? (
          <p className="carte__etat carte__etat--erreur">Liste momentanément indisponible.</p>
        ) : resultats.length > 0 ? (
          <>
            <ul className="recherche-resultats">
              {resultats.map((a) => (
                <li key={a.id} className="recherche-resultat recherche-resultat--place">
                  <span className="recherche-resultat__nom">
                    {a.prenom} {a.nom}
                  </span>
                  <PlaceArcher
                    journee={construireJournee(a.id, departs, plansParDepart)}
                    enChargement={placesEnChargement}
                    enErreur={placesEnErreur}
                  />
                </li>
              ))}
            </ul>
            {tropDeResultats && <p className="carte__etat">Trop de résultats — précisez le nom.</p>}
          </>
        ) : archersQuery.isLoading ? (
          <p className="carte__etat">Chargement…</p>
        ) : (
          <p className="carte__etat">Aucun archer à ce nom.</p>
        ))}
    </div>
  )
}

// La place d'un archer trouvé : une ligne par créneau où il est posé (départ + horaire → cible /
// position). Vide + plans en cours → « Chargement… » ; vide + plan en erreur → indisponible ; vide
// sinon → réellement « pas encore placé ». On ne confond jamais « pas chargé » et « pas placé ».
function PlaceArcher({
  journee,
  enChargement,
  enErreur,
}: {
  journee: ReturnType<typeof construireJournee>
  enChargement: boolean
  enErreur: boolean
}) {
  if (journee.length > 0) {
    return (
      <ul className="recherche-places">
        {journee.map((l) => (
          <li key={l.departId} className="recherche-place">
            Départ {l.numeroDepart}
            {l.horaire ? ` · ${l.horaire}` : ''} — Cible {l.cible} · Pos. {l.position}
          </li>
        ))}
      </ul>
    )
  }
  if (enChargement)
    return <span className="recherche-place recherche-place--attente">Chargement…</span>
  if (enErreur)
    return <span className="recherche-place recherche-place--attente">Place indisponible.</span>
  return <span className="recherche-place recherche-place--vide">Pas encore placé.</span>
}
