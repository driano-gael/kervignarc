// La bibliothèque de briques du club (E01US023, ADR-0060) — écrans de l'axe **atelier**.
//
// Ces écrans ne prennent **aucun `tournoiId`** : c'est ce qui résorbe DETTE-023. **Deux listes
// séparées** (CA) : référentiel officiel FFTA d'un côté, créations du club de l'autre — la marque
// d'origine dit **d'où vient** la brique, elle ne certifie pas la conformité au règlement (RG-8,
// ADR-0060 §4). Le référentiel FFTA reste **modifiable et supprimable** : le règlement est un
// template, jamais un verrou. Édition et suppression réutilisent les routes **à plat**
// d'E01US003/E01US005.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { Blason } from '../blasons/api'
import type { Categorie } from '../categories/api'
import type { OrigineBrique } from './api'
import { decrireRapport } from './format'
import {
  useBlasonsBibliotheque,
  useCategoriesBibliotheque,
  useCreerBlasonBibliotheque,
  useCreerCategorieBibliotheque,
  useDupliquerBlasonBibliotheque,
  useDupliquerCategorieBibliotheque,
  usePrechargerFftaBibliotheque,
  useRenommerCategorieBibliotheque,
  useSupprimerBlasonBibliotheque,
  useSupprimerCategorieBibliotheque,
} from './hooks'

/** Une brique de bibliothèque, vue par ces écrans : de quoi la nommer et la ranger. */
interface Brique {
  id: number
  origine: OrigineBrique
}

export function CategoriesBibliotheque() {
  const categories = useCategoriesBibliotheque()

  return (
    <section>
      <h3 className="carte__soustitre">Catégories du club</h3>
      <p className="carte__etat">
        Ces catégories appartiennent au club et vivent d’une année sur l’autre. Un tournoi en reçoit
        une <strong>copie</strong>&nbsp;: la modifier là-bas ne change rien ici, et les éditions
        déjà passées ne bougent pas.
      </p>
      <PrechargementFfta />
      <FormulaireCategorie />
      {categories.isError && <MessageErreur erreur={categories.error} />}
      {/* Sans ce garde, le premier rendu annonce « aucune catégorie » pendant le fetch — sur la
          destination d'ouverture de l'atelier, donc à chaque entrée dans l'axe. */}
      {categories.isPending ? (
        <p className="carte__etat">Chargement…</p>
      ) : (
        <ListesParOrigine
          briques={categories.data ?? []}
          rendre={(categorie) => <LigneCategorie key={categorie.id} categorie={categorie} />}
          videOfficiel="Aucune catégorie officielle : utilisez « Charger le référentiel FFTA »."
          videMaison="Aucune catégorie créée par le club."
        />
      )}
    </section>
  )
}

export function BlasonsBibliotheque() {
  const blasons = useBlasonsBibliotheque()

  return (
    <section>
      <h3 className="carte__soustitre">Blasons du club</h3>
      <p className="carte__etat">
        Comme les catégories&nbsp;: ce sont des modèles du club, dont chaque tournoi reçoit une
        copie.
      </p>
      <PrechargementFfta />
      <FormulaireBlason />
      {blasons.isError && <MessageErreur erreur={blasons.error} />}
      {blasons.isPending ? (
        <p className="carte__etat">Chargement…</p>
      ) : (
        <ListesParOrigine
          briques={blasons.data ?? []}
          rendre={(blason) => <LigneBlason key={blason.id} blason={blason} />}
          videOfficiel="Aucun blason officiel : utilisez « Charger le référentiel FFTA »."
          videMaison="Aucun blason créé par le club."
        />
      )}
    </section>
  )
}

/**
 * Les deux listes du CA, rendues côte à côte.
 *
 * Générique sur le type de brique plutôt que dupliqué : catégories et blasons se rangent par la
 * **même** règle, et la recopier aurait laissé les deux écrans diverger au premier ajustement.
 */
function ListesParOrigine<T extends Brique>({
  briques,
  rendre,
  videOfficiel,
  videMaison,
}: {
  briques: T[]
  rendre: (brique: T) => React.ReactNode
  videOfficiel: string
  videMaison: string
}) {
  const officielles = briques.filter((b) => b.origine === 'ffta')
  const maison = briques.filter((b) => b.origine === 'utilisateur')

  return (
    <>
      <h4 className="carte__soustitre">Référentiel officiel FFTA</h4>
      {/* Dit franchement ce que la marque ne prouve pas (ADR-0060 §4) : sans cette phrase, un
          organisateur lirait « officiel » comme « conforme », y compris après l'avoir modifié. */}
      <p className="carte__etat">
        Chargées depuis le référentiel fédéral. Elles restent <strong>modifiables</strong>&nbsp;: la
        mention «&nbsp;officiel&nbsp;» dit d’où elles viennent, pas qu’elles sont conformes au
        règlement en vigueur.
      </p>
      {officielles.length === 0 ? (
        <p className="carte__etat">{videOfficiel}</p>
      ) : (
        <ul className="liste-gabarits">{officielles.map(rendre)}</ul>
      )}

      <h4 className="carte__soustitre">Créations du club</h4>
      {maison.length === 0 ? (
        <p className="carte__etat">{videMaison}</p>
      ) : (
        <ul className="liste-gabarits">{maison.map(rendre)}</ul>
      )}
    </>
  )
}

