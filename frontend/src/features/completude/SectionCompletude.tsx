// Rendu d'une **section de complétude** — un titre, un résumé facultatif, et la liste de ses
// lignes.
//
// Extrait de `Completude.tsx` en E16US003, quand les deux sections ont cessé de vivre sur le même
// écran : le sportif reste au pilotage, l'administratif est parti sur l'axe gestion (A14). Le rendu
// ne devait surtout **pas** être dupliqué — deux copies auraient divergé au premier ajustement de
// pastille. L'état se rend en **couleur + pastille + texte** (jamais la couleur seule) ; l'alerte
// est **ambre**, jamais rouge (`DV-03`).

import type { LigneCompletude } from './api'
import { afficheEtat, detailLigne } from './presentation'

// `niveau` — le rang du titre dans le plan de la page, pas son style (la classe CSS est la même).
// Les deux appelants ne sont pas au même étage : sur l'écran de pilotage le titre d'écran est un
// `h2`, la section est donc un `h3` ; sur l'écran Paiements le titre d'écran est déjà un `h3` et ses
// sous-blocs des `h4`. Coder `h3` en dur y aurait fait de l'encart un **frère** du titre d'écran
// dans l'arbre d'accessibilité, au lieu d'une sous-section.
export function SectionCompletude({
  titre,
  lignes,
  complet,
  niveau = 3,
}: {
  titre: string
  lignes: LigneCompletude[]
  complet?: boolean
  niveau?: 3 | 4
}) {
  const Titre = niveau === 4 ? 'h4' : 'h3'
  return (
    <div className="completude__section">
      <Titre className="completude__titre">
        {titre}
        {complet !== undefined && (
          <span className={complet ? 'completude__resume--ok' : 'completude__resume--alerte'}>
            {complet ? 'complet' : 'incomplet'}
          </span>
        )}
      </Titre>
      <ul className="completude__liste">
        {lignes.map((ligne) => (
          <LigneCompletudeVue key={ligne.cle} ligne={ligne} />
        ))}
      </ul>
    </div>
  )
}

function LigneCompletudeVue({ ligne }: { ligne: LigneCompletude }) {
  const { classe, libelle } = afficheEtat(ligne.etat)
  const detail = detailLigne(ligne)
  return (
    <li className="completude__ligne">
      <span className="completude__libelle">{ligne.libelle}</span>
      <span className={`completude__etat completude__etat--${classe}`}>
        <span className="indicateur__pastille" aria-hidden="true" />
        {detail ?? libelle}
        {detail && <span className="completude__mention">{libelle}</span>}
      </span>
    </li>
  )
}
