// Le réglage « jusqu'où classer » d'une phase en tableau (E06US006, ADR-0070).
//
// Partagé par les **deux** écrans qui composent des phases — « Composer un déroulé » (un modèle de
// bibliothèque) et « Phases » (les phases d'un tournoi). Ce n'est pas un pattern introduit par
// anticipation : les deux sites existent aujourd'hui, et ils portent le même tri-état délicat.
//
// **Trois états, pas deux** :
//
// | À l'écran | Envoyé | Ce que le serveur en fait |
// |---|---|---|
// | Podium (défaut) | `null` | la phase suit le preset de son type |
// | Classement intégral | `{ nom: 'un_vers_n' }` | tous les rangs se jouent |
// | S'arrêter au rang N | `{ nom: 'top_n', jusqu_au: N }` | seuls les N premiers sont départagés |
//
// « Podium (défaut) » et « s'arrêter au rang 4 » produisent le **même tournoi**. Les fondre en une
// seule option écrirait pourtant un réglage sur chaque phase déjà composée, et ferait passer un
// défaut hérité pour une décision de l'organisateur.
//
// ⚠️ **Ce composant ne détient AUCUN état, et c'est la correction centrale de la revue.** Il en
// détenait un (`mode` + `seuil`, initialisés depuis une prop), pendant que le parent gardait le
// sien : deux sources pour une donnée. Comme il est monté sous condition
// (`{enTableau && <ChoixProfondeur/>}`), retyper une phase le **démontait**, y revenir le
// **remontait** réinitialisé — et le parent, lui, ne bougeait pas. L'écran affichait alors « Podium
// (défaut) » pendant que le formulaire envoyait « classement intégral » : sur un tableau de 120,
// 128 duels devenaient 436 sans que personne ne l'ait demandé, soit exactement ce qu'ADR-0070 §3
// s'engage à ne jamais imposer. Les **cinq** axes de revue l'ont trouvé.
//
// La leçon dépasse ce composant : un état dérivé d'une prop, dans un composant monté sous
// condition, diverge dès que la condition bascule. Ici l'unique source est le parent ; ce fichier
// ne fait que rendre et notifier.

import type { EtatProfondeur } from './profondeur'
import { estValide, RANGS_DU_PODIUM } from './profondeur'

// La **conséquence** de chaque mode, énoncée sous le choix (maquette A07, exigence `P-4` : chiffrer
// au moment du choix, pas le découvrir à 10 h).
//
// # DETTE-035 — c'est ici **l'endroit exact du raccourci** : le schéma à braquets, affiché juste à
// côté, ne compte **pas** les duels que la profondeur ajoute. On énonce donc la conséquence en
// toutes lettres, avec le seul chiffre mesuré, et l'on renvoie à la simulation pour le compte exact. C'est le réglage du déroulé qui pèse le plus lourd
// sur la journée : le classement intégral fait tirer un duel par rang — 436 duels au lieu de 128 sur
// un tableau de 120 (mesuré), soit près de quatre fois plus.
const AIDE_PROFONDEUR: Record<EtatProfondeur['mode'], string> = {
  preset:
    "La phase se joue comme aujourd'hui : finale et petite finale. Les battus des tours " +
    'antérieurs partagent la tranche de rangs de leur sortie — « 5ᵉ-8ᵉ » — sans être départagés ' +
    'au tir.',
  integral:
    'Chaque rang se joue : les perdants redescendent en cascade jusqu’au dernier. Personne ne ' +
    'reste en fourchette, mais le nombre de duels est multiplié par trois ou quatre (128 → 436 ' +
    'sur un tableau de 120) — vérifiez la simulation avant de vous y engager.',
  top: 'Seuls les premiers rangs sont départagés au tir ; au-delà, les archers restent groupés sur la tranche de leur sortie.',
}

/** Rend le choix de profondeur. Aucun état : l'unique source est `etat`, détenu par le parent. */
export function ChoixProfondeur({
  etat,
  surChangement,
}: {
  etat: EtatProfondeur
  surChangement: (etat: EtatProfondeur) => void
}) {
  const changerMode = (mode: EtatProfondeur['mode']) => {
    if (mode === 'top') {
      surChangement({ mode, seuil: etat.mode === 'top' ? etat.seuil : String(RANGS_DU_PODIUM) })
      return
    }
    surChangement({ mode })
  }

  return (
    <div className="formulaire__champ">
      <label className="formulaire__libelle">
        Jusqu’où classer
        <select
          value={etat.mode}
          onChange={(e) => changerMode(e.target.value as EtatProfondeur['mode'])}
        >
          {/* Le libellé ne **chiffre** pas le défaut : `RANGS_DU_PODIUM` est un miroir du domaine,
              et un miroir qui dérive ferait ici *mentir* l'écran sur le comportement du serveur —
              alors qu'en pré-saisie du champ ci-dessous, une dérive est sans conséquence. */}
          <option value="preset">Podium (défaut) — finale et petite finale</option>
          <option value="integral">Classement intégral — tous les rangs se jouent</option>
          <option value="top">S’arrêter à un rang précis…</option>
        </select>
      </label>
      {etat.mode === 'top' && (
        <label className="formulaire__libelle">
          Dernier rang départagé
          <input
            inputMode="numeric"
            value={etat.seuil}
            onChange={(e) => surChangement({ mode: 'top', seuil: e.target.value })}
          />
        </label>
      )}
      <p className="carte__aide">{AIDE_PROFONDEUR[etat.mode]}</p>
      {!estValide(etat) && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Indiquez le rang où le classement s’arrête — « tout classer » se dit en choisissant le
          classement intégral.
        </span>
      )}
    </div>
  )
}
