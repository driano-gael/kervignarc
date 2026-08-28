// Classement de qualification en direct (E06US001) — surface de **lecture** partagée par la
// coquille admin et la consultation publique (E07US001). La prop `admin` n'ajoute que la colonne «
// Placer » ; le reste est identique.
//
// Un filtre par catégorie restreint l'affichage **sans changer les rangs** : le rang scratch reste
// celui du classement complet — on **voit** une catégorie sans perdre la position d'ensemble.
// Extrait de `admin/CoquilleAdmin.tsx` en E07US001 : une vue de lecture n'a pas à vivre dans le
// module d'administration.

import { useState } from 'react'
import { useCategories } from '../categories/hooks'
import { ChoixCreneau } from '../departs/ChoixCreneau'
import { creneauRetenu } from '../departs/libelle'
import { useDeparts } from '../departs/hooks'
import { centrerLignes, type ModeAffichage } from '../../shared/suivis/focus'
import { departDeSalle } from '../salle/rotation'
import type { ReglagePages } from '../../shared/ui/pagination'
import { teteFigee } from './teteFigee'
import { useClassement } from './hooks'
import { DepartageManuel, PanneauBarrages } from './PanneauBarrages'
import { TableClassement } from './TableClassement'

export function VueClassement({
  tournoiId,
  admin,
  filtrable = true,
  mode = 'tout',
  suivis = [],
  detailFleches = false,
  pagination,
}: {
  tournoiId: number
  admin: boolean
  /** `false` pour une surface **sans interaction** — l'écran de salle (E07US004).
   *
   * Un `<select>` projeté dans un gymnase est au mieux inutile, au pire trompeur : personne ne
   * peut l'actionner, et il donne à croire que l'affichage résulte d'un choix. Sans cette prop,
   * l'écran de salle héritait du filtre. ⚠️ Depuis ADR-0075 elle gouverne **aussi** le choix du
   * créneau : interactif on l'offre, projeté on prend celui qu'on est en train de tirer.
   */
  filtrable?: boolean
  /** Bascule « mes archers / tout » de l'appli publique (E16US004). Par défaut `'tout'` : la
   * coquille admin et l'écran de salle n'ont pas de suivis et ne doivent pas en hériter. */
  mode?: ModeAffichage
  /** Les archers suivis sur ce tournoi — n'a de sens qu'avec `mode === 'suivis'`. */
  suivis?: number[]
  /** Ouvre le **détail des flèches** d'une ligne au clic (E16US004, P03 : *« le détail des flèches
   * des autres : oui »*). Réservé à la surface publique : l'admin a son écran de saisie, et la
   * salle n'a « aucune interaction » (CA E07US004). */
  detailFleches?: boolean
  /** Le réglage de pages de **cet écran de salle** (E16US009), servi par le serveur. Sa présence
   * bascule le reste du classement en **pages qui tournent** au lieu d'un cadre à ascenseur.
   * Absent sur les surfaces qu'on manipule, où l'ascenseur est le bon geste. */
  pagination?: ReglagePages
}) {
  const [categorieId, setCategorieId] = useState<number | undefined>(undefined)
  const [choixDepart, setChoixDepart] = useState<number | null>(null)
  const departs = useDeparts(tournoiId)
  const liste = departs.data ?? []
  // **Le départ qu'on tire fait le défaut**, ici comme sur le plan de cibles de salle : en fin de
  // journée, retomber sur `departs[0]` afficherait le classement du matin, clos depuis six heures,
  // sans rien signaler. `departDeSalle` est pur et testé (`salle/rotation.ts`) — le réécrire ici
  // serait la duplication d'invariant que le registre proscrit.
  const departId = creneauRetenu(liste, choixDepart, departDeSalle)
  const classement = useClassement(tournoiId, departId, filtrable ? categorieId : undefined)

  // ⚠️ **Seule la table est centrée sur les suivis.** Les barrages et le départage manuel, plus bas,
  // gardent `classement.data.lignes` **entier** : ce sont des surfaces d'organisation, et leur
  // donner une liste amputée ferait proposer un barrage entre deux archers sur trois.
  const lignesAffichees = centrerLignes(classement.data?.lignes ?? [], mode, suivis)
  // « Aucun de vos archers ici » n'est pas « aucun archer inscrit » : la table dirait le second,
  // qui est faux et fait chercher une panne. ⚠️ `classement.data.lignes.length > 0` : sans lui, un
  // classement **réellement vide** se présentait comme un vide de filtre — le défaut que ce bloc
  // existe pour éviter, retourné contre lui-même. ⚠️ Ce cas est celui d'un départ **sans aucun
  // engagé**, et **non** « le matin avant la première volée » : `calculer_classement` crée une
  // ligne `EN_LICE` pour **chaque** archer, série ou pas. C'est l'erreur que ce coin du domaine
  // inspire.
  const aucunSuiviIci =
    mode === 'suivis' &&
    classement.data !== undefined &&
    classement.data.lignes.length > 0 &&
    lignesAffichees.length === 0

  return (
    <>
      <h3 className="carte__soustitre">Classement en direct</h3>
      {filtrable && (
        <>
          <ChoixCreneau
            departs={liste}
            valeur={departId}
            surChangement={(id) => setChoixDepart(id)}
          />
          <FiltreCategorie
            tournoiId={tournoiId}
            valeur={categorieId}
            surChangement={setCategorieId}
          />
        </>
      )}
      {/* Un tournoi sans créneau n'a aucun classement à montrer — et le dire vaut mieux qu'un
          « Chargement… » perpétuel, qui est ce que rendrait la requête désactivée. */}
      {departs.isSuccess && liste.length === 0 && (
        <p className="carte__etat">Aucun départ n’est encore défini pour ce tournoi.</p>
      )}
      {liste.length > 0 && classement.isPending && <p className="carte__etat">Chargement…</p>}
      {/* DETTE-050 : rendu ad hoc non rallié à `shared/ui/texteErreur` — `error.message` brut. */}
      {classement.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Classement injoignable — {classement.error.message}
        </p>
      )}
      {/* Barrages : surface d'**organisation**, donc admin seulement — le public voit le
          classement, pas les places encore à trancher. Le panneau se replie de lui-même quand il
          n'y a ni égalité signalée ni barrage en cours (aucun seuil réglé = rien à afficher). */}
      {admin && classement.data && departId !== null && (
        <PanneauBarrages
          tournoiId={tournoiId}
          departId={departId}
          egalites={classement.data.egalites_a_departager}
          lignes={classement.data.lignes}
        />
      )}
      {aucunSuiviIci && (
        <p className="carte__etat">
          {/* La cause n'est **pas** nommée (correctif de revue) : le créneau en est une, le filtre
              par catégorie juste au-dessus en est une autre, tout aussi fréquente. Désigner le
              créneau seul envoyait changer de départ quand il fallait élargir la catégorie. */}
          Aucun des archers que vous suivez n’apparaît dans cette sélection. Passez à « Tout le
          tournoi », ou élargissez le filtre.
        </p>
      )}
      {classement.data && !aucunSuiviIci && (
        // Conteneur défilant : à 8 colonnes, la table déborde sur mobile (CA « responsive ») — on la
        // laisse défiler horizontalement plutôt que d'écraser les colonnes.
        <div className="table-defilement">
          {/* `teteFigee` (A16) : huit lignes sur les surfaces qu'on **manipule** — on y suit le
              haut d'une catégorie, pas seulement le podium. ✅ **Trois sur l'écran de salle**
              (P07, E16US009) ; la valeur restait à zéro tant que le défilement n'existait pas,
              sans quoi un classement de 40 archers tombait à 3 lignes — la régression refusée
              le 05/08/2026. */}

          {/* ⚠️ Le lien est **mécanique** : sans `pagination`, la tête figée retombe à zéro,
              donc un appelant qui passerait `filtrable` seul retrouve le classement entier
              d'avant l'US, jamais les 3 lignes seules (ADR-0098). */}
          <TableClassement
            tournoiId={tournoiId}
            lignes={lignesAffichees}
            // Les ex æquo se cherchent sur la liste **entière** : à égalité avec un archer qu'on ne
            // suit pas, le signalement disparaîtrait avec lui (correctif de revue).
            lignesCompletes={classement.data.lignes}
            admin={admin}
            // Centré sur ses archers, la liste est courte : figer une tête de 8 sur 3 lignes
            // n'encadre plus rien (même raison que `separer` dans `TableClassement`).
            teteFigee={teteFigee(filtrable, mode, pagination)}
            pagination={pagination}
            detailFleches={detailFleches}
          />
        </div>
      )}
      {/* Departage manuel (poule, Big Shoot Off) : replie, hors de la carte d'alerte. Ces formats
          n'ont aucun classement calcule qui pourrait signaler leurs ex aequo, donc c'est
          l'organisateur qui designe les tireurs — il lui faut un point d'entree permanent. */}
      {admin && classement.data && departId !== null && (
        <DepartageManuel
          tournoiId={tournoiId}
          departId={departId}
          lignes={classement.data.lignes}
        />
      )}
    </>
  )
}

/** Le filtre par catégorie, **dans son propre composant**.
 *
 * Séparé pour que `useCategories` ne soit monté que quand le filtre est réellement rendu : appelé en
 * tête de `VueClassement`, il faisait interroger `/categories` par l'écran de salle pour un
 * `<select>` qu'il n'affiche jamais (relevé en revue — le même défaut que le hook de suivi corrigé
 * trois fichiers plus loin).
 */
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
