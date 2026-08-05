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
import { useAffectations } from './hooks'
import { alerte, detail, encoreEnLice, partitionner, titre } from './presentation'
import { nombreDePages, pageCourante, rateauDePage, trancheDePage } from './pagination'

type Tri = 'cible' | 'nom'

const nomComplet = (ligne: RoutageArcher) => `${ligne.prenom} ${ligne.nom}`.trim()

export function VueAffectations({
  tournoiId,
  interactif = true,
}: {
  tournoiId: number
  interactif?: boolean
}) {
  const [tri, setTri] = useState<Tri>('cible')
  const affectations = useAffectations(tournoiId)
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

  // La partition vit dans `presentation.ts` — c'est elle qui portait le bloquant de la revue, et
  // la laisser ici la privait de tout test (remarque de la 2ᵉ passe). Le composant ne fait plus que
  // du rendu.
  const { poses, attente, sortis } = partitionner(donnees.archers)

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
        <SalleParPages poses={poses} tous={donnees.archers} />
      ) : tri === 'nom' ? (
        <ListeParNom lignes={donnees.archers} />
      ) : (
        <>
          <ListeParCible poses={poses} />
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
  const secondes = useHorlogeDeSalle()

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

/** L'horloge de la surface projetée, en secondes.
 *
 * Une **horloge** et non un compteur, pour la raison déjà écrite dans `salle/rotation.ts` : les
 * minuteurs d'un onglet en arrière-plan sont bridés, et huit heures de dérive font un écran bloqué
 * sur une page. Jumelle de `useHorlogeLocale` (`EcranSalle`) — 2ᵉ occurrence, donc dupliquée
 * volontairement : la règle du projet attend une 3ᵉ preuve avant tout remède structurel. */
function useHorlogeDeSalle(): number {
  const [secondes, setSecondes] = useState(() => Date.now() / 1000)
  useEffect(() => {
    const battement = window.setInterval(() => setSecondes(Date.now() / 1000), 1000)
    return () => window.clearInterval(battement)
  }, [])
  return secondes
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
