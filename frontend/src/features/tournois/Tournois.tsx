// Gestion des tournois (E01US001, E01US002) — extraite de l'écran monolithique lors de la coquille
// admin (guide §8 : « aucune fonction n'est enfouie dans le fichier d'une autre »).
//
// Périmètre : créer / éditer / lister / supprimer un tournoi et piloter son **cycle de vie**. La
// création et le cycle de vie sont réservés à l'admin (E10US002) ; la **lecture** reste publique —
// sans session admin, on présente l'écran de connexion à la place du formulaire. La couche données
// reste dans `competition/` : c'est un hub partagé qu'on ne déplace pas au titre de cette US.

import { useMemo, useState } from 'react'
import { useOuvertureParAdresse } from '../../shared/navigation/useOuvertureParAdresse'
import type { ApercuJalon } from '../jalons/api'
import { useApercusJalon } from '../jalons/hooks'
import { PastillePreparation } from '../jalons/PastillePreparation'
import { useDeconnexionAdmin } from '../admin/hooks'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useSessionAdminStore } from '../../shared/stores/sessionAdminStore'
import { FriseCycleDeVie } from '../accueil/FriseCycleDeVie'
import { BadgeStatut } from '../competition/BadgeStatut'
import type { StatutTournoi, Tournoi, TypeTournoi } from '../competition/api'
import {
  useCreerTournoi,
  useModifierTournoi,
  useSupprimerTournoi,
  useTournois,
} from '../competition/hooks'
import {
  dateDuJour,
  estAujourdhui,
  filtrerParStatut,
  ordonnerTournois,
  statutsPresents,
} from './tri'

