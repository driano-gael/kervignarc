// Partage entre `vite.config.ts` (qui répartit les tests en deux projets Vitest) et
// `test-environnement.test.ts` (qui vérifie cette répartition). Cf. ADR-0110 § Décision 8.

// Les modules `.test.ts` qui ont besoin d'un DOM, et **pourquoi**. La convention normale est :
// `.test.tsx` → composant → `jsdom` ; `.test.ts` → logique pure → `node`.
// ⚠️ La raison est obligatoire parce que le besoin est souvent **transitif** : un test peut
// n'écrire ni `document` ni `localStorage` et pourtant exercer un chemin qui en dépend. La
// détection automatique ci-dessous ne voit que les usages **directs** ; elle garde les modules
// hors de cette table, elle ne décide pas de son contenu.
export const TESTS_TS_AVEC_DOM: Readonly<Record<string, string>> = {
  'src/features/saisie/rejeu.test.ts': 'la file de rejeu est persistée en localStorage',
  'src/features/saisie-duels/rejeu.test.ts': 'store zustand `persist`, inopérant sans localStorage',
  'src/features/scoreur-session/url.test.ts': 'lit window.location',
  'src/shared/navigation/useChemin.test.ts': 'lit et écrit window.history',
  'src/shared/stores/fileHorsLigneStore.test.ts': 'store zustand `persist` adossé à localStorage',
  'src/shared/stores/sessionPosteStore.test.ts':
    '`definir()` applique le thème, et `appliquerTheme` sort tôt sans `document`',
  'src/shared/stores/sessionSuivisStore.test.ts': 'store zustand `persist` adossé à localStorage',
  'src/shared/theme.test.ts': 'applique des attributs sur `document.documentElement`',
  'src/shared/ui/pagination.test.ts': 'mesure des éléments rendus',
}

export const CHEMINS_AVEC_DOM: readonly string[] = Object.keys(TESTS_TS_AVEC_DOM)

// Ce qui trahit un usage **direct** du DOM dans un module de test.
export const MARQUEURS_DE_DOM =
  /@testing-library|\bdocument\.|\bwindow\.|\b(local|session)Storage\b|\bHTMLElement\b|\bnavigator\.|\bmatchMedia\b|getComputedStyle/

// ⚠️ Sans cette coupe, une simple **phrase de commentaire** citant `localStorage` suffit à
// ranger un module en jsdom — et le test « aucune entrée inutile » mesure alors le commentaire,
// pas le code. Constaté sur `features/saisie/rejeu.test.ts` en revue d'E00US031.
export function sansCommentaires(source: string): string {
  return source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')
}
