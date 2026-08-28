// Pavé de saisie d'un code de terrain — retour maquettes du 04/08/2026 (S01).
//
// Variante retenue **B — le code court domine** (« je ne suis pas sûr que les caméras soient
// toujours accessibles ») : le code devient la voie principale, et doit se taper **sans clavier
// système**. ⚠️ « Caractère non accessible » a un sens précis : le serveur tire ses codes dans un
// alphabet **sans confondables** (ni `I`, ni `O`, ni `0`, ni `1`), que le champ texte laissait
// pourtant saisir — pour finir sur un refus incompréhensible. L'ambiguïté est traitée là où elle
// naît. Alphabet et normalisation vivent dans `codeTerrain.ts`.

import { useId } from 'react'
import { ALPHABET_CODE, LONGUEUR_CODE, normaliserCode } from './codeTerrain'

export function PaveCode({
  code,
  onChange,
  libelle,
  desactive = false,
}: {
  code: string
  onChange: (code: string) => void
  libelle: string
  desactive?: boolean
}) {
  const idChamp = useId()

  const ajouter = (caractere: string) => {
    if (!desactive && code.length < LONGUEUR_CODE) onChange(code + caractere)
  }

  return (
    <div className="pave-code">
      {/* Les cases de ce qui est tapé. Un `<input>` reste **derrière**, non masqué : il porte le
          libellé accessible, accepte un clavier physique (le PC d'organisation en a un) et permet le
          collage d'un code reçu par message — filtré par `normaliserCode`. Le pavé le complète, il
          ne le remplace pas. */}
      <label className="pave-code__libelle" htmlFor={idChamp}>
        {libelle}
      </label>
      <input
        id={idChamp}
        className="formulaire__champ pave-code__champ"
        value={code}
        onChange={(e) => onChange(normaliserCode(e.target.value))}
        disabled={desactive}
        // `inputMode="none"` : sur tablette et téléphone, toucher le champ **n'ouvre pas** le clavier
        // système — c'est le pavé ci-dessous qui sert, et deux claviers superposés cachent l'écran.
        // Le clavier physique d'un PC continue de fonctionner : `inputMode` ne concerne que le
        // clavier virtuel.
        inputMode="none"
        autoComplete="one-time-code"
        autoCapitalize="characters"
        spellCheck={false}
        placeholder="——————"
      />

      <div className="pave-code__touches" role="group" aria-label="Touches du code">
        {[...ALPHABET_CODE].map((caractere) => (
          <button
            key={caractere}
            type="button"
            className="pave-code__touche"
            disabled={desactive || code.length >= LONGUEUR_CODE}
            onClick={() => ajouter(caractere)}
          >
            {caractere}
          </button>
        ))}
      </div>

      <div className="pave-code__actions">
        <button
          type="button"
          className="bouton--discret"
          disabled={desactive || code.length === 0}
          onClick={() => onChange(code.slice(0, -1))}
        >
          ← Corriger
        </button>
        <button
          type="button"
          className="bouton--discret"
          disabled={desactive || code.length === 0}
          onClick={() => onChange('')}
        >
          Tout effacer
        </button>
      </div>
    </div>
  )
}
