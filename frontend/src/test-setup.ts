// Setup Vitest partagé par toute la suite front (déclaré dans `test.setupFiles`, vite.config.ts).
//
// - `@testing-library/jest-dom/vitest` étend l'`expect` de Vitest avec les matchers lisibles
//   (`toBeVisible`, `toHaveAttribute`, `toBeEmptyDOMElement`…) — et fournit leur **typage** à `tsc`
//   (augmentation de module, donc visible dans tous les fichiers de test) ;
// - `cleanup()` démonte, après **chaque** test, ce que Testing Library a rendu dans le DOM jsdom :
//   sans lui, un composant d'un test survivrait dans le DOM du test suivant (fuite entre tests) ;
// - `localStorage.clear()` : sous l'environnement jsdom **global** (ADR-0053), les stores Zustand
//   `persist` écrivent réellement dans le localStorage de jsdom — là où l'ancien environnement Node
//   l'ignorait. `cleanup()` ne touche que le DOM rendu ; on vide donc le localStorage explicitement
//   pour qu'aucune persistance ne fuite d'un test au suivant (piège dormant relevé en revue).
import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// `<dialog>` : jsdom rend l'élément mais **n'implémente ni `showModal()` ni `close()`** (limitation
// connue de jsdom, pas du produit). Sans ce complément, tout test qui monte un composant contenant
// un `DialogueConfirmation` (A15, 04/08/2026) échoue sur « showModal is not a function », alors que
// le navigateur, lui, les fournit depuis 2022.
//
// On complète donc l'environnement plutôt que d'affaiblir le composant : ajouter un `typeof ===
// 'function'` dans le code de production reviendrait à écrire une garde qui ne protège de rien en
// vrai et n'existe que pour le test — exactement le genre de branche qu'on ne saurait plus retirer.
//
// L'implémentation reste **minimale et honnête** : elle ne simule ni le piège de focus, ni l'inertie
// de l'arrière-plan, ni `::backdrop`. Elle ne pose que `open`, ce dont les tests ont besoin pour
// interroger le contenu du dialogue. Un test qui prétendrait vérifier le piège de focus ici
// mesurerait ce polyfill, pas le navigateur.
if (typeof HTMLDialogElement !== 'undefined') {
  const prototype = HTMLDialogElement.prototype as HTMLDialogElement & {
    showModal?: () => void
    close?: () => void
  }
  if (typeof prototype.showModal !== 'function') {
    prototype.showModal = function showModal(this: HTMLDialogElement) {
      this.open = true
    }
  }
  if (typeof prototype.close !== 'function') {
    prototype.close = function close(this: HTMLDialogElement) {
      this.open = false
    }
  }
}

afterEach(() => {
  cleanup()
  localStorage.clear()
})
