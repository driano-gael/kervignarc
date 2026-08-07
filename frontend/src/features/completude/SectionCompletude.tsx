// Rendu d'une **section de complétude** — un titre, un résumé facultatif, et la liste de ses lignes.
//
// Extrait de `Completude.tsx` en E16US003, quand les deux sections ont cessé de vivre sur le même
// écran : le sportif reste au pilotage, l'administratif est parti sur l'axe gestion (A14, « je
// n'aime pas le mélange entre le déroulé et la gestion administrative »). Le rendu, lui, ne devait
// surtout **pas** être dupliqué — deux copies auraient divergé au premier ajustement de pastille.
//
// L'état se rend en **couleur + pastille + texte** (jamais la couleur seule) ; l'alerte = **ambre**,
// jamais rouge (charte, `DV-03`).

import type { LigneCompletude } from './api'
import { afficheEtat, detailLigne } from './presentation'

export function SectionCompletude({
  titre,
  lignes,
  complet,
}: {
  titre: string
  lignes: LigneCompletude[]
  complet?: boolean
}) {
  return (
    <div className="completude__section">
      <h3 className="completude__titre">
        {titre}
        {complet !== undefined && (
          <span className={complet ? 'completude__resume--ok' : 'completude__resume--alerte'}>
            {complet ? 'complet' : 'incomplet'}
          </span>
        )}
      </h3>
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
