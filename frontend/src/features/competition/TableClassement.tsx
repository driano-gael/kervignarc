// Tableau du classement de qualification (E06US001). Une ligne par archer : rang **de catégorie** et
// rang **scratch** (global), identité, catégorie, cible, total, et le décompte de **10** et de **9**
// qui rend le départage FFTA lisible (à total égal, plus de 10 puis de 9 — `referentiel-ffta` §8.1).
// Il se rafraîchit tout seul à chaque saisie (invalidation via le flux temps réel).
//
// Surface de **lecture** : le classement sert à connaître les positions. Le placement inline reste
// offert à l'admin (colonne « Placer ») ; la saisie des scores, elle, se fait sur l'écran de saisie
// dédié (E04US002) — l'ancien bouton « Marquer » du walking skeleton écrivait un score que le
// classement ne lit plus (il dérive des séries de saisie), il a donc été retiré.
//
// Le club encore inconnu y est signalé (E02US002, ADR-0014) : le classement est la surface qu'on
// regarde toute la journée, c'est là que l'anomalie se remarque ; l'écran d'admin la répare.

import { type ReactElement, useState } from 'react'
import { EnteteDePage } from '../../shared/ui/EnteteDePage'
import {
  type ReglagePages,
  nombreDePages,
  pageCourante,
  trancheDePage,
  useSecondesDAffichage,
} from '../../shared/ui/pagination'
import { useDeroule } from '../suivi/deroule'
import type { LigneClassement } from './api'
import { estExAequo, totauxExAequo } from './departage'
import { usePlacerArcher } from './hooks'

interface TableClassementProps {
  tournoiId: number
  lignes: LigneClassement[]
  /**
   * La liste **complète**, quand `lignes` en est un sous-ensemble affiché. Sert au seul calcul des
   * ex æquo. Par défaut : `lignes` (les deux se confondent hors centrage).
   *
   * ⚠️ **Ne pas confondre la source du calcul et la source de l'affichage** (correctif de revue,
   * E16US004). `totauxExAequo` cherche les totaux qui apparaissent **plusieurs fois** : le lui
   * donner déjà filtré fait disparaître l'égalité en même temps que l'archer avec qui elle
   * existait. Centré sur un seul archer, un 542 à égalité avec un autre 542 non suivi se
   * présentait comme un rang acquis — alors qu'il tient à un départage au nombre de 10, voire à
   * un barrage à venir.
   */
  lignesCompletes?: LigneClassement[]
  admin: boolean
  /**
   * Combien de lignes de tête restent **toujours visibles** pendant que le reste défile (A16 :
   * *« les x premiers sont toujours affichés, mais le dessous du tableau a un défilé jusqu'à n »*).
   *
   * `0` = pas de séparation, le tableau se comporte comme avant. La valeur est un **paramètre** et
   * non une constante parce que « x » n'a pas la même valeur partout : trois sur un écran de salle
   * (P07 : *« ok pour les 3 premiers toujours visible »*), davantage sur un PC d'organisation où
   * l'on suit le haut d'une catégorie.
   */
  teteFigee?: number
  /**
   * Déplie le **détail des flèches** d'un archer au clic sur sa ligne (E16US004).
   *
   * P03 posait la question en toutes lettres — *« le détail des flèches des autres »* — et la
   * réponse est *« oui »*. Rien à ouvrir côté serveur : `GET …/archers/{id}/deroule` est **déjà**
   * public et anonyme pour n'importe quel archer (ADR-0039, transparence assumée, scores
   * provisoires signalés). Cette prop ne fait donc que câbler une surface existante.
   *
   * Réservé à l'appli publique : l'admin a l'écran de saisie, et l'écran de salle n'a « aucune
   * interaction » (CA E07US004).
   */
  detailFleches?: boolean
  /**
   * Fait **défiler** le reste au lieu de l'enfermer dans un cadre à ascenseur (E16US009, P07 :
   * *« ok pour les 3 premiers toujours visible, mais défilement de tous les autres archers
   * dessous »*).
   *
   * ⚠️ **« Défilement » se lit ici comme une pagination, et c'est un arbitrage** — [ADR-0098]. Un
   * cadre `overflow-y: auto` sur un vidéoprojecteur est un cadre que **personne ne peut faire
   * défiler** : ni souris, ni doigt, « aucune interaction » (CA E07US004). Le commanditaire a par
   * ailleurs accepté la pagination pour les listes de noms projetées dans le même questionnaire
   * (P06, *« 20 s (réglable) par écran de liste de noms est correct »*) : c'est donc la forme qu'il
   * connaît déjà, et elle a l'avantage d'être **déterministe et testable**, là où une animation
   * continue ne se prouve pas.
   *
   * Absent = comportement d'avant, le cadre défilant des surfaces qu'on **manipule** (PC, tablette),
   * où l'ascenseur est le bon geste.
   *
   * [ADR-0098]: ../../../../docs/adr/0098-un-ecran-projete-pagine-au-lieu-de-defiler.md
   */
  pagination?: ReglagePages
}

