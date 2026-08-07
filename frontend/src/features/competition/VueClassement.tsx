// Classement de qualification en direct (E06US001) — surface de **lecture** partagée par la coquille
// admin (destination « Classement en direct ») et la **consultation publique** (E07US001). La prop
// `admin` n'ajoute que la colonne « Placer » (déléguée à `TableClassement`) ; le reste est identique,
// public ou non.
//
// Un filtre par catégorie restreint l'affichage à une catégorie **sans changer les rangs** : le rang
// scratch (global) reste celui du classement complet — on **voit** une catégorie sans perdre la
// position d'ensemble. Le classement se rafraîchit tout seul via l'invalidation temps réel (E04US009).
//
// Extrait de `admin/CoquilleAdmin.tsx` en E07US001 pour être réutilisable hors de la coquille admin :
// une vue de lecture n'a pas à vivre dans le module d'administration.

import { useState } from 'react'
import { useCategories } from '../categories/hooks'
import { ChoixCreneau } from '../departs/ChoixCreneau'
import { useDeparts } from '../departs/hooks'
import { departDeSalle } from '../salle/rotation'
import { useClassement } from './hooks'
import { DepartageManuel, PanneauBarrages } from './PanneauBarrages'
import { TableClassement } from './TableClassement'

export function VueClassement({
  tournoiId,
  admin,
  filtrable = true,
}: {
  tournoiId: number
  admin: boolean
  /** `false` pour une surface **sans interaction** — l'écran de salle (E07US004).
   *
   * Un `<select>` projeté dans un gymnase est au mieux inutile, au pire trompeur : personne ne peut
   * l'actionner, et il donne à croire que ce qui est affiché résulte d'un choix. Le CA d'E07US004
   * est explicite (« **aucune interaction** »), et la recette le vérifie à l'œil (« rien de
   * cliquable »). Sans cette prop, l'écran de salle héritait du filtre — relevé en revue.
   *
   * ⚠️ Depuis ADR-0075, elle gouverne **aussi** le choix du créneau : un classement appartient à un
   * départ, il faut donc en désigner un. Interactif, on l'offre au choix ; projeté, on prend celui
   * qu'on est en train de tirer (`departDeSalle`), sans rien à cliquer. */
  filtrable?: boolean
}) {
  const [categorieId, setCategorieId] = useState<number | undefined>(undefined)
  const [choixDepart, setChoixDepart] = useState<number | null>(null)
  const departs = useDeparts(tournoiId)
  const liste = departs.data ?? []
  // **Le départ qu'on tire fait le défaut**, ici comme sur le plan de cibles de salle : en fin de
  // journée, retomber sur `departs[0]` afficherait le classement du matin, clos depuis six heures,
  // sans rien signaler. `departDeSalle` est pur et testé (`salle/rotation.ts`) — le réécrire ici
  // serait la duplication d'invariant que le registre proscrit.
  const departId = choixDepart ?? departDeSalle(liste)?.id ?? null
  const classement = useClassement(tournoiId, departId, filtrable ? categorieId : undefined)

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
      {classement.data && (
        // Conteneur défilant : à 8 colonnes, la table déborde sur mobile (CA « responsive ») — on la
        // laisse défiler horizontalement plutôt que d'écraser les colonnes.
        <div className="table-defilement">
          {/* `teteFigee` (A16) : *« les x premiers sont toujours affichés, mais le dessous du tableau
              a un défilé jusqu'à n »*. Huit sur les surfaces qu'on **manipule** : on y suit le haut
              d'une catégorie, pas seulement le podium, et huit lignes tiennent sans écraser le cadre
              défilant.
              ⚠️ **Zéro sur l'écran de salle** (`filtrable === false`), et c'est délibéré. P07 demande
              bien « les 3 premiers toujours visibles, mais **défilement** de tous les autres archers
              dessous » — mais un cadre `overflow-y: auto` sur un vidéoprojecteur est un cadre que
              **personne ne peut faire défiler** : ni souris, ni doigt, « aucune interaction » (CA
              E07US004). Livrer la tête figée sans le défilement automatique aurait réduit un
              classement de 40 archers à 3 lignes — une **régression** de ce que la salle affichait
              avant ce lot (revue du 05/08/2026, axe B). Le défilement automatique est spécifié en
              `E16US009` ; jusque-là, la salle rend le classement entier, comme avant. */}
          <TableClassement
            tournoiId={tournoiId}
            lignes={classement.data.lignes}
            admin={admin}
            teteFigee={filtrable ? 8 : 0}
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
