// Partage des chemins entre `vite.config.ts` (qui répartit les tests en deux projets Vitest) et
// `test-environnement.test.ts` (qui vérifie que la liste ci-dessous est exacte). Cf. ADR-0110.

// Les modules `.test.ts` qui manipulent tout de même un DOM, et doivent donc tourner sous `jsdom`.
// La convention normale est : `.test.tsx` → composant → `jsdom` ; `.test.ts` → logique pure →
// `node`. Ces six-là sont de la logique pure qui touche `document`, `window` ou `localStorage`.
// ⚠️ Un `.test.ts` neuf touchant au DOM échouerait sous `node` avec un message obscur
// (`document is not defined`) : `test-environnement.test.ts` le rattrape et nomme le coupable.
export const TESTS_TS_AVEC_DOM: readonly string[] = [
  'src/features/saisie/rejeu.test.ts',
  'src/features/scoreur-session/url.test.ts',
  'src/shared/navigation/useChemin.test.ts',
  'src/shared/stores/sessionSuivisStore.test.ts',
  'src/shared/theme.test.ts',
  'src/shared/ui/pagination.test.ts',
]

// Ce qui trahit un besoin de DOM dans un module de test.
export const MARQUEURS_DE_DOM =
  /@testing-library|\bdocument\.|\bwindow\.|\blocalStorage\b|\bHTMLElement\b/
