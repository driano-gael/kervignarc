// Tests du réglage « jusqu'où classer » sur l'écran de composition (E06US006, ADR-0070).
//
// Quatre choses s'y jouent, et chacune ferme un piège de l'US :
//
// 1. **Le réglage n'apparaît que sur un tableau.** Une poule ou un échauffement n'a pas d'arbre à
//    tronquer ; l'offrir mènerait à un 422 dont la consigne n'est pas réalisable à l'écran ;
// 2. **« Ne rien régler » reste distinct de « podium 4 »**, alors que les deux produisent le même
//    tournoi. Les confondre écrirait un réglage sur chaque phase déjà composée ;
// 3. **Un top N sans rang d'arrêt ne part pas au serveur** ;
// 4. **Ce qui est affiché est ce qui est soumis** — y compris après un aller-**retour** de type.
//
// ⚠️ Le point 4 est celui que la première version de ce fichier a manqué, et il portait l'unique
// bloquant de l'US : le test « oublie le réglage si la phase cesse d'être un tableau » s'arrêtait au
// changement **aller** et ne revenait jamais sur un type en tableau. Le garde-fou était écrit,
// testé, et fuyait par la porte d'à côté. C'est la leçon du fichier : un test qui suit le chemin
// heureux d'un garde-fou ne prouve rien sur le chemin de retour.

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { FormulaireEtape } from './Deroule'

// Matcher volontairement court : le libellé mêle apostrophes droites et typographiques selon les
// écrans, et un test qui casse sur une apostrophe ne dit rien de la fonctionnalité.
const CHOIX = /classer/

function poser(type: 'elimination_directe' | 'poules' | 'placement' = 'elimination_directe') {
  const surValider = vi.fn()
  render(
    <FormulaireEtape
      etape={{
        ordre: 1,
        type,
        bareme: null,
        validation: null,
        poules: null,
        big_shoot_off: null,
        suisse: null,
        colline: null,
        decoupage: null,
        sources: [],
        effectif: null,
        profondeur: null,
        // E05US033 : les deux réglages neufs, au défaut d'avant l'US.
        arrets: [],
        titre: null,
      }}
      etapesAmont={[]}
      surValider={surValider}
      surAnnuler={() => {}}
    />,
  )
  return surValider
}

const valider = () => userEvent.click(screen.getByRole('button', { name: 'Valider' }))
const choisirType = (valeur: string) =>
  userEvent.selectOptions(screen.getByLabelText(/Type de phase/), valeur)

