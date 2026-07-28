// Setup Vitest partagé par toute la suite front (déclaré dans `test.setupFiles`, vite.config.ts).
//
// - `@testing-library/jest-dom/vitest` étend l'`expect` de Vitest avec les matchers lisibles
//   (`toBeVisible`, `toHaveAttribute`, `toBeEmptyDOMElement`…) — et fournit leur **typage** à `tsc`
//   (augmentation de module, donc visible dans tous les fichiers de test) ;
// - `cleanup()` démonte, après **chaque** test, ce que Testing Library a rendu dans le DOM jsdom :
//   sans lui, un composant d'un test survivrait dans le DOM du test suivant (fuite entre tests).
import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
})
