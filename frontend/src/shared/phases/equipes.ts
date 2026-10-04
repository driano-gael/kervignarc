// Le type d'équipe qu'une étape oppose (E13US004, ADR-0120) — déclaré une fois, lu par l'atelier des
// phases et par la feature équipes. Séparé du `.tsx` pour `react-refresh/only-export-components`.

export type TypeEquipe = 'standard' | 'mixte'

export function estTypeEquipe(valeur: string): valeur is TypeEquipe {
  return valeur === 'standard' || valeur === 'mixte'
}
