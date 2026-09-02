// Vue « palmarès » (E06US004) — le **classement final** du tournoi, podiums en tête.
//
// Un seul composant pour trois surfaces, comme `VueAffectations` (E07US008) : l'appli publique
// (interactive), l'écran de salle (projeté, sans interaction) et l'admin — les dessiner séparément
// les ferait diverger sur la seule chose qui compte. **Les podiums d'abord, le classement ensuite**
// : c'est l'ordre de lecture réel, et le PDF suit le même, délibérément — écran et papier doivent
// se comparer d'un coup d'œil.

import { useState } from 'react'
import { useCategories } from '../categories/hooks'
import { centrerLignes, type ModeAffichage } from '../../shared/suivis/focus'
import type { LignePalmares, Podium } from './api'
import { urlPalmaresPdf } from './api'
import { usePalmares } from './hooks'
import { detail, etatPodium, medaille, nomComplet, provenance, rang } from './presentation'

export function VuePalmares({
  tournoiId,
  interactif = true,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  /** Bascule « mes archers / tout » de l'appli publique (E16US004).
   *
   * ⚠️ **Elle ne touche que le classement complet, jamais les podiums.** Un podium amputé de ses
   * médaillés n'est plus un podium — il ne répond pas à « qui a gagné », qui est la seule question
   * que cet écran serve. Le centrage sert à retrouver *ses* archers dans la longue liste, pas à
   * réécrire le résultat du tournoi. */
  mode?: ModeAffichage
  /** Les archers suivis sur ce tournoi — n'a de sens qu'avec `mode === 'suivis'`. */
  suivis?: number[]
  /** `false` pour une surface **sans interaction** — l'écran de salle (E07US004).
   *
   * Un `<select>` et un bouton « Exporter » projetés dans un gymnase sont au mieux inutiles, au
   * pire trompeurs : personne ne peut les actionner. Même parti que `VueClassement`. */
  interactif?: boolean
}) {
  const [categorieId, setCategorieId] = useState<number | undefined>(undefined)
  const filtre = interactif ? categorieId : undefined
  const palmares = usePalmares(tournoiId, filtre)
  const donnees = palmares.data

  return (
    <>
      <h3 className="carte__soustitre">Palmarès</h3>
      {interactif && (
        <div className="palmares-barre">
          <FiltreCategorie
            tournoiId={tournoiId}
            valeur={categorieId}
            surChangement={setCategorieId}
          />
          {/* Un lien, pas un `fetch` : le PDF est servi `inline`, le navigateur sait l'afficher et
              l'imprimer sans blob intermédiaire — et le lien reste utilisable au clic droit. */}
          <a
            className="bouton bouton--secondaire"
            href={urlPalmaresPdf(tournoiId, categorieId)}
            target="_blank"
            rel="noreferrer"
          >
            Exporter en PDF
          </a>
        </div>
      )}
      {/* ⚠️ **Les données priment sur l'erreur** : React Query conserve le `data` de la dernière
          lecture réussie pendant un échec. Tester l'erreur d'abord jetterait un palmarès valide au
          premier clignotement réseau et laisserait l'écran projeté sur un message d'erreur. Même
          correctif que celui qu'a subi `VueAffectations` en revue d'E07US008. */}
      {donnees === undefined ? (
        <p className="carte__etat">
          {palmares.isError
            ? 'Connexion momentanément perdue — mise à jour au retour.'
            : 'Chargement…'}
        </p>
      ) : /* ⚠️ **Le serveur le dit, on ne le déduit pas.** Quatre gardes successives ont tenté
             d'inférer « ce tournoi est-il classé ? » de `lignes` (filtrées) puis de `podiums` (que
             le réglage vide à bon droit quand aucune portée n'est cochée) : quatre fois fausses,
             dans un coin différent. Le vide du FILTRE, lui, est nommé par `ClassementFinal`. */
      donnees.classement_vide ? (
        <p className="carte__etat">Aucun archer classé pour l'instant.</p>
      ) : (
        <>
          {donnees.podiums.map((podium) => (
            <BlocPodium
              key={`${podium.portee}-${podium.cle ?? 'scratch'}`}
              podium={podium}
              profondeur={donnees.profondeur_podium}
            />
          ))}
          <ClassementFinal lignes={centrerLignes(donnees.lignes, mode, suivis)} mode={mode} />
        </>
      )}
    </>
  )
}

/** Le podium d'une catégorie — ou ce qui en tient lieu tant que les finales ne sont pas tirées.
 *
 * On affiche le bloc **même vide** : sur un écran projeté, une catégorie qui disparaît se lit comme
 * une catégorie sans archers, alors qu'elle est simplement en cours. Le dire est le parti `P-3`
 * (« ce qui n'est pas encore connu est nommé ») qu'E07US008 a posé pour le routage.
 */