// Destination « Tournoi » de la coquille (E00US015) et accueil public (liste en lecture seule).
// Fetch interne : la feature est autonome, on ne lui passe pas la liste. Un tournoi sélectionné
// (`selectionneId`) est mis en évidence et, côté admin, coiffé de son cycle de vie.
export function GestionTournois({
  selectionneId,
  onChoisi,
  ouvrir = null,
  onOuvrir,
}: {
  selectionneId: number | null
  onChoisi: (t: Tournoi) => void
  // ⚠️ **`ouvrir` n'est pas `selectionneId`** : sélectionner désigne le tournoi sur lequel on
  // travaille, ouvrir déplie son formulaire d'édition (E16US010, ADR-0100). Les confondre ferait
  // s'ouvrir une fiche à chaque fois qu'on change de tournoi courant.
  ouvrir?: number | null
  onOuvrir?: (id: number | null) => void
}) {
  // `estAdmin` gouverne **l'affichage** des contrôles d'écriture (création, cycle de vie, édition,
  // suppression). Le **login** n'est plus ici : il vit dans `CoquilleAdmin` (porte Admin, E00US017).
  // Invariant qui garde le public : sous la porte **Public** (`AccueilPublic`), aucun jeton admin ne
  // peut exister — on n'atteint l'écran de choix que si `resoudreRole === null`, donc `!aJetonAdmin`,
  // et le public n'a aucun moyen de se logger (pas de `ConnexionAdmin` monté). `estAdmin` y est donc
  // toujours faux, ces contrôles restent masqués. Le serveur reste l'autorité en dernier ressort.
  const estAdmin = useSessionAdminStore((s) => s.jeton) !== null
  const tournois = useTournois()

  // La pastille de préparation (E16US010, A02) : « voir d'avance ce qui bloque un lancement ».
  // ⚠️ **La requête elle-même est gardée par `estAdmin`**, pas seulement son exploitation : sous
  // la porte Public cette liste est rendue sans jeton, et l'appel partirait en 401 à chaque
  // affichage. Une seule requête pour toute la liste — c'est le serveur qui agrège.
  const apercus = useApercusJalon('demarrer', estAdmin)
  const apercuParTournoi = new Map<number, ApercuJalon>(
    (apercus.data ?? []).map((a) => [a.tournoi_id, a]),
  )

  // Filtre par état (A04 : *« j'ajouterais également un filtre sur les états »*). Ensemble **vide au
  // départ** = tout est montré : un écran qui s'ouvre déjà filtré ferait chercher longtemps un
  // tournoi qui existe.
  const [statutsRetenus, setStatutsRetenus] = useState<ReadonlySet<StatutTournoi>>(new Set())

  // `useMemo` sur le `??` lui-même : sans lui, une liste absente rendrait un tableau **neuf** à
  // chaque rendu, donc les deux `useMemo` qui en dépendent recalculeraient toujours — le lint le
  // signale, et il a raison : le tri d'une liste de tournois est peu coûteux, mais la référence
  // instable se propagerait à tout ce qui prendrait `visibles` en dépendance plus tard.
  const liste = useMemo(() => tournois.data ?? [], [tournois.data])
  // L'horloge est lue **ici**, au bord — les règles de `tri.ts` la reçoivent en paramètre pour rester
  // déterministes (règle 9). `useMemo` sur la liste seule : la date du jour ne change pas assez vite
  // pour justifier un abonnement, et un tournoi consulté à minuit pile se corrigera au prochain
  // rafraîchissement de la liste.
  const aujourdhui = useMemo(() => dateDuJour(new Date()), [])
  const visibles = useMemo(
    () => ordonnerTournois(filtrerParStatut(liste, statutsRetenus)),
    [liste, statutsRetenus],
  )
  const filtres = useMemo(() => statutsPresents(liste), [liste])

  const basculerStatut = (statut: StatutTournoi) =>
    setStatutsRetenus((precedent) => {
      const suivant = new Set(precedent)
      if (!suivant.delete(statut)) suivant.add(statut)
      return suivant
    })

  // Version **fraîche** du tournoi courant : après un démarrer/terminer, la liste est invalidée et
  // re-lue, ce qui rafraîchit le statut ici sans état local à synchroniser.
  const courant =
    selectionneId === null ? null : (tournois.data?.find((t) => t.id === selectionneId) ?? null)

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Tournois</h2>

      {/* Sans ce bloc, une liste injoignable (backend coupé) se réduirait à « aucun tournoi » — un
          faux vide qui fait croire à une base vide plutôt qu'à une panne réseau. */}
      {/* DETTE-050 : rendu ad hoc non rallié à `shared/ui/texteErreur` — `error.message` brut. */}
      {tournois.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Liste des tournois injoignable — {tournois.error.message}
        </p>
      )}

      {/* Cycle de vie du tournoi courant, en tête : c'est ici, sur la destination « Tournoi », que
          se pilote son avancement (l'ancien écran monolithique le mêlait aux autres modules). */}
      {estAdmin && courant !== null && (
        <div className="tournoi-courant">
          <h3 className="carte__soustitre">
            {courant.nom} <BadgeStatut statut={courant.statut} />
          </h3>
          <FriseCycleDeVie tournoi={courant} />
        </div>
      )}

      {estAdmin && <FormulaireNouveauTournoi onChoisi={onChoisi} />}

      {liste.length > 0 && (
        <>
          <h3 className="carte__soustitre">Tournois existants</h3>

          {/* Filtre par état (A04). Des **bascules** et non un `<select>` : on veut pouvoir garder
              « en cours + prêt » ensemble, ce qu'une liste déroulante à choix unique interdit. Chaque
              bascule porte son décompte, pour qu'on sache ce qu'on écarte avant de cliquer. */}
          {filtres.length > 1 && (
            <div className="filtre-statuts" role="group" aria-label="Filtrer par état">
              <button
                type="button"
                className={
                  statutsRetenus.size === 0 ? 'filtre-statut filtre-statut--actif' : 'filtre-statut'
                }
                aria-pressed={statutsRetenus.size === 0}
                onClick={() => setStatutsRetenus(new Set())}
              >
                Tous ({liste.length})
              </button>
              {filtres.map(({ statut, nombre }) => (
                <button
                  key={statut}
                  type="button"
                  className={
                    statutsRetenus.has(statut)
                      ? 'filtre-statut filtre-statut--actif'
                      : 'filtre-statut'
                  }
                  aria-pressed={statutsRetenus.has(statut)}
                  onClick={() => basculerStatut(statut)}
                >
                  <BadgeStatut statut={statut} /> {nombre}
                </button>
              ))}
            </div>
          )}

          <ul className="liste-tournois">
            {visibles.map((t) => (
              <LigneTournoi
                key={t.id}
                tournoi={t}
                estAdmin={estAdmin}
                selectionne={t.id === selectionneId}
                aujourdhui={aujourdhui}
                onChoisi={onChoisi}
                ouvrir={ouvrir}
                onOuvrir={onOuvrir}
                apercu={apercuParTournoi.get(t.id)}
              />
            ))}
          </ul>

          {/* Un filtre qui ne rend rien doit **le dire** : sans ce mot, l'écran est indiscernable
              d'une base vide, et on cherche un tournoi qui est là. */}
          {visibles.length === 0 && (
            <p className="carte__etat">
              Aucun tournoi dans les états retenus — décochez un filtre pour élargir.
            </p>
          )}
        </>
      )}
    </section>
  )
}

