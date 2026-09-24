// Bandeau hors ligne — **aplat plein, toute la largeur** (planche S09, variante retenue).
//
// Il double la pastille de l'en-tête, qui ne se voit pas quand on regarde une cible à 3 m.
// ⚠️ Le texte dit que **la saisie continue**, il ne nomme pas seulement la panne : un bandeau qui
// dirait « hors ligne » et rien d'autre ferait arrêter de saisir.
// Le pourquoi de la forme et du texte : relevé de l'axe saisie, `epics/EPIC-17`.

import { useConnexionStore } from '../stores/connexionStore'
import { useFileHorsLigneStore } from '../stores/fileHorsLigneStore'

// ⚠️ `DETTE-112` — **la priorité est écrite ici, pas dérivée d'`etatIndicateur`**, et cet écart est
// voulu tant que la dette n'est pas résorbée. La pastille annonce « Hors ligne » dès que la file
// n'est pas vide, **quel que soit le lien** : tolérable sur 10 px, faux sur un aplat pleine largeur.
// Les deux se réuniront quand `etatIndicateur` gagnera son état « en attente ».
export function BandeauHorsLigne() {
  const statut = useConnexionStore((state) => state.statut)
  const nbEnAttente = useFileHorsLigneStore((state) => state.enAttente.length)
  const synchronisation = useFileHorsLigneStore((state) => state.synchronisation)

  if (synchronisation) {
    return (
      <p className="bandeau-hors-ligne bandeau-hors-ligne--synchronisation" role="status">
        <strong>Synchronisation…</strong> — les saisies en attente repartent vers le serveur.
      </p>
    )
  }

  if (statut === 'deconnecte') {
    return (
      <p className="bandeau-hors-ligne bandeau-hors-ligne--deconnecte" role="status">
        <strong>Hors ligne{nbEnAttente > 0 ? ` · ${enAttente(nbEnAttente)}` : ''}</strong> — la
        saisie continue. Ce qui est tapé part tout seul au retour du réseau.
      </p>
    )
  }

  // ⚠️ **Le cas qui ne se referme jamais** : lien revenu, file pleine, rejeu arrêté sur un
  // transitoire — il n'écoute qu'une **transition** de statut, qui n'arrivera plus. Se taire ici
  // laissait des saisies jamais parties sans un pixel pour le dire ; le message, lui, est vrai.
  if (nbEnAttente > 0) {
    return (
      <p className="bandeau-hors-ligne bandeau-hors-ligne--synchronisation" role="status">
        <strong>{enAttente(nbEnAttente)} d’envoi</strong> — rechargez l’écran si le compte ne
        descend pas.
      </p>
    )
  }

  // `connexion` (lien en cours d'établissement) sans rien en attente : pas de bandeau, il
  // clignoterait à chaque arrivée sur un écran.
  return null
}

function enAttente(nb: number): string {
  return `${nb} saisie${nb > 1 ? 's' : ''} en attente`
}