describe('profondeur de classement', () => {
  it('ne propose le réglage que sur une phase en tableau', () => {
    poser('poules')

    expect(screen.queryByLabelText(CHOIX)).toBeNull()
  })

  it('laisse la phase au preset tant qu’on ne choisit rien', async () => {
    const surValider = poser()

    await valider()

    // `null`, et non `{ nom: 'top_n', jusqu_au: 4 }` : le serveur distingue « non réglée » de
    // « réglée au podium », et seule la première laisse la phase suivre son preset.
    expect(surValider).toHaveBeenCalledWith(expect.objectContaining({ profondeur: null }))
  })

  it('transmet le classement intégral sans rang d’arrêt', async () => {
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'integral')
    await valider()

    expect(surValider).toHaveBeenCalledWith(
      expect.objectContaining({ profondeur: { nom: 'un_vers_n', jusqu_au: null } }),
    )
  })

  it('transmet le rang d’arrêt d’un top N', async () => {
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'top')
    const seuil = screen.getByLabelText(/Dernier rang départagé/)
    await userEvent.clear(seuil)
    await userEvent.type(seuil, '8')
    await valider()

    expect(surValider).toHaveBeenCalledWith(
      expect.objectContaining({ profondeur: { nom: 'top_n', jusqu_au: 8 } }),
    )
  })

  it('refuse de valider un top N dont le rang d’arrêt est vide', async () => {
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'top')
    await userEvent.clear(screen.getByLabelText(/Dernier rang départagé/))

    expect(screen.getByRole('button', { name: 'Valider' })).toHaveProperty('disabled', true)
    // `DV-03` : le blocage est **dit**, jamais seulement subi par un bouton grisé.
    expect(screen.getByRole('status').textContent).toContain('rang où le classement')
    expect(surValider).not.toHaveBeenCalled()
  })

  it('oublie le réglage si la phase cesse d’être un tableau', async () => {
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'integral')
    await choisirType('poules')
    await valider()

    // Sans cet oubli, retyper une phase enverrait une profondeur que le serveur refuse (422) —
    // sur un réglage devenu invisible, donc impossible à corriger depuis l'écran.
    expect(surValider).toHaveBeenCalledWith(expect.objectContaining({ profondeur: null }))
  })

  it('affiche après un aller-retour de type ce qu’il soumettra', async () => {
    // ⚠️ **Le test qui manquait** — l'unique bloquant de l'US passait exactement ici. Le contrôle
    // détenait une copie de l'état ; le démontage/remontage la réinitialisait sans toucher celle du
    // formulaire, si bien que l'écran annonçait « Podium (défaut) » et que la soumission envoyait
    // « classement intégral ». Sur un tableau de 120, 128 duels au lieu de 436 — ou l'inverse.
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'integral')
    await choisirType('poules')
    await choisirType('elimination_directe')

    expect(screen.getByLabelText(CHOIX)).toHaveProperty('value', 'integral')
    await valider()
    expect(surValider).toHaveBeenCalledWith(
      expect.objectContaining({ profondeur: { nom: 'un_vers_n', jusqu_au: null } }),
    )
  })

  it('ne reste pas bloqué sans message après un aller-retour sur un seuil vide', async () => {
    // Variante du même défaut : le message d'alerte disparaissait au remontage alors que le
    // formulaire restait bloqué. Bouton grisé, aucune explication, aucun geste évident pour sortir.
    const surValider = poser()

    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'top')
    await userEvent.clear(screen.getByLabelText(/Dernier rang départagé/))
    await choisirType('poules')
    await choisirType('elimination_directe')

    // Soit le formulaire est soumettable, soit il dit pourquoi il ne l'est pas — jamais ni l'un ni
    // l'autre.
    const bloque = screen.getByRole('button', { name: 'Valider' }).hasAttribute('disabled')
    expect(bloque).toBe(screen.queryByRole('status') !== null)
    expect(surValider).not.toHaveBeenCalled()
  })

  it('annonce le preset du type, qui n’est pas le même pour un placement', () => {
    // Le serveur donne au type `placement` le preset **intégral** (il n'a aucun existant à
    // préserver, et son intitulé promet de classer tout le monde). Un libellé unique ferait donc
    // annoncer « finale et petite finale » là où tous les rangs se joueront — le premier correctif
    // n'avait changé que le backend, et deux axes de la 2ᵉ passe l'ont relevé.
    poser('placement')

    expect(screen.getByLabelText(CHOIX).textContent).toContain('classement intégral')
    expect(screen.getByLabelText(CHOIX).textContent).not.toContain('petite finale')
  })

  it('remet le réglage au preset après un ajout, pour ne pas le reporter en silence', async () => {
    // Le formulaire d'ajout n'est jamais démonté entre deux phases. Sans remise à zéro,
    // « classement intégral » se reportait sur la phase suivante — deux tableaux de 120 partant à
    // ~616 duels non demandés. Le correctif avait été appliqué à l'écran jumeau seulement.
    const surValider = vi.fn()
    render(<FormulaireEtape etapesAmont={[]} surValider={surValider} />)

    await userEvent.selectOptions(screen.getByLabelText(/Type de phase/), 'elimination_directe')
    await userEvent.selectOptions(screen.getByLabelText(CHOIX), 'integral')
    await userEvent.click(screen.getByRole('button', { name: 'Ajouter la phase' }))

    expect(screen.getByLabelText(CHOIX)).toHaveProperty('value', 'preset')
  })
})
