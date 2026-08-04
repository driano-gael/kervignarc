// Le réglage « jusqu'où classer » d'une phase en tableau (E06US006, ADR-0070).
//
// Partagé par les **deux** écrans qui composent des phases — « Composer un déroulé » (un modèle de
// bibliothèque) et « Phases » (les phases d'un tournoi). Ce n'est pas un pattern introduit par
// anticipation : les deux sites existent aujourd'hui, et ils portent le même tri-état délicat.
//
// **Trois états, pas deux**, et c'est là que la duplication aurait fait mal :
//
// | À l'écran | Envoyé | Ce que le serveur en fait |
// |---|---|---|
// | Podium (défaut) | `null` | la phase suit le preset de son type |
// | Classement intégral | `{ nom: 'un_vers_n' }` | tous les rangs se jouent |
// | S'arrêter au rang N | `{ nom: 'podium', jusqu_au: N }` | seuls les N premiers sont départagés |
//
// « Podium (défaut) » et « s'arrêter au rang 4 » produisent le **même tournoi**. Les fondre en une
// seule option écrirait pourtant un réglage sur chaque phase déjà composée, et ferait passer un
// défaut hérité pour une décision de l'organisateur. Deux copies de cette subtilité auraient
// divergé à la première correction.

import { useState } from 'react'

import type { Profondeur } from '../../features/patrimoine/api'

/** Les rangs qu'un tableau à petite finale décerne — miroir de `RANGS_DU_PODIUM` côté domaine. */
export const RANGS_DU_PODIUM = 4

/** Ce que l'organisateur choisit ; `preset` = « je ne règle rien ». */
type ModeProfondeur = 'preset' | 'un_vers_n' | 'podium'

// La **conséquence** de chaque mode, énoncée sous le choix (maquette A07, exigence `P-4` : chiffrer
// au moment du choix, pas le découvrir à 10 h). C'est le réglage du déroulé qui pèse le plus lourd
// sur la journée : le classement intégral fait tirer un duel par rang, soit plusieurs fois le
// nombre de matchs d'un tableau tronqué au podium.
const AIDE_PROFONDEUR: Record<ModeProfondeur, string> = {
  preset:
    "La phase se joue comme aujourd'hui : finale et petite finale. Les battus des tours " +
    'antérieurs partagent la tranche de rangs de leur sortie — « 5ᵉ-8ᵉ » — sans être départagés ' +
    'au tir.',
  un_vers_n:
    'Chaque rang se joue : les perdants redescendent en cascade jusqu’au dernier. Personne ne ' +
    'reste en fourchette, mais le nombre de duels augmente fortement — vérifiez la simulation ' +
    'avant de vous y engager.',
  podium:
    'Seuls les premiers rangs sont départagés au tir ; au-delà, les archers restent groupés sur ' +
    'la tranche de leur sortie.',
}

/**
 * Rend le choix de profondeur et **remonte** ce qu'il vaut.
 *
 * `surChangement` reçoit `undefined` quand la saisie est illisible — la convention de `lireEntier`,
 * déjà en place dans ces écrans : le parent bloque alors sa soumission sans avoir à réinterpréter
 * le formulaire.
 */
export function ChoixProfondeur({
  valeur,
  surChangement,
}: {
  valeur: Profondeur | null
  surChangement: (profondeur: Profondeur | null | undefined) => void
}) {
  const [mode, setMode] = useState<ModeProfondeur>(valeur?.nom ?? 'preset')
  // Saisi en **texte** : un champ numérique vidé doit pouvoir rester vide pendant qu'on le retape,
  // ce qu'un `number` piloté ferait perdre à chaque frappe (même parti que l'effectif simulé).
  const [seuil, setSeuil] = useState(String(valeur?.jusqu_au ?? RANGS_DU_PODIUM))

  const lu = lireSeuil(seuil)
  const invalide = mode === 'podium' && lu === undefined

  const propager = (modeSuivant: ModeProfondeur, seuilSuivant: string) => {
    setMode(modeSuivant)
    setSeuil(seuilSuivant)
    surChangement(composer(modeSuivant, lireSeuil(seuilSuivant)))
  }

  return (
    <div className="formulaire__champ">
      <label className="formulaire__libelle">
        Jusqu’où classer
        <select value={mode} onChange={(e) => propager(e.target.value as ModeProfondeur, seuil)}>
          <option value="preset">Podium — rangs 1 à {RANGS_DU_PODIUM} (défaut)</option>
          <option value="un_vers_n">Classement intégral — tous les rangs se jouent</option>
          <option value="podium">S’arrêter à un rang précis…</option>
        </select>
      </label>
      {mode === 'podium' && (
        <label className="formulaire__libelle">
          Dernier rang départagé
          <input
            inputMode="numeric"
            value={seuil}
            onChange={(e) => propager(mode, e.target.value)}
          />
        </label>
      )}
      <p className="carte__aide">{AIDE_PROFONDEUR[mode]}</p>
      {invalide && (
        <span className="carte__etat carte__etat--alerte" role="status">
          Indiquez le rang où le classement s’arrête — « tout classer » se dit en choisissant le
          classement intégral.
        </span>
      )}
    </div>
  )
}

/** `undefined` = illisible **ou vide** : « je m'arrête à un rang » sans dire lequel n'en est pas un. */
function lireSeuil(saisi: string): number | undefined {
  const valeur = Number(saisi)
  if (saisi.trim() === '' || !Number.isInteger(valeur) || valeur < 1) return undefined
  return valeur
}

function composer(mode: ModeProfondeur, seuil: number | undefined): Profondeur | null | undefined {
  if (mode === 'preset') return null
  if (mode === 'un_vers_n') return { nom: 'un_vers_n', jusqu_au: null }
  return seuil === undefined ? undefined : { nom: 'podium', jusqu_au: seuil }
}
