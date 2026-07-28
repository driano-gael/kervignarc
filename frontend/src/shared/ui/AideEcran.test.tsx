import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AideEcran } from './AideEcran'

// Premier test de **rendu** du projet (Testing Library + jsdom, E14US002 / ADR-0053). Il vérifie le
// comportement de disclosure d'`AideEcran` — ce que la porte mécanique (tsc/eslint) ne peut pas
// prouver : que le bouton bascule bien l'aide, et qu'elle part **repliée** (CA « masqué par défaut »).
describe('AideEcran', () => {
  const TEXTE = 'Créez les créneaux de tir et leur tarif.'

  // Repli défensif (comme MessageErreur) : une destination sans aide ne doit pas laisser de bouton
  // fantôme. Le garde `if (!texte)` couvre les **trois** valeurs falsy admises par la signature
  // (`string | null | undefined`) ; `undefined` est le chemin de prod réaliste (accès `AIDE_ECRANS[id]`
  // sous noUncheckedIndexedAccess), on cloue les trois pour verrouiller tout le contrat.
  it.each([undefined, null, ''])('ne rend rien quand le texte est %p', (texte) => {
    const { container } = render(<AideEcran texte={texte} />)
    expect(container).toBeEmptyDOMElement()
  })

  it("affiche le bouton mais garde l'aide repliée par défaut", () => {
    render(<AideEcran texte={TEXTE} />)

    const bouton = screen.getByRole('button', { name: /aide/i })
    expect(bouton).toHaveAttribute('aria-expanded', 'false')
    // Le panneau est maintenu dans le DOM (pour `aria-controls`) mais masqué par `hidden` → invisible.
    expect(screen.getByText(TEXTE)).not.toBeVisible()
  })

  it("déploie puis replie l'aide au tap", async () => {
    const utilisateur = userEvent.setup()
    render(<AideEcran texte={TEXTE} />)
    const bouton = screen.getByRole('button', { name: /aide/i })

    await utilisateur.click(bouton)
    expect(bouton).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(TEXTE)).toBeVisible()

    await utilisateur.click(bouton)
    expect(bouton).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText(TEXTE)).not.toBeVisible()
  })
})
