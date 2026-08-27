// Vue « toutes les affectations » (E07US008) — le **canal n°2** des quatre canaux de routage.
//
// Un seul composant pour deux surfaces (table de l'organisation, écran de salle) : les dessiner
// séparément les ferait diverger sur la butte annoncée, écart qu'on ne découvre qu'à 18 h.
// **`Q-UX2`, volet « tri » : les deux** — l'écran projeté garde l'ordre du **pas de tir**, la table
// bascule d'un bouton. ✅ Le volet « scannabilité » est fermé par P06 : la surface projetée
// **pagine** (cf. `pagination.ts`). La surface **interactive** ne pagine pas et n'a pas à le faire
// : on y défile à la main.

import { useState } from 'react'
import type { RoutageArcher } from './api'
import { useDeparts } from '../departs/hooks'
import { centrerLignes, type ModeAffichage } from '../../shared/suivis/focus'
import { departDeSalle } from '../salle/rotation'
import { useAffectations } from './hooks'
import { alerte, detail, encoreEnLice, partitionner, posesParCible, titre } from './presentation'
import { EnteteDePage } from '../../shared/ui/EnteteDePage'
import {
  type ReglagePages,
  nombreDePages,
  pageCourante,
  rateauDePage,
  trancheDePage,
  useSecondesDAffichage,
} from '../../shared/ui/pagination'

type Tri = 'cible' | 'nom'

const nomComplet = (ligne: RoutageArcher) => `${ligne.prenom} ${ligne.nom}`.trim()

