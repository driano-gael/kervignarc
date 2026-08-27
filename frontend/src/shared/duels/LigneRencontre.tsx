// La ligne d'une rencontre **rédigée** — le composant que les trois formats sans arbre partagent
// dans l'onglet « En cours » (E05US031, ADR-0089).
//
// Le rendu reprend la grammaire visuelle de `LigneDuel` : un spectateur qui passe d'une poule à un
// arbre ne doit pas réapprendre à lire. ⚠️ `# DETTE-072` — **`VueTableaux` n'a pas été migrée
// dessus**, délibérément : son `LigneDuel` porte une feuille de style calibrée sur deux surfaces.
// La duplication restante ne porte que du **JSX** — la logique de lecture est partagée et testée.
// Déclencheur de résorption : la première US qui touche l'un des deux.

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
  prefixe,
}: {
  rencontre: RencontreLisible
  /** Les places de tir de la rencontre, déjà rédigées — `null` si le plan n'est pas posé. */
  places?: string | null
  /** Met la ligne en avant : un archer suivi y tire (ADR-0079). */
  souligne?: boolean
  /**
   * Ce que la rencontre est, **avant** de dire qui s'y oppose — « le 6 défie le 4 » (E05US027).
   *
   * ⚠️ Ajouté pour la colline, et seulement parce que ce format en a besoin : ses positions
   * **sont** l'information que le public suit. Les trois autres l'omettent — une rencontre de poule
   * n'oppose aucune hiérarchie préalable, et un préfixe vide serait du bruit sur un écran projeté.
   */
  prefixe?: string
}) {
  const score = scoreRencontre(rencontre)
  const gagnant = gagnantAffiche(rencontre)
  return (
    <li className={souligne ? 'encours__ligne encours__ligne--suivi' : 'encours__ligne'}>
      {prefixe != null && <span className="encours__places">{prefixe}</span>}
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
          place lisible. « À tirer » non plus n'apprend rien — l'absence de score le dit.
          ⚠️ **La désynchronisation prime, ici comme dans `etatRencontre`** (correctif de revue,
          axe C1). La condition d'origine (`!validee && (termine || desynchronisee)`) taisait le cas
          `desynchronisee && validee`, alors que `rencontre.test.ts` lui consacre un cas et que
          `rencontre.ts` argumente que ce drapeau prime sur tout le reste : la paire test ↔ rendu
          était incohérente, dans le sens qui cache un tir bloqué. */}
      {(rencontre.desynchronisee || (rencontre.termine && !rencontre.validee)) && (
        <span className="encours__etat">{etatRencontre(rencontre)}</span>
      )}
    </li>
  )
}
