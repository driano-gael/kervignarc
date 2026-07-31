// La bibliothèque de **formats de tournoi** (E01US023, ADR-0060 §5) — écran de l'axe **atelier**.
//
// Un format est le déroulé type d'une compétition : « FFTA officiel : qualification 20×3 en fin de
// série ». C'est lui, et non la phase, qui se réutilise d'une année sur l'autre — une phase porte un
// statut et un rang dans **une** édition, qui n'ont aucun sens hors d'elle.
//
// L'écran ne prend **aucun `tournoiId`** : appliquer un format à un tournoi se fait depuis le
// pilotage (`Assemblage`), là où l'on travaille sur une édition.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Etape, FormatTournoi } from './api'
import { decrireEtape } from './format'
import {
  useCreerFormat,
  useDupliquerFormat,
  useFormats,
  useModifierFormat,
  usePrechargerPresetsFormats,
  useSupprimerFormat,
} from './hooks'

export function Formats() {
  const formats = useFormats()
  const precharger = usePrechargerPresetsFormats()

  const officiels = (formats.data ?? []).filter((f) => f.origine === 'ffta')
  const maison = (formats.data ?? []).filter((f) => f.origine === 'utilisateur')

  return (
    <section>
      <h3 className="carte__soustitre">Formats de tournoi</h3>
      <p className="carte__etat">
        Un format décrit <strong>le déroulé</strong> d’une compétition&nbsp;: ses phases, leur
        barème et le moment où le scoreur valide. Appliqué à un tournoi, il en{' '}
        <strong>crée les phases</strong>
        &nbsp;; les ajuster ensuite ne change pas le format.
      </p>

      <div>
        <button type="button" disabled={precharger.isPending} onClick={() => precharger.mutate()}>
          Charger les formats types
        </button>
        {precharger.data && (
          <p className="carte__etat">
            {precharger.data.length === 0
              ? 'Rien de neuf : les formats types étaient déjà là.'
              : `${precharger.data.length} format(s) ajouté(s).`}
          </p>
        )}
        <MessageErreur erreur={precharger.error} />
      </div>

      <FormulaireFormat />
      {formats.isError && <MessageErreur erreur={formats.error} />}

      <h4 className="carte__soustitre">Formats officiels</h4>
      <p className="carte__etat">
        Modifier un format officiel le <strong>laisse officiel</strong> (le règlement évolue). Pour
        garder les deux versions, utilisez «&nbsp;Dupliquer&nbsp;».
      </p>
      {officiels.length === 0 ? (
        <p className="carte__etat">
          Aucun format officiel : utilisez « Charger les formats types ».
        </p>
      ) : (
        <ul className="liste-gabarits">
          {officiels.map((format) => (
            <LigneFormat key={format.id} format={format} />
          ))}
        </ul>
      )}

      <h4 className="carte__soustitre">Formats du club</h4>
      {maison.length === 0 ? (
        <p className="carte__etat">Aucun format créé par le club.</p>
      ) : (
        <ul className="liste-gabarits">
          {maison.map((format) => (
            <LigneFormat key={format.id} format={format} />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneFormat({ format }: { format: FormatTournoi }) {
  const [duplication, setDuplication] = useState(false)
  const [nouveauNom, setNouveauNom] = useState(`${format.nom} (copie)`)
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const dupliquer = useDupliquerFormat()
  const modifier = useModifierFormat()
  const supprimer = useSupprimerFormat()

  return (
    <li className="gabarit">
      <div className="gabarit__ligne">
        <span className="gabarit__nom">{format.nom}</span>
        <span className="gabarit__attributs">{format.etapes.map(decrireEtape).join(' → ')}</span>
        <span className="gabarit__actions">
          {/* Les **deux issues** du CA « modifier un officiel », côte à côte : modifier sur place
              (l'officiel reste officiel — le règlement évolue) ou dupliquer (les deux modèles
              coexistent). L'API du premier existait déjà mais aucun écran ne l'atteignait. */}
          <button type="button" className="bouton--discret" onClick={() => setEdition(!edition)}>
            {edition ? 'Annuler' : 'Modifier'}
          </button>
          <button type="button" className="bouton--discret" onClick={() => setDuplication(true)}>
            Dupliquer
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate(format.id)}
              >
                Confirmer la suppression
              </button>
              <button
                type="button"
                className="bouton--discret"
                onClick={() => setConfirmationSuppression(false)}
              >
                Annuler
              </button>
            </>
          ) : (
            <button
              type="button"
              className="bouton--danger"
              onClick={() => setConfirmationSuppression(true)}
            >
              Supprimer
            </button>
          )}
        </span>
      </div>
      {/* Supprimer un format ne touche aucun tournoi : ses phases en portent une copie. Le dire
          ici évite l'hésitation devant un bouton rouge (ADR-0060 §2). */}
      {confirmationSuppression && (
        <p className="carte__etat">
          Les tournois qui l’ont déjà utilisé gardent leurs phases&nbsp;: rien ne sera perdu chez
          eux.
        </p>
      )}
      {edition && (
        <FormulaireEtapeUnique
          format={format}
          enCours={modifier.isPending}
          onEnregistrer={(nom, etapes) =>
            modifier.mutate(
              { id: format.id, entree: { nom, etapes } },
              {
                onSuccess: () => setEdition(false),
              },
            )
          }
        />
      )}
      {duplication && (
        <form
          className="formulaire"
          onSubmit={(evenement) => {
            evenement.preventDefault()
            dupliquer.mutate(
              { id: format.id, nom: nouveauNom },
              { onSuccess: () => setDuplication(false) },
            )
          }}
        >
          <input
            className="formulaire__champ"
            value={nouveauNom}
            onChange={(e) => setNouveauNom(e.target.value)}
            aria-label="Nom de la copie"
          />
          <button type="submit" disabled={dupliquer.isPending || nouveauNom.trim() === ''}>
            Créer la copie
          </button>
          <button type="button" className="bouton--discret" onClick={() => setDuplication(false)}>
            Annuler
          </button>
        </form>
      )}
      <MessageErreur erreur={modifier.error} />
      <MessageErreur erreur={dupliquer.error} />
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

/**
 * Édition **sur place** du barème d'un format à une seule étape.
 *
 * Bornée au même périmètre que la création (cf. `FormulaireFormat`) : un format à plusieurs phases
 * se fabrique en composant un tournoi puis en l'enregistrant comme format du club, plutôt que de
 * coder ici un second éditeur de séquence. Un format à plusieurs étapes n'affiche donc pas ce
 * formulaire — mieux vaut ne rien proposer que de proposer un geste qui écraserait les autres étapes.
 */
function FormulaireEtapeUnique({
  format,
  enCours,
  onEnregistrer,
}: {
  format: FormatTournoi
  enCours: boolean
  onEnregistrer: (nom: string, etapes: Etape[]) => void
}) {
  const etape = format.etapes[0]
  const [nom, setNom] = useState(format.nom)
  const [nbVolees, setNbVolees] = useState(String(etape?.bareme?.nb_volees ?? 20))
  const [nbFleches, setNbFleches] = useState(String(etape?.bareme?.nb_fleches_par_volee ?? 3))

  if (format.etapes.length !== 1 || etape === undefined || etape.bareme === null) {
    return (
      <p className="carte__etat">
        Ce format enchaîne plusieurs phases&nbsp;: composez-le sur un tournoi (écran
        «&nbsp;Phases&nbsp;») puis enregistrez-le à nouveau sous ce nom depuis l’assemblage.
      </p>
    )
  }

  const valide = nom.trim() !== '' && Number(nbVolees) >= 1 && Number(nbFleches) >= 1

  return (
    <form
      className="formulaire"
      onSubmit={(evenement) => {
        evenement.preventDefault()
        if (!valide) return
        onEnregistrer(nom, [
          {
            ...etape,
            bareme: {
              nb_volees: Number(nbVolees),
              nb_fleches_par_volee: Number(nbFleches),
            },
          },
        ])
      }}
    >
      <input
        className="formulaire__champ"
        value={nom}
        onChange={(e) => setNom(e.target.value)}
        aria-label="Nom du format"
      />
      <input
        className="formulaire__champ"
        type="number"
        min={1}
        value={nbVolees}
        onChange={(e) => setNbVolees(e.target.value)}
        aria-label="Nombre de volées"
      />
      <input
        className="formulaire__champ"
        type="number"
        min={1}
        value={nbFleches}
        onChange={(e) => setNbFleches(e.target.value)}
        aria-label="Flèches par volée"
      />
      <button type="submit" disabled={enCours || !valide}>
        Enregistrer
      </button>
    </form>
  )
}

/**
 * Création d'un format **de qualification** — la seule forme que le moteur sait dérouler seul.
 *
 * Volontairement borné : composer une séquence complète (élimination directe, sources, effectifs)
 * demande un éditeur de séquence, et l'écran « Phases » d'un tournoi le fait déjà. Ici, on crée le
 * cas courant ; les formats plus riches se fabriquent en promouvant le déroulé d'un tournoi déjà
 * composé (« ce format est permanent »), ce qui évite de coder deux fois le même éditeur.
 */
function FormulaireFormat() {
  const [nom, setNom] = useState('')
  const [nbVolees, setNbVolees] = useState('20')
  const [nbFleches, setNbFleches] = useState('3')
  const creer = useCreerFormat()

  const valide = nom.trim() !== '' && Number(nbVolees) >= 1 && Number(nbFleches) >= 1

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!valide) return
    const etape: Etape = {
      ordre: 1,
      type: 'qualification',
      bareme: { nb_volees: Number(nbVolees), nb_fleches_par_volee: Number(nbFleches) },
      validation: { type: 'fin_de_serie', n_volees: null },
      sources: [],
      effectif: null,
    }
    creer.mutate({ nom, etapes: [etape] }, { onSuccess: () => setNom('') })
  }

  return (
    <div>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom du format (ex. Challenge des Champions)"
          aria-label="Nom du format"
        />
        <input
          className="formulaire__champ"
          type="number"
          min={1}
          value={nbVolees}
          onChange={(e) => setNbVolees(e.target.value)}
          placeholder="Nombre de volées"
          aria-label="Nombre de volées"
        />
        <input
          className="formulaire__champ"
          type="number"
          min={1}
          value={nbFleches}
          onChange={(e) => setNbFleches(e.target.value)}
          placeholder="Flèches par volée"
          aria-label="Flèches par volée"
        />
        <div className="formulaire__actions">
          <button type="submit" disabled={creer.isPending || !valide}>
            Ajouter le format
          </button>
        </div>
      </form>
      <MessageErreur erreur={creer.error} />
    </div>
  )
}