export function VueAffectations({
  tournoiId,
  interactif = true,
  mode = 'tout',
  suivis = [],
  pagination,
}: {
  tournoiId: number
  interactif?: boolean
  /** Bascule « mes archers / tout » de l'appli publique (E16US004). Par défaut `'tout'` : l'écran
   * de salle et la table de l'organisation ne suivent personne. */
  mode?: ModeAffichage
  /** Les archers suivis sur ce tournoi — n'a de sens qu'avec `mode === 'suivis'`. */
  suivis?: number[]
  /** Le réglage de pages de **cet écran de salle** (E16US009), servi par le serveur. Absent, la
   * séquence retombe sur les défauts du module — c'est-à-dire le comportement d'avant l'US. */
  pagination?: ReglagePages
}) {
  const [tri, setTri] = useState<Tri>('cible')
  // Le pas de tir est celui d'un **créneau** (ADR-0075). Ni l'écran de salle ni la table
  // d'organisation n'ont de sélecteur ici : on prend le créneau qu'on est en train de tirer, par le
  // même helper pur que les vues sœurs.
  const departs = useDeparts(tournoiId)
  const departId = departDeSalle(departs.data ?? [])?.id ?? null
  const affectations = useAffectations(departId)
  const donnees = affectations.data

  // ⚠️ **Les données priment sur l'erreur** (correctif de revue, axe adversarial). React Query
  // conserve le `data` de la dernière lecture réussie pendant un échec : tester `isError` d'abord
  // **jetait un pas de tir valide** au premier clignotement réseau, et laissait l'écran projeté sur
  // un message d'erreur pendant ≥ 20 s alors que l'affichage précédent était encore exact. Un
  // premier jet de ce composant faisait exactement ce que son propre commentaire disait d'éviter.
  // Les vues sœurs de l'écran de salle ne s'y trompent pas (`SuiviDeSalle` rend `data?.blocs ?? []`
  // sans jamais brancher sur `isError`), et le bandeau porte déjà l'indicateur hors-ligne.
  if (donnees === undefined) {
    return (
      <p className="carte__etat">
        {affectations.isError
          ? 'Connexion momentanément perdue — mise à jour au retour.'
          : 'Chargement…'}
      </p>
    )
  }
  if (donnees.phase_id === null) {
    // `phase_id` à `null` ≠ liste vide : c'est la seule chose qui permette de dire « on n'en est pas
    // là » au lieu de laisser croire que le tableau ne route personne.
    return (
      <p className="carte__etat">Pas encore de tableau final — les duels ne sont pas lancés.</p>
    )
  }
  if (donnees.archers.length === 0) {
    // Phase configurée mais tableau **pas constituable** : moins de deux archers en lice dans tout
    // le tournoi. ⚠️ Ce n'est **pas** « le matin avant la qualification » (rectification de la 2ᵉ
    // passe) — `calculer_classement` crée une ligne `EN_LICE` pour *chaque* archer, série ou pas,
    // si bien que le tableau s'ensemence dès deux inscrits. Cas rare, donc, mais il vaut mieux le
    // nommer que rendre un panneau vide : le canal n°1 le dit déjà de son côté (`TABLEAU_ABSENT`).
    return <p className="carte__etat">Tableau final pas encore constitué.</p>
  }

  // Centrage « mes archers » (E16US004) **avant** la partition : c'est bien la même liste qu'on
  // restreint, poses / attente / sortis compris. Filtrer après aurait demandé de le refaire trois
  // fois, et la troisième aurait fini par diverger.
  const archersAffiches = centrerLignes(donnees.archers, mode, suivis)
  if (archersAffiches.length === 0) {
    // Le tableau route du monde, mais aucun de *vos* archers : le dire précisément, sinon la page
    // se lit comme le « Tableau final pas encore constitué » juste au-dessus, qui est faux ici.
    return (
      <p className="carte__etat">
        Aucun des archers que vous suivez n’est affecté sur ce tableau. Passez à « Tout le tournoi »
        pour voir le pas de tir complet.
      </p>
    )
  }

  // La partition vit dans `presentation.ts` — c'est elle qui portait le bloquant de la revue, et
  // la laisser ici la privait de tout test (remarque de la 2ᵉ passe). Le composant ne fait plus que
  // du rendu.
  const { poses, attente, sortis } = partitionner(archersAffiches)

  // Le pas de tir garde ses **buttes entières, adversaire compris** — même raison que ci-dessus :
  // la règle vit dans `presentation.ts` (`posesParCible`), où elle est testée.
  const posesDuPasDeTir = posesParCible(poses, donnees.archers, mode === 'suivis')

  return (
    <div className="affectations">
      {interactif && (
        <div className="affectations__tri" role="group" aria-label="Trier les affectations">
          <button
            type="button"
            className={tri === 'cible' ? 'onglet onglet--actif' : 'onglet'}
            aria-pressed={tri === 'cible'}
            onClick={() => setTri('cible')}
          >
            Par cible
          </button>
          <button
            type="button"
            className={tri === 'nom' ? 'onglet onglet--actif' : 'onglet'}
            aria-pressed={tri === 'nom'}
            onClick={() => setTri('nom')}
          >
            Par nom
          </button>
        </div>
      )}

      {/* L'écran projeté ne peut rien actionner : il ne choisit donc pas son tri, il **cycle**
          (P06). `interactif` fait plus que masquer deux boutons — il change la nature de la vue. */}
      {!interactif ? (
        <SalleParPages poses={poses} tous={archersAffiches} pagination={pagination} />
      ) : tri === 'nom' ? (
        <ListeParNom lignes={archersAffiches} />
      ) : (
        <>
          <ListeParCible poses={posesDuPasDeTir} suivis={mode === 'suivis' ? suivis : []} />
          {/* Encore en lice, sans butte attribuée. Ni dans le pas de tir (ils n'ont pas de cible),
              ni parmi les sortis (ils n'ont rien perdu) : leur propre section, sinon l'écran ment
              dans un sens ou dans l'autre. Titre **neutre** — le groupe rassemble deux attentes que
              le serveur distingue (tour ≥ 2 / plan non matérialisé au tour 1) et chaque ligne porte
              déjà le `manque` exact ; un titre qui n'en nomme qu'une contredirait ses propres
              lignes dans l'autre cas (remarque de la 2ᵉ passe). */}
          {attente.length > 0 && (
            <ListeAnnexe titre="En lice — cible pas encore attribuée" lignes={attente} />
          )}
          {sortis.length > 0 && <ListeAnnexe titre="Sortis du tableau" lignes={sortis} />}
        </>
      )}
    </div>
  )
}

