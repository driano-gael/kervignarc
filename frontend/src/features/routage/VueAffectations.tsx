// Vue « toutes les affectations » (E07US008) — le **canal n°2** des quatre canaux de routage (`D-09`).
//
// Un seul composant pour deux surfaces, comme le schéma à braquets d'E01US024 : la **table de
// l'organisation** (dans l'appli publique, interactive) et l'**écran de salle** (projeté, aucune
// interaction). Les dessiner séparément les ferait diverger sur la seule chose qui compte ici — la
// butte annoncée — et c'est précisément l'écart qu'on ne découvre qu'à 18 h, quand deux archers se
// présentent au même endroit.
//
// **`Q-UX2`, volet « tri » : les deux.** La question ouverte depuis le CDC UX était « trier par
// **nom** (l'archer se cherche) ou par **cible** (l'organisation vérifie) ». Ce n'est pas le même
// écran, et c'est justement pourquoi trancher pour tout le monde était le mauvais réflexe : l'écran
// projeté, qui ne peut rien actionner, garde l'ordre du **pas de tir** (celui du serveur, seul ordre
// qui se lise de loin) ; la table de l'organisation, elle, bascule d'un bouton. Même arbitrage que
// `Q-UX7` en E07US004 — « les deux », quand offrir les deux coûte un bouton.
//
// ✅ **Le volet « scannabilité » de `Q-UX2` est fermé** par le retour maquettes du 04/08/2026 (P06).
// L'avertissement qui figurait ici — *« 200 archers ne tiennent pas sur un écran projeté, et rien ici
// ne pagine ni ne cycle »* — a reçu sa réponse : variante A, *« défilement par pages, tri par nom »*,
// *« oui pour le compteur de pages »*, ~20 s par page, et un ordre d'ensemble — *« d'abord par tour,
// puis par archer »*. La surface projetée pagine donc désormais (cf. `pagination.ts` pour les
// règles, et `SalleParPages` plus bas pour la séquence).
//
// La surface **interactive** (table de l'organisation) ne pagine pas et n'a pas à le faire : on y
// défile à la main, et un découpage automatique sous les doigts serait une gêne, pas un service.

import { useEffect, useState } from 'react'
import type { RoutageArcher } from './api'
import { useDeparts } from '../departs/hooks'
import { centrerLignes, type ModeAffichage } from '../../shared/suivis/focus'
import { departDeSalle } from '../salle/rotation'
import { useAffectations } from './hooks'
import { alerte, detail, encoreEnLice, partitionner, titre } from './presentation'
import { nombreDePages, pageCourante, rateauDePage, trancheDePage } from './pagination'

type Tri = 'cible' | 'nom'

const nomComplet = (ligne: RoutageArcher) => `${ligne.prenom} ${ligne.nom}`.trim()