// Une ligne de la liste : ouvrir le tournoi, plus (admin) l'éditer ou le supprimer. La suppression
// demande une **confirmation explicite** (deux temps) et reste indisponible tant que le tournoi est
// **en cours** (il faut d'abord le terminer, garanti aussi côté serveur, E01US002).
function LigneTournoi({
  tournoi,
  estAdmin,
  selectionne,
  aujourdhui,
  onChoisi,
  ouvrir,
  onOuvrir,
  apercu,
}: {
  tournoi: Tournoi
  estAdmin: boolean
  selectionne: boolean
  aujourdhui: string
  onChoisi: (t: Tournoi) => void
  ouvrir: number | null
  onOuvrir?: (id: number | null) => void
  apercu: ApercuJalon | undefined
}) {
  const [edition, setEdition] = useOuvertureParAdresse(tournoi.id, ouvrir, onOuvrir)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const supprimer = useSupprimerTournoi()

  if (edition) {
    return (
      <li>
        <FormulaireEditionTournoi tournoi={tournoi} onTermine={() => setEdition(false)} />
      </li>
    )
  }

  // Le serveur refuse la suppression d'un tournoi `en_cours` **ou** `en_pause`
  // (`TournoiEnCoursNonSupprimable`, 409) : la pré-vérification front couvre les deux (alignement
  // 7 statuts, E14US001) pour afficher le garde-fou **avant** le clic plutôt qu'une erreur après coup.
  const nonSupprimable = tournoi.statut === 'en_cours' || tournoi.statut === 'en_pause'

  return (
    <li className={selectionne ? 'tournoi tournoi--selectionne' : 'tournoi'}>
      <div className="tournoi__ligne">
        <button type="button" className="lien" onClick={() => onChoisi(tournoi)}>
          {tournoi.nom} — {tournoi.date}
          {tournoi.lieu ? ` · ${tournoi.lieu}` : ''} · {tournoi.type_tournoi.replace('_', ' ')}
        </button>
        <BadgeStatut statut={tournoi.statut} />
        {/* « une pastille d'alerte si tout n'est pas complet ; alerte forte si impossible de
            lancer en l'état » (A02). Elle vit **après** le statut : le statut dit où en est le
            tournoi, la pastille ce qui l'empêche d'avancer — l'ordre est celui de la lecture. */}
        <PastillePreparation apercu={apercu} />
        {/* « surtout si on est à la date prévue du tournoi » (A02) : l'ordre le fait déjà remonter,
            cette marque dit **pourquoi** il est là. Un mot et non une couleur seule (`DV-03`). */}
        {estAujourdhui(tournoi, aujourdhui) && (
          <span className="tournoi__aujourdhui">Aujourd’hui</span>
        )}
        {estAdmin && (
          <span className="tournoi__actions">
            <button type="button" className="bouton--discret" onClick={() => setEdition(true)}>
              Éditer
            </button>
            {confirmationSuppression ? (
              <>
                <button
                  type="button"
                  className="bouton--danger"
                  disabled={supprimer.isPending}
                  onClick={() => supprimer.mutate(tournoi.id)}
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
            ) : nonSupprimable ? (
              // Un tournoi en cours ou en pause n'est pas supprimable (garanti aussi côté serveur,
              // 409). On l'explique par un **texte visible** plutôt qu'un `title` sur un bouton
              // désactivé (inatteignable au clavier / lecteur d'écran — le CDC vise WCAG AA).
              <span className="tournoi__note">
                Terminez ou annulez le tournoi pour pouvoir le supprimer.
              </span>
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
        )}
      </div>
      <MessageErreur erreur={supprimer.error} />
    </li>
  )
}

// `BadgeStatut` (pastille de cycle de vie) vit désormais dans `competition/BadgeStatut`, co-localisé
// avec le type `StatutTournoi` qu'il rend : `accueil` a besoin du badge **et** `tournois` a besoin de
// la frise de `accueil` — garder le badge ici créait un cycle d'import `accueil ↔ tournois`
// (revue E14US001). Il est simplement importé en tête.

function FormulaireNouveauTournoi({ onChoisi }: { onChoisi: (t: Tournoi) => void }) {
  const [nom, setNom] = useState('')
  const [date, setDate] = useState('')
  const [lieu, setLieu] = useState('')
  const [type, setType] = useState<TypeTournoi>('non_officiel')
  const creer = useCreerTournoi()
  const deconnexion = useDeconnexionAdmin()

  // Le tarif ne se fixe plus à la création du tournoi : il vit sur chaque départ (créneau), qui se
  // configure une fois le tournoi ouvert (E02US004, ADR-0017).
  const soumissionPossible = nom.trim() !== '' && date !== ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    // Un 401 (session expirée) est géré centralement par le client HTTP (purge de session).
    creer.mutate(
      {
        nom,
        date,
        lieu: lieu.trim() || null,
        type_tournoi: type,
      },
      { onSuccess: onChoisi },
    )
  }

  return (
    <div>
      <h3 className="carte__soustitre">Nouveau tournoi</h3>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom du tournoi"
          aria-label="Nom du tournoi"
        />
        <input
          className="formulaire__champ"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          aria-label="Date du tournoi"
        />
        <input
          className="formulaire__champ"
          value={lieu}
          onChange={(e) => setLieu(e.target.value)}
          placeholder="Lieu (facultatif)"
          aria-label="Lieu du tournoi"
        />
        <select
          className="formulaire__champ"
          value={type}
          onChange={(e) => setType(e.target.value as TypeTournoi)}
          aria-label="Type de tournoi"
        >
          <option value="non_officiel">Non officiel</option>
          <option value="officiel">Officiel</option>
        </select>
        <button type="submit" disabled={creer.isPending || !soumissionPossible}>
          Créer
        </button>
      </form>
      <MessageErreur erreur={creer.error} />
      <button type="button" className="lien" onClick={() => deconnexion.mutate()}>
        Se déconnecter (admin)
      </button>
    </div>
  )
}

// Édition des métadonnées d'un tournoi (nom, date, lieu, type) — autorisée quel que soit le statut ;
// le cycle de vie évolue par ailleurs via Démarrer/Terminer.
function FormulaireEditionTournoi({
  tournoi,
  onTermine,
}: {
  tournoi: Tournoi
  onTermine: () => void
}) {
  const [nom, setNom] = useState(tournoi.nom)
  const [date, setDate] = useState(tournoi.date)
  const [lieu, setLieu] = useState(tournoi.lieu ?? '')
  const [type, setType] = useState<TypeTournoi>(tournoi.type_tournoi)
  const modifier = useModifierTournoi()

  const soumissionPossible = nom.trim() !== '' && date !== ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (!soumissionPossible) return
    modifier.mutate(
      {
        id: tournoi.id,
        entree: {
          nom,
          date,
          lieu: lieu.trim() || null,
          type_tournoi: type,
        },
      },
      { onSuccess: onTermine },
    )
  }

  return (
    <div>
      <h3 className="carte__soustitre">Modifier le tournoi</h3>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => setNom(e.target.value)}
          placeholder="Nom du tournoi"
          aria-label="Nom du tournoi"
        />
        <input
          className="formulaire__champ"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          aria-label="Date du tournoi"
        />
        <input
          className="formulaire__champ"
          value={lieu}
          onChange={(e) => setLieu(e.target.value)}
          placeholder="Lieu (facultatif)"
          aria-label="Lieu du tournoi"
        />
        <select
          className="formulaire__champ"
          value={type}
          onChange={(e) => setType(e.target.value as TypeTournoi)}
          aria-label="Type de tournoi"
        >
          <option value="non_officiel">Non officiel</option>
          <option value="officiel">Officiel</option>
        </select>
        <div className="formulaire__actions">
          <button type="submit" disabled={modifier.isPending || !soumissionPossible}>
            Enregistrer
          </button>
          <button type="button" className="bouton--discret" onClick={onTermine}>
            Annuler
          </button>
        </div>
      </form>
      <MessageErreur erreur={modifier.error} />
    </div>
  )
}

// Le pilotage du cycle de vie (démarrer, terminer, mettre en pause, archiver, annuler…) vit
// désormais dans `FriseCycleDeVie` (feature « accueil », E14US001) : une frise 7 statuts qui lit les
// transitions offertes du serveur. L'ancien `CycleDeVie` local ne couvrait que 3 statuts et bloquait
// dès `prêt`/`en_pause` (aucun bouton) — supprimé au profit de la source unique.