/** La surface **projetée** : une séquence de pages qui tourne toute seule (P06).
 *
 * L'ordre vient de la question 3 — *« d'abord par tour, puis par archer »* : page 0 le **tour en
 * cours** groupé par butte, pages suivantes **tous les archers par nom**, pour que chacun retrouve
 * le sien. ⚠️ Le tour en cours reste **une seule page** même si le pas de tir est long : c'est une
 * vue de situation, pas un annuaire, et la découper ferait perdre la lecture d'ensemble.
 */
function SalleParPages({
  poses,
  tous,
  pagination,
}: {
  poses: RoutageArcher[]
  tous: RoutageArcher[]
  pagination: ReglagePages | undefined
}) {
  // Clé propre à cette vue : le cumul est indexé, sans quoi le classement projeté (qui pagine
  // depuis E16US009) et les affectations feraient avancer les pages l'un de l'autre.
  const secondes = useSecondesDAffichage('affectations')

  const parNom = [...tous].sort((a, b) => nomComplet(a).localeCompare(nomComplet(b), 'fr'))
  const pagesDeNoms = nombreDePages(parNom.length, pagination?.noms_par_page)
  // +1 pour la page « tour en cours », quand il y a effectivement un pas de tir à montrer. Sans
  // butte posée (avant le premier lancement), on ne montre que les noms — une page « tour en cours »
  // vide serait vingt secondes de mur blanc.
  const avecTour = poses.length > 0
  const total = pagesDeNoms + (avecTour ? 1 : 0)
  const index = pageCourante(total, secondes, pagination?.cadence_page_s)

  if (avecTour && index === 0) {
    return (
      <div className="salle-pages">
        <EnteteDePage numero={1} total={total} titre="Tour en cours" rateau={null} />
        <ListeParCible poses={poses} />
      </div>
    )
  }

  const pageNoms = avecTour ? index - 1 : index
  const lignes = trancheDePage(parNom, pageNoms, pagination?.noms_par_page)
  const rateau = rateauDePage(lignes.map(nomComplet))

  return (
    <div className="salle-pages">
      <EnteteDePage numero={index + 1} total={total} titre="Tous les archers" rateau={rateau} />
      <ul className="salle-pages__noms">
        {lignes.map((ligne) => (
          <li key={ligne.archer_id} className="salle-pages__nom">
            <span className="salle-pages__nom-texte">{nomComplet(ligne)}</span>
            <span className="salle-pages__nom-destination">{titre(ligne)}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

// Le pas de tir, groupé par butte : la disposition physique de la salle. L'ordre vient du serveur —
// on ne re-trie pas ici, on **groupe** ce qui est déjà trié (cible croissante, puis position A→D).
function ListeParCible({ poses, suivis = [] }: { poses: RoutageArcher[]; suivis?: number[] }) {
  // ⚠️ **Marquer les archers suivis** (2ᵉ passe de revue). La butte est rendue entière pour que
  // l'adversaire y figure — mais l'interrupteur affiche « Mes archers (3) » au-dessus, et l'écran
  // en montrait alors une douzaine sans dire lesquels étaient les siens : le compte et la liste se
  // contredisaient. La règle empruntée au plan de cibles marche là-bas parce qu'on y cherche une
  // **butte** ; ici on cherche un **nom** dans une liste de noms.
  const estSuivi = new Set(suivis)
  const parCible = new Map<number, RoutageArcher[]>()
  for (const ligne of poses) {
    const cible = ligne.prochain?.cible
    if (cible == null) continue
    const groupe = parCible.get(cible)
    if (groupe) groupe.push(ligne)
    else parCible.set(cible, [ligne])
  }

  // Aucune butte posée : ce n'est pas une anomalie hors du 1ᵉʳ tour (les cibles des tours suivants
  // sont attribuées au lancement). On ne dit donc rien ici — les sections annexes portent
  // l'information, et un message d'absence de plus ferait croire à une panne.
  if (parCible.size === 0) return null

  return (
    <ul className="affectations__cibles">
      {[...parCible].map(([cible, lignes]) => (
        <li key={cible} className="affectations__cible">
          <span className="affectations__cible-num">Cible {cible}</span>
          <ul className="affectations__postes">
            {lignes.map((ligne) => (
              <li
                key={ligne.archer_id}
                className={
                  estSuivi.has(ligne.archer_id)
                    ? 'affectations__poste affectations__poste--suivi'
                    : 'affectations__poste'
                }
              >
                <span className="affectations__position">{ligne.prochain?.position ?? '—'}</span>
                <span className="affectations__nom">{nomComplet(ligne)}</span>
                <span className="affectations__contexte">{ligne.prochain?.libelle}</span>
                {alerte(ligne) !== null && (
                  <span className="affectations__alerte">{alerte(ligne)}</span>
                )}
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}

// Une ligne nominative : le nom, ce qu'il doit retenir, le contexte. Partagée par les deux listes
// nominatives — c'est la même ligne, et la dupliquer la ferait diverger sur la mise en avant du
// « encore en lice », qui est justement ce qui distingue un repêché d'un éliminé.
function LigneNominative({ ligne }: { ligne: RoutageArcher }) {
  return (
    <li className="affectations__ligne">
      <span className="affectations__nom">{nomComplet(ligne)}</span>
      <span
        className={
          encoreEnLice(ligne)
            ? 'affectations__titre affectations__titre--en-lice'
            : 'affectations__titre'
        }
      >
        {titre(ligne)}
      </span>
      {detail(ligne) !== null && <span className="affectations__contexte">{detail(ligne)}</span>}
    </li>
  )
}

// Le tri « l'archer se cherche » : tout le monde, par nom, avec sa destination en clair. On trie une
// **copie** — le tableau vient de React Query, le muter en place corromprait le cache partagé.
function ListeParNom({ lignes }: { lignes: RoutageArcher[] }) {
  const ordonnees = [...lignes].sort((a, b) => nomComplet(a).localeCompare(nomComplet(b), 'fr'))
  return (
    <ul className="affectations__nominatif">
      {ordonnees.map((ligne) => (
        <LigneNominative key={ligne.archer_id} ligne={ligne} />
      ))}
    </ul>
  )
}

// Une section annexe, sous le pas de tir : ceux qui attendent leur cible, ou ceux qui sont sortis.
// Le **titre est passé par l'appelant** parce que c'est exactement là que le composant mentait
// avant la revue — un même bloc intitulé « Sortis du tableau » recevait aussi bien des éliminés que
// des demi-finalistes en attente de butte.
//
// Ceux qui ont encore quelque chose à jouer passent devant : parmi les sortis, un **repêché** n'est
// pas un éliminé, et le noyer dans la liste reviendrait à lui dire de rentrer chez lui.
function ListeAnnexe({ titre: intitule, lignes }: { titre: string; lignes: RoutageArcher[] }) {
  const ordonnees = [...lignes].sort((a, b) => {
    if (encoreEnLice(a) !== encoreEnLice(b)) return encoreEnLice(a) ? -1 : 1
    return nomComplet(a).localeCompare(nomComplet(b), 'fr')
  })
  return (
    <div className="affectations__annexe">
      <span className="affectations__annexe-titre">{intitule}</span>
      <ul className="affectations__nominatif">
        {ordonnees.map((ligne) => (
          <LigneNominative key={ligne.archer_id} ligne={ligne} />
        ))}
      </ul>
    </div>
  )
}
