// Import en masse du référentiel des clubs (E01US023) — brique de l'écran « Clubs » de l'atelier.
//
// Un champ **texte libre** plutôt qu'un fichier : ce que l'organisateur a sous la main, c'est un
// copier-coller depuis un tableur ou un courriel. ⚠️ **Ce n'est pas l'import des inscrits**
// (E02US007, non livré), qui lit un fichier fédéral et crée archers, clubs et départs d'un tournoi
// ; celui-ci ne fait que peupler un référentiel global. Le dire à l'écran évite qu'on l'essaie avec
// un fichier de licenciés.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useImporterClubs } from './hooks'

export function ImportClubs() {
  const [lignes, setLignes] = useState('')
  const importer = useImporterClubs()
  const rapport = importer.data

  return (
    <section>
      <h4 className="carte__soustitre">Importer une liste de clubs</h4>
      <p className="carte__etat">
        Collez une liste, <strong>un club par ligne</strong>. Les clubs déjà connus sont ignorés
        (accents et majuscules ne comptent pas), les lignes vides aussi.
      </p>
      <form
        className="formulaire formulaire--colonne"
        onSubmit={(evenement) => {
          evenement.preventDefault()
          if (lignes.trim() !== '') importer.mutate(lignes, { onSuccess: () => setLignes('') })
        }}
      >
        <textarea
          className="formulaire__champ"
          rows={8}
          value={lignes}
          onChange={(e) => setLignes(e.target.value)}
          placeholder={'Arc Club de Lorient\nLes Archers de Kervignac\nÉlan de Fougères'}
          aria-label="Liste de clubs à importer"
        />
        <div className="formulaire__actions">
          <button type="submit" disabled={importer.isPending || lignes.trim() === ''}>
            Importer
          </button>
        </div>
      </form>
      {rapport && (
        <p className="carte__etat">
          {rapport.crees.length} club(s) ajouté(s)
          {rapport.doublons.length > 0 && `, ${rapport.doublons.length} déjà connu(s)`}
          {rapport.lignes_ignorees > 0 && `, ${rapport.lignes_ignorees} ligne(s) vide(s)`}.
          {rapport.doublons.length > 0 && <> Déjà connus&nbsp;: {rapport.doublons.join(', ')}.</>}
        </p>
      )}
      <MessageErreur erreur={importer.error} />
    </section>
  )
}
