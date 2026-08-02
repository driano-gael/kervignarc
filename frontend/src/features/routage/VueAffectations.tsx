// Vue « toutes les affectations » (E07US008) — le **canal n°2** des quatre canaux de routage (`D-09`).
//
// Un seul composant pour deux surfaces, comme le schéma à braquets d'E01US024 : la **table de
// l'organisation** (dans l'appli publique, interactive) et l'**écran de salle** (projeté, aucune
// interaction). Les dessiner séparément les ferait diverger sur la seule chose qui compte ici — la
// butte annoncée — et c'est précisément l'écart qu'on ne découvre qu'à 18 h, quand deux archers se
// présentent au même endroit.
//
// **`Q-UX2` fermée : les deux tris.** La question ouverte depuis le CDC UX était « trier par **nom**
// (l'archer se cherche) ou par **cible** (l'organisation vérifie) ». Ce n'est pas le même écran, et
// c'est justement pourquoi trancher pour tout le monde était le mauvais réflexe : l'écran projeté,
// qui ne peut rien actionner, garde l'ordre du **pas de tir** (celui du serveur, seul ordre qui se
// lise de loin) ; la table de l'organisation, elle, bascule d'un bouton. Même arbitrage que `Q-UX7`
// en E07US004 — « les deux », quand offrir les deux coûte un bouton.

import { useState } from 'react'
import { LIBELLE_TYPE, type TypePhase } from '../../shared/phases/catalogue'
import type { RoutageArcher } from './api'
import { useAffectations } from './hooks'
import { alerte, detail, encoreEnLice, titre } from './presentation'

type Tri = 'cible' | 'nom'

const nommerType = (type: string) => LIBELLE_TYPE[type as TypePhase] ?? type

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

  // Ordre des états : erreur, puis données, puis chargement, et « rien » en dernier. Un écran de
  // salle qui perd le réseau ne doit **jamais** afficher un pas de tir vide — il serait indiscernable
  // d'un tournoi sans tableau, et personne dans la salle ne peut voir la différence.
  if (affectations.isError) {
    return <p className="carte__etat">Connexion momentanément perdue — mise à jour au retour.</p>
  }
  if (donnees === undefined) {
    return <p className="carte__etat">Chargement…</p>
  }
  if (donnees.phase_id === null) {
    // `phase_id` à `null` ≠ liste vide : c'est la seule chose qui permette de dire « on n'en est pas
    // là » au lieu de laisser croire que le tableau ne route personne.
    return (
      <p className="carte__etat">Pas encore de tableau final — les duels ne sont pas lancés.</p>
    )
  }
  if (donnees.archers.length === 0) {
    return <p className="carte__etat">Aucun duelliste à afficher pour l’instant.</p>
  }

  const enLice = donnees.archers.filter((ligne) => ligne.prochain?.cible != null)
  const autres = donnees.archers.filter((ligne) => ligne.prochain?.cible == null)

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
        <ListeParCible enLice={enLice} />
      )}

      {(!interactif || tri === 'cible') && autres.length > 0 && <ListeSortis lignes={autres} />}
    </div>
  )
}

// Le pas de tir, groupé par butte : la disposition physique de la salle. L'ordre vient du serveur —
// on ne re-trie pas ici, on **groupe** ce qui est déjà trié (cible croissante, puis position A→D).
function ListeParCible({ enLice }: { enLice: RoutageArcher[] }) {
  const parCible = new Map<number, RoutageArcher[]>()
  for (const ligne of enLice) {
    const cible = ligne.prochain?.cible
    if (cible == null) continue
    const groupe = parCible.get(cible)
    if (groupe) groupe.push(ligne)
    else parCible.set(cible, [ligne])
  }

  if (parCible.size === 0) {
    return <p className="carte__etat">Aucune cible attribuée pour l’instant.</p>
  }

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
        {titre(ligne, nommerType)}
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

// Ceux qui n'ont plus de butte : éliminés (avec leur rang acquis) et **repêchés** (avec leur
// destination). Les repêchés d'abord — ils ont encore quelque chose à jouer, et les noyer parmi les
// éliminés serait leur dire de rentrer chez eux.
function ListeSortis({ lignes }: { lignes: RoutageArcher[] }) {
  const ordonnees = [...lignes].sort((a, b) => {
    if (encoreEnLice(a) !== encoreEnLice(b)) return encoreEnLice(a) ? -1 : 1
    return nomComplet(a).localeCompare(nomComplet(b), 'fr')
  })
  return (
    <div className="affectations__sortis">
      <span className="affectations__sortis-titre">Sortis du tableau</span>
      <ul className="affectations__nominatif">
        {ordonnees.map((ligne) => (
          <LigneNominative key={ligne.archer_id} ligne={ligne} />
        ))}
      </ul>
    </div>
  )
}