export function TableClassement({
  tournoiId,
  lignes,
  lignesCompletes,
  admin,
  teteFigee = 0,
  detailFleches = false,
  pagination,
}: TableClassementProps) {
  if (lignes.length === 0) {
    return <p className="carte__etat">Aucun archer inscrit pour l'instant.</p>
  }

  const egalites = totauxExAequo(lignesCompletes ?? lignes)
  // ⚠️ **La règle ne s'annonce que si une ligne VISIBLE la porte** (relevé en revue). Calculer les
  // égalités sur la liste complète corrige le marquage, mais ne doit pas décider seul de l'affichage
  // du paragraphe : centré sur trois archers, `egalites` décrit tout le créneau, donc la mention
  // serait apparue dès qu'une égalité existe **quelque part** — c'est-à-dire en permanence à partir
  // de la mi-journée — sous une table où aucune ligne n'est marquée. C'est très exactement la
  // devinette que `departage.ts` dit vouloir éviter (« encore faut-il montrer sur qui »), et le
  // retour A16 demandait la mention « seulement en cas d'ex æquo ».
  const egaliteVisible = lignes.some((ligne) => estExAequo(ligne, egalites))
  // Séparation seulement si elle **sert** : figer les 5 premiers d'une liste de 5 ne fait
  // qu'ajouter un cadre autour de rien.
  const separer = teteFigee > 0 && lignes.length > teteFigee
  const tete = separer ? lignes.slice(0, teteFigee) : lignes
  const reste = separer ? lignes.slice(teteFigee) : []

  const corps = (source: LigneClassement[]) => (
    <tbody>
      {source.map((ligne) => (
        <LigneArcher
          key={ligne.archer_id}
          tournoiId={tournoiId}
          ligne={ligne}
          admin={admin}
          exAequo={estExAequo(ligne, egalites)}
          detailFleches={detailFleches}
        />
      ))}
    </tbody>
  )

  return (
    <div className={admin ? 'classement classement--admin' : 'classement'}>
      {/* La tête est enveloppée pour **réserver la gouttière d'ascenseur** du cadre défilant : sans
          conteneur, `scrollbar-gutter` n'a aucun effet et les deux tables se décalent. */}
      <div className="classement__tete">
        <table className="table">
          <Colonnes admin={admin} />
          <thead>
            <EnTetes admin={admin} />
          </thead>
          {corps(tete)}
        </table>
      </div>

      {/* Le reste, dans son propre cadre défilant. Deux tables et non une seule à lignes
          `position: sticky` : figer des `<tr>` demande de connaître la hauteur de chaque ligne pour
          calculer leur `top`, or une ligne peut grandir (badge « Club inconnu », nom qui passe à la
          ligne) — le calage aurait été juste jusqu'au premier cas réel. `table-layout: fixed` et un
          `<colgroup>` **partagé** (cf. `Colonnes`) garantissent l'alignement des colonnes entre les
          deux tables, sans mesure ni JavaScript. */}
      {separer && pagination !== undefined && (
        <ResteProjete lignes={reste} pagination={pagination} admin={admin} corps={corps} />
      )}

      {separer && pagination === undefined && (
        <div className="classement__defilement">
          <table className="table">
            <Colonnes admin={admin} />
            {/* En-têtes **répétés et masqués visuellement** : sans eux, toutes les lignes hors de la
                tête figée perdaient l'association `scope="col"` — un lecteur d'écran annonçait des
                nombres sans dire de quelle colonne (revue du 05/08/2026). `sr-only` existe déjà dans
                la feuille du projet. */}
            <thead className="sr-only">
              <EnTetes admin={admin} />
            </thead>
            {corps(reste)}
          </table>
        </div>
      )}

      {/* **La règle de départage, seulement en cas d'ex æquo** (A16). En permanence, elle explique
          une règle qui ne s'applique pas — et un écran qui explique en continu finit par ne plus
          être lu. Les lignes concernées sont marquées : dire « il y a des ex æquo » sans dire
          lesquels serait une devinette. */}
      {egaliteVisible && (
        <p className="classement__departage" role="note">
          Ex æquo signalés : à total égal, le plus grand nombre de <strong>10</strong> départage,
          puis le nombre de <strong>9</strong> (règle FFTA).
        </p>
      )}
    </div>
  )
}

