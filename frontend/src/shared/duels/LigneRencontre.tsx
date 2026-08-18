// La ligne d'une rencontre **rédigée** — le composant que les trois formats sans arbre partagent
// dans l'onglet « En cours » (E05US031, ADR-0089).
//
// Le rendu est celui de `LigneDuel` (`features/tableaux/VueTableaux.tsx`), dont il reprend la
// grammaire visuelle : deux noms, un score au milieu, le gagnant en gras une fois scellé. C'est
// voulu — un spectateur qui passe d'une poule à un arbre ne doit pas réapprendre à lire.
//
// ⚠️ `# DETTE-072` — **`VueTableaux` n'a pas été migrée dessus dans cette US**, et c'est délibéré :
// son `LigneDuel` porte les classes `tableaux__*` et une feuille de style calibrée sur deux surfaces
// (360 px et projection), et la refondre aurait mêlé à cette US un remaniement de l'existant sans
// bénéfice pour le CA. La duplication restante est **connue et bornée à deux rendus** ; ce qui
// compte est qu'elle ne porte que du JSX — la logique de lecture, elle, est partagée dans
// `rencontre.ts` et testée. Déclencheur de résorption : la première US qui touche l'un des deux.

import {
  etatRencontre,
  gagnantAffiche,
  nomComplet,
  scoreRencontre,
  type RencontreLisible,
} from './rencontre'

export function LigneRencontre({
  rencontre,
  places,
  souligne = false,
}: {
  rencontre: RencontreLisible
  /** Les places de tir de la rencontre, déjà rédigées — `null` si le plan n'est pas posé. */
  places?: string | null
  /** Met la ligne en avant : un archer suivi y tire (ADR-0079). */
  souligne?: boolean
}) {
  const score = scoreRencontre(rencontre)
  const gagnant = gagnantAffiche(rencontre)
  return (
    <li className={souligne ? 'encours__ligne encours__ligne--suivi' : 'encours__ligne'}>
      <span className={gagnant === 'haut' ? 'encours__gagnant' : undefined}>
        {rencontre.haut === null ? '—' : nomComplet(rencontre.haut)}
      </span>
      <span className="encours__vs">{score ?? 'vs'}</span>
      <span className={gagnant === 'bas' ? 'encours__gagnant' : undefined}>
        {rencontre.bas === null ? '—' : nomComplet(rencontre.bas)}
      </span>
      {places != null && <span className="encours__places">{places}</span>}
      {/* L'état n'est écrit que lorsqu'il apprend quelque chose : « validée » sur une ligne qui
          porte déjà son score en gras est du bruit, et sur un écran projeté le bruit coûte de la
          place lisible. « À tirer » non plus n'apprend rien — l'absence de score le dit. */}
      {!rencontre.validee && (rencontre.termine || rencontre.desynchronisee) && (
        <span className="encours__etat">{etatRencontre(rencontre)}</span>
      )}
    </li>
  )
}
