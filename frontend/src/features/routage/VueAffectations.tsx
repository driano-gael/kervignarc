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
// ⚠️ **Le volet « scannabilité » de `Q-UX2` reste ouvert** (précision de revue) : 200 archers ne
// tiennent pas sur un écran projeté, et rien ici ne pagine ni ne cycle — même régime que la vue
// `classement` depuis E07US004. Ne pas lire cette US comme ayant clos la question entière.

import { useState } from 'react'
import type { RoutageArcher } from './api'
import { useAffectations } from './hooks'
import { alerte, detail, encoreEnLice, titre } from './presentation'

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
    // Phase configurée mais tableau **pas encore constituable** (moins de deux archers en lice) :
    // le cas de la matinée, quand la séquence est composée d'avance. À ne pas confondre avec
    // « personne n'est retenu » — le canal n°1 le dit déjà (`TABLEAU_ABSENT`), celui-ci aussi.
    return <p className="carte__etat">Tableau final pas encore constitué.</p>
  }

  // ⚠️ **On partitionne sur l'ISSUE, jamais sur la cible** (correctif de revue — bloquant relevé par
  // trois axes, deux preuves à l'exécution). Le serveur ne pose une cible **qu'au tour 1** (garde
  // tour-1, `# DETTE-019`) : partitionner sur `prochain?.cible` rangeait donc, dès le tour 2, **tous
  // les archers encore en lice — demi-finalistes compris — sous « Sortis du tableau »**, sur l'appli
  // publique comme sur l'écran projeté, et pour toute la durée du tableau sauf le premier tour.
  // Trois groupes, parce qu'il y a bien trois situations et non deux.
  const poses = donnees.archers.filter(
    (l) => l.issue === 'prochain_duel' && l.prochain?.cible != null,
  )
  const attente = donnees.archers.filter(
    (l) => l.issue === 'prochain_duel' && l.prochain?.cible == null,
  )
  const sortis = donnees.archers.filter((l) => l.issue !== 'prochain_duel')

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

      {/* L'écran projeté ne peut rien actionner : il reste sur l'ordre du serveur, quoi qu'il
          arrive. `interactif` fait donc plus que masquer deux boutons — il fixe la lecture. */}
      {interactif && tri === 'nom' ? (
        <ListeParNom lignes={donnees.archers} />
      ) : (
        <>
          <ListeParCible poses={poses} />
          {/* Encore en lice, mais la cible ne sera posée qu'au lancement du tour. Ni dans le pas de
              tir (ils n'ont pas de butte), ni parmi les sortis (ils n'ont rien perdu) : leur propre
              section, sinon l'écran ment dans un sens ou dans l'autre. */}
          {attente.length > 0 && (
            <ListeAnnexe titre="En lice — cible annoncée au lancement du tour" lignes={attente} />
          )}
          {sortis.length > 0 && <ListeAnnexe titre="Sortis du tableau" lignes={sortis} />}
        </>
      )}
    </div>
  )
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
    <div className="affectations__sortis">
      <span className="affectations__sortis-titre">{intitule}</span>
      <ul className="affectations__nominatif">
        {ordonnees.map((ligne) => (
          <LigneNominative key={ligne.archer_id} ligne={ligne} />
        ))}
      </ul>
    </div>
  )
}