/** Le nombre de colonnes **de lecture** (hors « Placer », réservée à l'admin).
 *
 * Troisième domicile de ce compte, et le seul qui ne se voie pas : `EnTetes` et `Colonnes` cassent
 * le rendu ou le typage quand ils divergent, un `colSpan` faux se contente de laisser une case vide
 * en bout de ligne de détail. La constante ne supprime pas la duplication — elle la rend nommée, ce
 * qui suffit ici (correctif de revue, sans pattern : les trois listes restent côte à côte). */
const NB_COLONNES_LECTURE = 8

/** Combien de **noms** de liste projetée valent une **ligne** de classement.
 *
 * ⚠️ **Ce 3 n'est pas un goût : c'est `columns: 3` dans `features/salle/salle.css`.** Le réglage
 * d'écran compte des noms tels que la page d'affectations les dispose — sur trois colonnes ; le
 * classement est un tableau mono-colonne. Changer la règle CSS oblige à changer ce nombre, et rien
 * ici ne peut le signaler. Décision : ADR-0098 §5. */
const NOMS_PAR_LIGNE_PROJETEE = 3

/** Le plafond de lignes d'une page projetée, **quel que soit le réglage**.
 *
 * ⚠️ **Calculé depuis le CSS, jamais mesuré** — `DETTE-086` porte le décompte et l'incertitude. Ce
 * que le plafond garantit n'est pas la justesse de la valeur mais la **direction de l'erreur** :
 * trop bas, on fait plus de pages et tout finit par passer ; trop haut, le bas de page n'est
 * **jamais montré** (`.classement__pages` n'a aucun ascenseur — ADR-0098 §3).
 *
 * ⚠️ **Effet de bord** : au-delà de `LIGNES_PROJETEES_MAX * NOMS_PAR_LIGNE_PROJETEE` noms réglés, le
 * classement ne réagit plus au réglage — l'aide de l'écran d'admin le dit à l'organisateur, un
 * cadran bloqué ressemblant à une panne. */
const LIGNES_PROJETEES_MAX = 9

/** Le reste du classement **projeté**, page après page (E16US009).
 *
 * Distinct du cadre défilant, et rendu par un composant à part pour une raison mécanique : il tient
 * un minuteur (`useSecondesDAffichage`), et `TableClassement` est monté sur trois surfaces dont deux
 * n'ont rien à faire d'une horloge qui bat à la seconde. Un hook appelé en tête du composant parent
 * aurait fait battre l'appli publique et l'écran d'admin pour rien.
 *
 * ⚠️ **La clé du cumul est propre à cette vue.** Le compteur de `useSecondesDAffichage` est indexé
 * depuis cette US : partagé avec les affectations, il faisait avancer les pages du classement
 * pendant que l'écran montrait autre chose.
 */
function ResteProjete({
  lignes,
  pagination,
  admin,
  corps,
}: {
  lignes: LigneClassement[]
  pagination: ReglagePages
  admin: boolean
  corps: (source: LigneClassement[]) => ReactElement
}) {
  const secondes = useSecondesDAffichage('classement')
  // Le réglage compte des noms sur trois colonnes ; ici chaque archer prend une ligne pleine
  // largeur. Sans cette conversion, le bas de chaque page tomberait sous le bord de l'image — et
  // le plafond tient le reste, que le ratio seul ne couvre pas (cf. les deux constantes).
  const lignesParPage = Math.min(
    Math.max(1, Math.ceil(pagination.noms_par_page / NOMS_PAR_LIGNE_PROJETEE)),
    LIGNES_PROJETEES_MAX,
  )
  const total = nombreDePages(lignes.length, lignesParPage)
  const index = pageCourante(total, secondes, pagination.cadence_page_s)
  const page = trancheDePage(lignes, index, lignesParPage)
  // Le râteau se calcule sur les **noms**, comme pour les affectations : c'est lui qui répond à
  // « mon nom est-il sur cette page ». Le classement est trié par rang, pas par nom — le râteau
  // n'est donc pas un intervalle alphabétique ici, et l'afficher tromperait. On ne le passe pas.
  return (
    <div className="classement__pages">
      <EnteteDePage numero={index + 1} total={total} titre="Suite du classement" rateau={null} />
      <table className="table">
        <Colonnes admin={admin} />
        {/* En-têtes **répétés et masqués visuellement**, même raison que le cadre défilant : sans
            eux, les lignes hors de la tête figée perdent l'association `scope="col"`. */}
        <thead className="sr-only">
          <EnTetes admin={admin} />
        </thead>
        {corps(page)}
      </table>
    </div>
  )
}