/** Charge le référentiel FFTA **dans la bibliothèque** — une fois, plus à chaque tournoi. */
function PrechargementFfta() {
  const precharger = usePrechargerFftaBibliotheque()
  const rapport = precharger.data

  return (
    <div>
      <button type="button" disabled={precharger.isPending} onClick={() => precharger.mutate()}>
        Charger le référentiel FFTA
      </button>
      {rapport && <p className="carte__etat">{decrireRapport(rapport)}</p>}
      <MessageErreur erreur={precharger.error} />
    </div>
  )
}

function LigneCategorie({ categorie }: { categorie: Categorie }) {
  const [edition, setEdition] = useState(false)
  const [libelle, setLibelle] = useState(categorie.libelle)
  const renommer = useRenommerCategorieBibliotheque()
  const dupliquer = useDupliquerCategorieBibliotheque()
  const supprimer = useSupprimerCategorieBibliotheque()

  return (
    <li className="gabarit">
      <div className="gabarit__ligne">
        <span className="gabarit__nom">{categorie.libelle}</span>
        <span className="gabarit__attributs">
          {[categorie.arme, categorie.ages.join(', '), categorie.sexe].filter(Boolean).join(' · ')}
        </span>
        <span className="gabarit__actions">
          <button type="button" className="bouton--discret" onClick={() => setEdition(!edition)}>
            {edition ? 'Annuler' : 'Renommer'}
          </button>
          <BoutonDupliquer
            nomInitial={`${categorie.libelle} (copie)`}
            enCours={dupliquer.isPending}
            onConfirmer={(nom) => dupliquer.mutate({ id: categorie.id, nom })}
          />
          <BoutonSupprimer
            enCours={supprimer.isPending}
            onConfirmer={() => supprimer.mutate(categorie.id)}
          />
        </span>
      </div>
      {edition && (
        <form
          className="formulaire"
          onSubmit={(evenement) => {
            evenement.preventDefault()
            renommer.mutate(
              {
                id: categorie.id,
                // Le PUT catégorie est **total** (ADR-0020) : tout champ omis est **remis à son
                // défaut**. On renvoie donc l'entité entière — la première version n'envoyait que
                // trois champs et effaçait `ages`, `sexe` et `blason_id` à chaque renommage.
                entree: {
                  libelle,
                  arme: categorie.arme,
                  ages: categorie.ages,
                  sexe: categorie.sexe,
                  blason_id: categorie.blason_id,
                  hauteur_cm: categorie.hauteur_cm,
                },
              },
              { onSuccess: () => setEdition(false) },
            )
          }}
        >
          <input
            className="formulaire__champ"
            value={libelle}
            onChange={(e) => setLibelle(e.target.value)}
            aria-label="Nouveau libellé"
          />
          <button type="submit" disabled={renommer.isPending || libelle.trim() === ''}>
            Enregistrer
          </button>
        </form>
      )}
      <MessageErreur erreur={renommer.error} />
      <MessageErreur erreur={dupliquer.error} />
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

function LigneBlason({ blason }: { blason: Blason }) {
  const dupliquer = useDupliquerBlasonBibliotheque()
  const supprimer = useSupprimerBlasonBibliotheque()

  return (
    <li className="gabarit">
      <div className="gabarit__ligne">
        <span className="gabarit__nom">{blason.nom}</span>
        <span className="gabarit__attributs">
          {blason.capacite} archer(s) · {blason.zones.length} zone(s)
        </span>
        <span className="gabarit__actions">
          <BoutonDupliquer
            nomInitial={`${blason.nom} (copie)`}
            enCours={dupliquer.isPending}
            onConfirmer={(nom) => dupliquer.mutate({ id: blason.id, nom })}
          />
          <BoutonSupprimer
            enCours={supprimer.isPending}
            onConfirmer={() => supprimer.mutate(blason.id)}
          />
        </span>
      </div>
      {/* Un blason encore utilisé comme défaut d'une catégorie est refusé en 409 côté serveur
          (`BlasonReference`, E01US006) : l'erreur remonte telle quelle, avec son message. */}
      <MessageErreur erreur={dupliquer.error} />
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

/**
 * « Dupliquer » — la **seconde issue** du CA « modifier un officiel ».
 *
 * Face à « Renommer », qui modifie l'officiel **sur place** et le laisse officiel (le règlement
 * évolue), celle-ci détache une copie marquée « création du club » et laisse l'original intact.
 * Sans elle, la seule façon d'adapter une brique fédérale était de l'écraser — l'écrasement
 * silencieux que le CA proscrit.
 */
function BoutonDupliquer({
  nomInitial,
  enCours,
  onConfirmer,
}: {
  nomInitial: string
  enCours: boolean
  onConfirmer: (nom: string) => void
}) {
  const [ouvert, setOuvert] = useState(false)
  const [nom, setNom] = useState(nomInitial)

  if (!ouvert) {
    return (
      <button type="button" className="bouton--discret" onClick={() => setOuvert(true)}>
        Dupliquer
      </button>
    )
  }
  return (
    <>
      <input
        className="formulaire__champ"
        value={nom}
        onChange={(e) => setNom(e.target.value)}
        aria-label="Nom de la copie"
      />
      <button
        type="button"
        disabled={enCours || nom.trim() === ''}
        onClick={() => {
          onConfirmer(nom)
          setOuvert(false)
        }}
      >
        Créer la copie
      </button>
      <button type="button" className="bouton--discret" onClick={() => setOuvert(false)}>
        Annuler
      </button>
    </>
  )
}

/** Suppression à confirmation, comme partout ailleurs dans l'admin (patron `Gabarits`). */
function BoutonSupprimer({ enCours, onConfirmer }: { enCours: boolean; onConfirmer: () => void }) {
  const [confirmation, setConfirmation] = useState(false)

  if (!confirmation) {
    return (
      <button type="button" className="bouton--danger" onClick={() => setConfirmation(true)}>
        Supprimer
      </button>
    )
  }
  return (
    <>
      <button type="button" className="bouton--danger" disabled={enCours} onClick={onConfirmer}>
        Confirmer la suppression
      </button>
      <button type="button" className="bouton--discret" onClick={() => setConfirmation(false)}>
        Annuler
      </button>
    </>
  )
}

function FormulaireCategorie() {
  const [libelle, setLibelle] = useState('')
  const [arme, setArme] = useState('')
  const creer = useCreerCategorieBibliotheque()

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (libelle.trim() === '') return
    creer.mutate(
      { libelle, arme: arme.trim() === '' ? null : arme },
      {
        onSuccess: () => {
          setLibelle('')
          setArme('')
        },
      },
    )
  }

  return (
    <div>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={libelle}
          onChange={(e) => setLibelle(e.target.value)}
          placeholder="Libellé (ex. Arc Classique Sénior 1 Homme)"
          aria-label="Libellé de la catégorie"
        />
        <input
          className="formulaire__champ"
          value={arme}
          onChange={(e) => setArme(e.target.value)}
          placeholder="Arme (facultatif)"
          aria-label="Arme de la catégorie"
        />
        <div className="formulaire__actions">
          <button type="submit" disabled={creer.isPending || libelle.trim() === ''}>
            Ajouter au club
          </button>
        </div>
      </form>
      <MessageErreur erreur={creer.error} />
    </div>
  )
}

function FormulaireBlason() {
  const [nom, setNom] = useState('')
  const [taille, setTaille] = useState('1')
  const [capacite, setCapacite] = useState('1')
  const creer = useCreerBlasonBibliotheque()

  const valide =
    nom.trim() !== '' && Number(taille) > 0 && Number(taille) <= 1 && Number(capacite) >= 1

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!valide) return
    creer.mutate(
      { nom, taille: Number(taille), capacite: Number(capacite) },
      {
        onSuccess: () => {
          setNom('')
          setTaille('1')
          setCapacite('1')
        },
      },
    )
  }

  return (
    <div>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom (ex. Blason 40 cm)"
          aria-label="Nom du blason"
        />
        <input
          className="formulaire__champ"
          type="number"
          step="0.05"
          min={0.05}
          max={1}
          value={taille}
          onChange={(e) => setTaille(e.target.value)}
          // « Taille » est une **fraction de place** sur une butte, pas un diamètre — le libellé
          // doit le dire, sinon on saisit « 40 » et le placement devient absurde.
          placeholder="Place occupée sur une cible (1 = toute la butte)"
          aria-label="Place occupée sur une cible"
        />
        <input
          className="formulaire__champ"
          type="number"
          min={1}
          value={capacite}
          onChange={(e) => setCapacite(e.target.value)}
          placeholder="Archers admis"
          aria-label="Nombre d'archers admis"
        />
        <div className="formulaire__actions">
          <button type="submit" disabled={creer.isPending || !valide}>
            Ajouter au club
          </button>
        </div>
      </form>
      <MessageErreur erreur={creer.error} />
    </div>
  )
}
