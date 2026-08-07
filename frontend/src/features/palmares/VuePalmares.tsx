// Vue « palmarès » (E06US004) — le **classement final** du tournoi, podiums en tête.
//
// Un seul composant pour trois surfaces, comme `VueAffectations` (E07US008) : l'appli publique
// (interactive : filtre + export), l'écran de salle (projeté, aucune interaction) et l'admin. Les
// dessiner séparément les ferait diverger sur la seule chose qui compte — qui a gagné.
//
// **Les podiums d'abord, le classement ensuite** : c'est l'ordre de lecture réel. On cherche
// d'abord qui monte sur la boîte ; le détail des 120 rangs sert après. Le PDF suit le même ordre,
// délibérément — écran et papier doivent se ressembler assez pour qu'on les compare d'un coup d'œil.

import { useState } from 'react'
import { useCategories } from '../categories/hooks'
import { centrerLignes, type ModeAffichage } from '../public/focus'
import type { LignePalmares, PodiumCategorie } from './api'
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
      ) : donnees.lignes.length === 0 ? (
        <p className="carte__etat">Aucun archer classé pour l'instant.</p>
      ) : (
        <>
          {donnees.podiums.map((podium) => (
            <BlocPodium
              key={podium.categorie_id}
              podium={podium}
              effectif={donnees.lignes.filter((l) => l.categorie_id === podium.categorie_id).length}
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
  effectif,
}: {
  podium: PodiumCategorie
  /** Le nombre d'archers de la catégorie — une catégorie de deux a un podium complet
   * à deux noms, et ne doit pas être annoncée « partielle » indéfiniment. */
  effectif: number
}) {
  const etat = etatPodium(podium, effectif)
  return (
    <section className="palmares-podium" aria-label={`Podium ${podium.categorie_libelle}`}>
      <h4 className="palmares-section">{podium.categorie_libelle}</h4>
      {etat && <p className="carte__etat">{etat}</p>}
      {podium.lignes.length > 0 && (
        <ol className="palmares-podium__places">
          {podium.lignes.map((ligne) => (
            <li key={ligne.archer_id} className="palmares-podium__place">
              <span className="palmares-podium__rang">
                {rang(ligne.rang_categorie_min, ligne.rang_categorie_max)}
              </span>
              <span className="palmares-podium__nom">{nomComplet(ligne)}</span>
              {medaille(ligne.rang_categorie_min) && (
                <span className="palmares-podium__medaille">
                  {medaille(ligne.rang_categorie_min)}
                  {provenance(ligne) && ` · ${provenance(ligne)}`}
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
          Aucun des archers que vous suivez n’apparaît au palmarès. Passez à « Tout le tournoi »
          pour voir le classement complet.
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