/** La rangée d'en-têtes, **partagée** par les deux tables — visible en tête, masquée (mais lue) dans
 * la table défilante. Un seul point de vérité : ajouter une colonne sans toucher les deux endroits
 * ne peut plus décaler l'une par rapport à l'autre. ⚠️ Toute colonne ajoutée ici se compte aussi
 * dans `NB_COLONNES_LECTURE` et se dessine dans `Colonnes`. */
function EnTetes({ admin }: { admin: boolean }) {
  return (
    <tr>
      <th scope="col">Rang cat.</th>
      <th scope="col">Scratch</th>
      <th scope="col">Archer</th>
      <th scope="col">Catégorie</th>
      <th scope="col">Cible</th>
      <th scope="col">Total</th>
      <th scope="col" title="Nombre de 10 (départage FFTA)">
        10
      </th>
      <th scope="col" title="Nombre de 9 (départage FFTA)">
        9
      </th>
      {admin && <th scope="col">Placer</th>}
    </tr>
  )
}

/** Le `<colgroup>` **partagé** par la table de tête et la table défilante — c'est lui qui fait que
 * les colonnes restent alignées entre les deux, sans mesurer quoi que ce soit au rendu. */
function Colonnes({ admin }: { admin: boolean }) {
  return (
    <colgroup>
      <col className="classement__col--rang" />
      <col className="classement__col--rang" />
      <col />
      <col className="classement__col--categorie" />
      <col className="classement__col--court" />
      <col className="classement__col--court" />
      <col className="classement__col--court" />
      <col className="classement__col--court" />
      {admin && <col className="classement__col--action" />}
    </colgroup>
  )
}

function LigneArcher({
  tournoiId,
  ligne,
  admin,
  exAequo,
  detailFleches,
}: {
  tournoiId: number
  ligne: LigneClassement
  admin: boolean
  exAequo: boolean
  detailFleches: boolean
}) {
  const [cible, setCible] = useState('')
  const [detailOuvert, setDetailOuvert] = useState(false)
  const placer = usePlacerArcher(tournoiId)

  const soumettrePlacement = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    const valeur = Number(cible)
    if (!Number.isInteger(valeur) || valeur < 1) return
    placer.mutate({ archerId: ligne.archer_id, cible: valeur }, { onSuccess: () => setCible('') })
  }

  // Nom **et** prénom : depuis E02US002, deux homonymes confirmés (un père et son fils) peuvent
  // coexister — les distinguer à l'écran est le minimum vital.
  const identite = `${ligne.nom} ${ligne.prenom}`

  // Statut forfait (E04US015, ADR-0050) : un abandon est relégué (rang affiché), une DSQ est sortie
  // du classement (rang `null` → « — »). Le badge rend le statut visible ; le score reste affiché
  // (les flèches sont préservées).
  const badgeStatut =
    ligne.statut === 'abandon' ? 'Abandon' : ligne.statut === 'disqualifie' ? 'Disqualifié' : null

  // Deux marquages indépendants, qui peuvent se cumuler sans se contredire : forfait (le score
  // reste, le rang part) et ex æquo (le rang tient à un départage).
  const classes = [
    ligne.statut !== 'en_lice' ? 'table__ligne--forfait' : '',
    exAequo ? 'table__ligne--ex-aequo' : '',
  ]
    .filter((c) => c !== '')
    .join(' ')

  // Le nombre de colonnes, pour que la ligne de détail s'étale sous la table entière. Les colonnes
  // de lecture, plus « Placer » côté admin.
  const nbColonnes = admin ? NB_COLONNES_LECTURE + 1 : NB_COLONNES_LECTURE

  return (
    <>
      <tr className={classes === '' ? undefined : classes}>
        <td>{ligne.rang_categorie ?? '—'}</td>
        <td className="table__scratch">{ligne.rang_scratch ?? '—'}</td>
        <td>
          {detailFleches ? (
            // Un vrai `<button>`, pas un `<tr onClick>` : la ligne doit être atteignable au clavier et
            // annoncée comme dépliable (`aria-expanded`). Une rangée cliquable ne l'est ni l'un ni
            // l'autre, et l'appli publique se consulte aussi au lecteur d'écran.
            <button
              type="button"
              className="lien table__detail-bascule"
              aria-expanded={detailOuvert}
              // `aria-controls` (correctif de revue) : sans lui, le lecteur d'écran annonce
              // « déplié » sans pouvoir dire **quoi** — l'association bouton → région manquait.
              aria-controls={`detail-archer-${ligne.archer_id}`}
              onClick={() => setDetailOuvert((ouvert) => !ouvert)}
            >
              {identite}
            </button>
          ) : (
            identite
          )}
          {badgeStatut && (
            <span className="table__badge-forfait" title="Statut de participation">
              {' '}
              {badgeStatut}
            </span>
          )}
          {ligne.club_id === null && (
            <span
              className="table__anomalie"
              title="Renseignez son club pour compléter l'inscription"
            >
              {' '}
              Club inconnu
            </span>
          )}
        </td>
        <td>{ligne.categorie_libelle}</td>
        <td>{ligne.cible ?? '—'}</td>
        <td className="table__total">{ligne.total}</td>
        <td>{ligne.nb_dix}</td>
        <td>{ligne.nb_neuf}</td>
        {admin && (
          <td>
            <form className="ligne-action" onSubmit={soumettrePlacement}>
              <input
                className="ligne-action__champ"
                type="number"
                min={1}
                value={cible}
                onChange={(e) => setCible(e.target.value)}
                aria-label={`Cible de ${identite}`}
              />
              <button type="submit" disabled={placer.isPending || cible === ''}>
                OK
              </button>
            </form>
          </td>
        )}
      </tr>
      {detailOuvert && (
        <tr className="table__detail" id={`detail-archer-${ligne.archer_id}`}>
          <td colSpan={nbColonnes}>
            <DetailFleches tournoiId={tournoiId} archerId={ligne.archer_id} nom={identite} />
          </td>
        </tr>
      )}
    </>
  )
}