function BlocPodium({
  podium,
  profondeur,
}: {
  /** ⚠️ L'effectif du groupe et son attente sont **portés par le bloc** (E16US014), jamais
   * recalculés sur les lignes affichées : celles-ci sont filtrées, le bloc ne l'est pas. */
  podium: Podium
  /** Les places que ce tournoi récompense (E16US014) — borne le seuil de « complet ». */
  profondeur: number
}) {
  const etat = etatPodium(podium, profondeur)
  return (
    <section className="palmares-podium" aria-label={`Podium ${podium.libelle}`}>
      <h4 className="palmares-section">{podium.libelle}</h4>
      {etat && <p className="carte__etat">{etat}</p>}
      {podium.places.length > 0 && (
        <ol className="palmares-podium__places">
          {podium.places.map((place) => (
            <li key={place.ligne.archer_id} className="palmares-podium__place">
              {/* Le rang du bloc, jamais un des trois couples de bornes de la ligne : c'est le
                  serveur qui sait lequel s'applique à cette portée. */}
              <span className="palmares-podium__rang">{rang(place.rang, place.rang)}</span>
              <span className="palmares-podium__nom">{nomComplet(place.ligne)}</span>
              {medaille(place.rang) && (
                <span className="palmares-podium__medaille">
                  {medaille(place.rang)}
                  {provenance(place.ligne) && ` · ${provenance(place.ligne)}`}
                </span>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

/** Le classement final sous les podiums — entier, ou centré sur les archers suivis (E16US004).
 *
 * La table vide n'est **pas** rendue : un `<thead>` seul sous un titre « Mes archers » se lit comme
 * une panne. On nomme le cas — un archer suivi peut n'être dans aucun tableau (sorti en
 * qualification), ou dans une catégorie filtrée juste au-dessus.
 */
function ClassementFinal({ lignes, mode }: { lignes: LignePalmares[]; mode: ModeAffichage }) {
  return (
    <>
      <h4 className="palmares-section">
        {mode === 'suivis' ? 'Mes archers' : 'Classement complet'}
      </h4>
      {lignes.length === 0 ? (
        <p className="carte__etat">
          {/* Cause non nommée (correctif de revue) : le filtre par catégorie de cet écran vide la
              liste tout aussi souvent que l'interrupteur, et désigner le second envoyait chercher
              au mauvais endroit. Le podium, lui, reste entier au-dessus — il n'est jamais centré. */}
          {mode === 'suivis'
            ? 'Aucun des archers que vous suivez n’apparaît dans cette sélection. Passez à « Tout le tournoi », ou élargissez le filtre.'
            : 'Aucun archer dans cette sélection — élargissez le filtre par catégorie.'}
        </p>
      ) : (
        // Conteneur défilant : la table déborde sur mobile (CA « responsive ») — on la laisse
        // défiler horizontalement plutôt que d'écraser les colonnes.
        <div className="table-defilement">
          <TablePalmares lignes={lignes} />
        </div>
      )}
    </>
  )
}

function TablePalmares({ lignes }: { lignes: LignePalmares[] }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th scope="col">Rang</th>
          <th scope="col">Rang cat.</th>
          <th scope="col">Archer</th>
          <th scope="col">Catégorie</th>
        </tr>
      </thead>
      <tbody>
        {lignes.map((ligne) => {
          const complement = detail(ligne)
          return (
            <tr key={ligne.archer_id}>
              <td>
                {rang(ligne.rang_min, ligne.rang_max)}
                {complement && <span className="palmares-detail"> · {complement}</span>}
              </td>
              <td>{rang(ligne.rang_categorie_min, ligne.rang_categorie_max)}</td>
              <td>{nomComplet(ligne)}</td>
              <td>{ligne.categorie_libelle}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

/** Le filtre par catégorie, **dans son propre composant** — pour que `useCategories` ne soit monté
 * que quand le filtre est réellement rendu (même correctif que `VueClassement` en revue). */
function FiltreCategorie({
  tournoiId,
  valeur,
  surChangement,
}: {
  tournoiId: number
  valeur: number | undefined
  surChangement: (categorieId: number | undefined) => void
}) {
  const categories = useCategories(tournoiId)
  return (
    <label className="classement-filtre">
      Catégorie{' '}
      <select
        value={valeur ?? ''}
        onChange={(e) => surChangement(e.target.value === '' ? undefined : Number(e.target.value))}
      >
        <option value="">Toutes catégories</option>
        {(categories.data ?? []).map((categorie) => (
          <option key={categorie.id} value={categorie.id}>
            {categorie.libelle}
          </option>
        ))}
      </select>
    </label>
  )
}
