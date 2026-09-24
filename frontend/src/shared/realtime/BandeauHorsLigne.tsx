// Bandeau hors ligne — **aplat plein, toute la largeur** (planche S09, variante retenue).
//
// Il double la pastille de l'en-tête, qui ne se voit pas quand on regarde une cible à 3 m.
// ⚠️ Le texte dit que **la saisie continue**, il ne nomme pas seulement la panne : un bandeau qui
// dirait « hors ligne » et rien d'autre ferait arrêter de saisir.
// Le pourquoi de la forme et du texte : relevé de l'axe saisie, `epics/EPIC-17`.

import { useConnexionStore } from '../stores/connexionStore'
import { useFileHorsLigneStore } from '../stores/fileHorsLigneStore'
import { etatIndicateur } from './indicateur'

export function BandeauHorsLigne() {
  const statut = useConnexionStore((state) => state.statut)
  const nbEnAttente = useFileHorsLigneStore((state) => state.enAttente.length)
  const synchronisation = useFileHorsLigneStore((state) => state.synchronisation)
  const { classe, libelle } = etatIndicateur(statut, nbEnAttente, synchronisation)

  // `connexion` (lien en cours d'établissement) n'ouvre pas le bandeau : au chargement, il
  // clignoterait à chaque arrivée sur un écran.
  if (classe !== 'deconnecte' && classe !== 'synchronisation') return null
  // ⚠️ **Lien rétabli = pas de bandeau, même file pleine.** `etatIndicateur` rend `deconnecte` dès
  // que `nbEnAttente > 0`, quel que soit le lien : tolérable pour une pastille de 10 px, faux pour
  // un aplat en travers de l'écran. Le cas n'est pas théorique — un rejeu interrompu sur un
  // transitoire laisse la file pleine sans redéclencher (`useRejeuFileHorsLigne` n'écoute qu'une
  // **transition** de statut), et la file est persistée. Le bandeau resterait à vie. `DETTE-112`.
  if (statut === 'connecte' && !synchronisation) return null

  return (
    <p className={`bandeau-hors-ligne bandeau-hors-ligne--${classe}`} role="status">
      <strong>{libelle}</strong>
      {classe === 'deconnecte'
        ? ' — la saisie continue. Ce qui est tapé part tout seul au retour du réseau.'
        : ' — les saisies en attente repartent vers le serveur.'}
    </p>
  )
}