/** Les flèches d'un archer, dépliées sous sa ligne de classement (E16US004, P03).
 *
 * Même source que la carte de suivi (`useDeroule`, E07US009) — un seul appel par archer déplié,
 * mis en cache par React Query et invalidé en direct par la diffusion post-commit : le détail suit
 * la saisie sans qu'on le redemande (P03 : *« en direct, dès que les informations sont
 * disponibles »*).
 *
 * Les volées **non validées** sont montrées, marquées « en attente » : c'est la décision d'ADR-0039,
 * pas une négligence — les taire ferait un total muet pendant tout un tour.
 */
function DetailFleches({
  tournoiId,
  archerId,
  nom,
}: {
  tournoiId: number
  archerId: number
  nom: string
}) {
  const deroule = useDeroule(tournoiId, archerId)
  const volees = deroule.data?.volees ?? []

  // Ce qu'on CONNAÎT d'abord, l'erreur ensuite, le fait négatif en dernier — l'ordre que les revues
  // de `VueSuivi` ont imposé : ne jamais présenter un chargement ou une coupure comme « rien tiré ».
  if (volees.length === 0) {
    if (deroule.isError) {
      return <p className="carte__etat">Détail momentanément indisponible — connexion perdue.</p>
    }
    if (deroule.isPending) return <p className="carte__etat">Chargement…</p>
    return <p className="carte__etat">Aucune flèche saisie pour l’instant.</p>
  }

  return (
    <div className="table__fleches">
      <ul className="suivi-deroule__volees" aria-label={`Flèches de ${nom}`}>
        {volees.map((v) => (
          <li key={v.numero} className="suivi-volee">
            <span className="suivi-volee__num">V{v.numero}</span>
            <span className="suivi-volee__valeurs">{v.valeurs.join(' ')}</span>
            <span className="suivi-volee__points">{v.points}</span>
            <span
              className={
                v.statut === 'valide'
                  ? 'suivi-volee__statut suivi-volee__statut--valide'
                  : 'suivi-volee__statut suivi-volee__statut--attente'
              }
            >
              {v.statut === 'valide' ? 'validé' : 'en attente'}
            </span>
          </li>
        ))}
      </ul>
      <p className="suivi-deroule__cumul">
        Total validé <strong>{deroule.data?.cumul ?? 0}</strong>
      </p>
    </div>
  )
}