export function VueAffectations({
  tournoiId,
  interactif = true,
  mode = 'tout',
  suivis = [],
}: {
  tournoiId: number
  interactif?: boolean
  /** Bascule « mes archers / tout » de l'appli publique (E16US004). Par défaut `'tout'` : l'écran
   * de salle et la table de l'organisation ne suivent personne. */
  mode?: ModeAffichage
  /** Les archers suivis sur ce tournoi — n'a de sens qu'avec `mode === 'suivis'`. */
  suivis?: number[]
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

  // ⚠️ **Le pas de tir garde ses buttes entières, adversaire compris** (correctif de revue).
  //
  // C'est la règle déjà posée par `focus.centrerCibles` pour le plan de cibles — « on garde la
  // cible entière, voisins compris » — et elle n'avait pas été appliquée ici, où elle compte
  // pourtant davantage : sur un tableau de duels, le voisin de butte **est** l'adversaire. Filtré
  // ligne à ligne, « Cible 7 · B · MARTIN Luc » ne disait plus contre qui Luc tire, alors que
  // l'affichage complet le montre en face de lui — et laissait croire à une butte à un seul tireur.
  //
  // Les sections annexes (attente, sortis) restent, elles, centrées sur les seuls archers suivis :
  // ce sont des listes de personnes, pas une disposition de salle, et personne n'y cherche un
  // vis-à-vis.
  const ciblesSuivies = new Set(
    poses.map((ligne) => ligne.prochain?.cible).filter((cible) => cible != null),
  )
  const posesParCible =
    mode === 'tout'
      ? poses
      : partitionner(donnees.archers).poses.filter(
          (ligne) => ligne.prochain?.cible != null && ciblesSuivies.has(ligne.prochain.cible),
        )

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
        <SalleParPages poses={poses} tous={archersAffiches} />
      ) : tri === 'nom' ? (
        <ListeParNom lignes={archersAffiches} />
      ) : (
        <>
          <ListeParCible poses={posesParCible} />
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

/**
 * La surface **projetée** : une séquence de pages qui tourne toute seule (P06).
 *
 * L'ordre vient de la réponse à la question 3 — *« d'abord par tour, puis par archer »* :
 *
 *   page 0 · **le tour en cours**, groupé par butte — ce que la salle regarde quand un tour part ;
 *   pages 1…n · **tous les archers, par nom** — *« par nom, c'est plus clair »* (question 1), pour
 *              que chacun retrouve le sien même s'il n'est pas concerné par le tour qui se lance.
 *
 * Le tour en cours reste **une seule page** même si le pas de tir est long : c'est une vue de
 * situation, pas un annuaire, et la découper ferait perdre la lecture d'ensemble qu'on vient y
 * chercher. Ce sont les pages nominatives, elles, qui pagineraient sur 200 archers.
 */
function SalleParPages({ poses, tous }: { poses: RoutageArcher[]; tous: RoutageArcher[] }) {
  const secondes = useSecondesDAffichage()

  const parNom = [...tous].sort((a, b) => nomComplet(a).localeCompare(nomComplet(b), 'fr'))
  const pagesDeNoms = nombreDePages(parNom.length)
  // +1 pour la page « tour en cours », quand il y a effectivement un pas de tir à montrer. Sans
  // butte posée (avant le premier lancement), on ne montre que les noms — une page « tour en cours »
  // vide serait vingt secondes de mur blanc.
  const avecTour = poses.length > 0
  const total = pagesDeNoms + (avecTour ? 1 : 0)
  const index = pageCourante(total, secondes)

  if (avecTour && index === 0) {
    return (
      <div className="salle-pages">
        <EnteteDePage numero={1} total={total} titre="Tour en cours" rateau={null} />
        <ListeParCible poses={poses} />
      </div>
    )
  }

  const pageNoms = avecTour ? index - 1 : index
  const lignes = trancheDePage(parNom, pageNoms)
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

/** L'en-tête d'une page projetée : **le compteur et le râteau, en grand** (P06 : *« grossir le
 * compteur de page, il faut qu'il soit visible, de même que les lettres comprises dans le râteau de
 * nom »*). Ce sont les deux seules informations qui servent à quelqu'un debout au fond de la salle :
 * « est-ce que mon nom est sur cette page, et sinon combien de temps j'attends ». */
function EnteteDePage({
  numero,
  total,
  titre: intitule,
  rateau,
}: {
  numero: number
  total: number
  titre: string
  rateau: { debut: string; fin: string } | null
}) {
  return (
    <header className="salle-pages__entete">
      <span className="salle-pages__titre">{intitule}</span>
      {rateau !== null && (
        <span className="salle-pages__rateau">
          {rateau.debut} <span aria-hidden="true">→</span> {rateau.fin}
        </span>
      )}
      {total > 1 && (
        <span className="salle-pages__compteur">
          {numero}
          <span className="salle-pages__compteur-total">/{total}</span>
        </span>
      )}
    </header>
  )
}

/**
 * Temps d'affichage **cumulé de cette vue**, en secondes — pas l'heure du monde.
 *
 * ⚠️ **C'est la correction d'un défaut trouvé en revue adversariale (05/08/2026), et il n'était pas
 * théorique.** La première version dérivait la page de `Date.now()` nu, comme `salle/rotation.ts` le
 * fait pour la rotation des vues. Le raisonnement était faux d'un cran : la rotation, elle, tourne
 * **en continu** ; la vue « affectations », non — elle n'est à l'écran qu'une étape sur N du déroulé.
 * Une page calée sur l'heure absolue n'avance donc que **par sauts**, et quand la période du déroulé
 * et les 20 s tombent juste, certaines pages ne sortent **jamais**. Vérifié en exécutant la
 * fonction : déroulé « affectations 30 s + classement 30 s » et trois pages → la page 2 n'est jamais
 * projetée de la journée. La moitié des archers ne verrait jamais son nom, c'est-à-dire exactement
 * la fonction demandée en P06.
 *
 * On compte donc le temps **pendant lequel la vue est affichée**, cumulé d'un passage à l'autre : la
 * séquence reprend où elle s'était arrêtée, et toutes les pages finissent par sortir quelle que soit
 * la découpe du déroulé.
 *
 * Le cumul vit **au module** et non dans un état React : le composant est démonté à chaque fois que
 * l'écran passe à une autre vue, donc tout état interne serait perdu — c'est précisément ce qu'on
 * cherche à conserver. Une seule surface projetée par onglet, donc pas de collision possible.
 *
 * Reste une **horloge** et non un compteur incrémenté, pour la raison écrite dans `rotation.ts` : un
 * onglet en arrière-plan voit ses minuteurs bridés, et huit heures de dérive figeraient l'écran.
 */
let secondesAffichees = 0

function useSecondesDAffichage(): number {
  const [ecoulees, setEcoulees] = useState(secondesAffichees)
  useEffect(() => {
    const debut = Date.now() / 1000
    const battement = window.setInterval(
      () => setEcoulees(secondesAffichees + (Date.now() / 1000 - debut)),
      1000,
    )
    return () => {
      window.clearInterval(battement)
      secondesAffichees += Date.now() / 1000 - debut
    }
  }, [])
  return ecoulees
}

// Le pas de tir, groupé par butte : la disposition physique de la salle. L'ordre vient du serveur —
// on ne re-trie pas ici, on **groupe** ce qui est déjà trié (cible croissante, puis position A→D).
function ListeParCible({ poses }: { poses: RoutageArcher[] }) {
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
              <li key={ligne.archer_id} className="affectations__poste">
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
