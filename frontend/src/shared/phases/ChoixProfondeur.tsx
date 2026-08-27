// Le réglage « jusqu'où classer » d'une phase en tableau (E06US006, ADR-0070).
//
// Partagé par les **deux** écrans qui composent des phases. **Trois états, pas deux** : « Podium
// (défaut) » envoie `null` (preset du type), « intégral » et « rang N » envoient une politique.
// Podium et « rang 4 » produisent le **même** tournoi, mais les fondre écrirait un réglage sur
// chaque phase déjà composée et ferait passer un défaut hérité pour une décision. ⚠️ **Ce composant
// ne détient AUCUN état** : monté sous condition, un état dérivé d'une prop diverge à la bascule.

import type { EtatProfondeur } from './profondeur'
import { estValide, RANGS_DU_PODIUM } from './profondeur'

// La **conséquence** de chaque mode, énoncée sous le choix (maquette A07, `P-4` : chiffrer au
// moment du choix, pas le découvrir à 10 h).
//
// # DETTE-035 — **l'endroit exact du raccourci** : le schéma à braquets ne compte **pas** les duels
// que la profondeur ajoute. Le classement intégral fait tirer un duel par rang — 436 au lieu de 128
// sur un tableau de 120 (mesuré). ⚠️ Le mode `preset` a **deux** libellés parce que le serveur a
// deux presets (podium pour une élimination directe, **intégral** pour un placement) : un libellé
// unique ferait mentir l'écran sur la moitié des types en tableau.
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

/** Rend le choix de profondeur. Aucun état : l'unique source est `etat`, détenu par le parent.
 *
 * `presetIntegral` dit quel preset le **serveur** appliquera si l'on ne règle rien — il dépend du
 * type de la phase, et l'écran doit le refléter sous peine d'annoncer l'inverse de ce qui se jouera.
 */
export function ChoixProfondeur({
  etat,
  surChangement,
  presetIntegral = false,
}: {
  etat: EtatProfondeur
  surChangement: (etat: EtatProfondeur) => void
  presetIntegral?: boolean
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
          <option value="preset">
            {presetIntegral
              ? 'Défaut du type — classement intégral'
              : 'Défaut du type — podium (finale et petite finale)'}
          </option>
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
      <p className="carte__aide">
        {etat.mode === 'preset' && presetIntegral
          ? AIDE_PROFONDEUR.integral
          : AIDE_PROFONDEUR[etat.mode]}
      </p>
      {!estValide(etat) && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Indiquez le rang où le classement s’arrête — « tout classer » se dit en choisissant le
          classement intégral.
        </span>
      )}
    </div>
  )
}
