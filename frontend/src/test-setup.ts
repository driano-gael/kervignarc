// Setup Vitest partagé par toute la suite front (`test.setupFiles`, vite.config.ts).
//
// `jest-dom/vitest` étend l'`expect` de Vitest et fournit leur **typage** à `tsc` ; `cleanup()`
// démonte après **chaque** test ce que Testing Library a rendu, sans quoi un composant survivrait
// dans le DOM du test suivant. ⚠️ `localStorage.clear()` : sous jsdom **global** (ADR-0053), les
// stores Zustand `persist` écrivent réellement dans le localStorage — `cleanup()` ne touche que le
// DOM rendu, on le vide donc explicitement (piège dormant relevé en revue).
import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// ⚠️ `<dialog>` : jsdom rend l'élément mais **n'implémente ni `showModal()` ni `close()`**
// (limitation de jsdom, pas du produit). Sans ce complément, tout test montant un
// `DialogueConfirmation` échoue sur « showModal is not a function ».
//
// On complète l'environnement plutôt que d'affaiblir le composant : une garde `typeof ===
// 'function'` en production ne protégerait de rien et n'existerait que pour le test.
// L'implémentation reste **minimale et honnête** — ni piège de focus, ni inertie, ni `::backdrop` :
// un test qui prétendrait vérifier le piège de focus mesurerait ce polyfill, pas le navigateur.
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
