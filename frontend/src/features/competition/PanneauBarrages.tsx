// Barrages de places décisives (E06US003, ADR-0066) — surface **admin** du classement.
//
// Deux moitiés, dans l'ordre où l'organisateur les vit : les égalités que le format réclame de
// trancher au tir (« faire tirer »), puis les barrages en cours, avec la saisie de leur manche.
//
// Cette carte ne s'affiche que s'il y a une egalite signalee ou un barrage en cours : le defaut du
// produit reste l'ex aequo partage (E06US001), et une alerte ambre permanente sur les tournois qui
// ne barrent pas serait du bruit sur l'ecran qu'on regarde toute la journee. Le **departage
// manuel** (poule, Big Shoot Off) vit hors de cette carte, dans `VueClassement` : il doit rester
// atteignable en permanence, mais replie, sans allumer d'alerte.
//
// ⚠️ **Un groupe se retire en entier.** Le serveur refuse une manche où une partie seulement du
// groupe a tiré — deux ex æquo dont un seul a retiré ne se départagent sur rien. Le formulaire
// soumet donc **tout le groupe** d'un coup, et un tireur qu'on n'a pas renseigné part « absent »
// seulement si on l'a coché : sans cela, un oubli de saisie ferait perdre quelqu'un qui a tiré.

import { useState } from 'react'
import { BoutonConfirme } from '../../shared/ui/BoutonConfirme'
import type { Barrage, EgaliteADepartager, LigneClassement, PorteeBarrage, TirBarrage } from './api'
import {
  correspond,
  depuisTirs,
  mancheComplete,
  type SaisieTir,
  TIR_VIERGE,
  versTirs,
} from './barrage'
import {
  useAnnoncerBarrage,
  useAnnulerBarrage,
  useBarrages,
  useCloreBarrage,
  useSaisirMancheBarrage,
} from './hooks'

/** Ce que chaque portée vient trancher — le panneau sert les trois (ADR-0066). */
const LIBELLE_PORTEE: Record<PorteeBarrage, string> = {
  qualification: 'Qualification',
  poule: 'Poule',
  big_shoot_off: 'Big Shoot Off',
}

export function PanneauBarrages({
  tournoiId,
  egalites,
  lignes,
}: {
  tournoiId: number
  egalites: EgaliteADepartager[]
  /** Le classement affiché — sert à **nommer** les archers d'un barrage.
   *
   * Le barrage ne connaît que des identifiants (le moteur oppose des participants opaques,
   * ADR-0028) ; c'est la couche d'affichage qui résout l'identité. On réutilise les lignes déjà
   * chargées plutôt que d'interroger `/archers` : elles sont là, à jour, et une seconde source
   * afficherait un nom périmé après une correction d'état civil. */
  lignes: LigneClassement[]
}) {
  const barrages = useBarrages(tournoiId)
  // ⚠️ **Les barrages CLOS sont rendus eux aussi**, et c'est un correctif de revue. Les filtrer
  // rendait inatteignable le seul chemin de réparation d'un verdict acté par erreur : le barrage
  // quittait l'écran au clic sur « Acter », l'égalité disparaissait du classement (le verdict
  // s'appliquant), et la carte entière s'effaçait. Le juge qui avait inversé deux flèches sur la
  // dernière place qualificative envoyait le mauvais archer au tableau, définitivement — le
  // dommage même que le correctif serveur disait avoir fermé.
  const tous = barrages.data ?? []
  const nomDe = (archerId: number) => {
    const ligne = lignes.find((candidate) => candidate.archer_id === archerId)
    return ligne ? `${ligne.nom} ${ligne.prenom}` : `Archer ${archerId}`
  }

  // La carte d'**alerte** ne s'affiche que s'il y a quelque chose a faire ou a suivre : c'est la
  // promesse « aucun bruit par defaut », et l'etape 1 de la recette la verifie explicitement. Le
  // depliant de departage manuel, lui, vit hors de cette carte (`VueClassement`) : il doit rester
  // atteignable en permanence sans allumer une alerte ambre toute la journee.
  if (egalites.length === 0 && tous.length === 0) {
    return null
  }

  // ⚠️ **L'ambre signale « il reste à faire », pas « il s'est passé quelque chose ».** Depuis que
  // les barrages clos sont rendus, la carte reste affichée jusqu'à la fin du tournoi — sans ce
  // distinguo, un tournoi terminé et entièrement réglé garderait une alerte permanente, et l'ambre
  // ne signalerait plus rien.
  const aFaire = egalites.length > 0 || tous.some((b) => !b.clos || b.perime || b.incoherent)

  return (
    <section className={`carte carte--barrages${aFaire ? ' carte--barrages-actif' : ''}`}>
      <h3 className="carte__soustitre">Barrages — places décisives</h3>
      {egalites.length > 0 && (
        <ul className="barrages__egalites">
          {egalites.map((egalite) => (
            <EgaliteALancer
              key={egalite.rang}
              tournoiId={tournoiId}
              egalite={egalite}
              nomDe={nomDe}
              dejaOuvert={tous.some(
                (barrage) =>
                  // Portee **et** tireurs : un barrage de poule portant un rang masquait le bouton
                  // de l'egalite de qualification du meme rang, et un barrage **perime** (annonce
                  // avant qu'un archer ne rejoigne l'egalite) le masquait aussi — l'organisateur
                  // faisait alors tirer un groupe incomplet sans que rien ne l'explique.
                  barrage.portee === 'qualification' &&
                  barrage.rang_dispute === egalite.rang &&
                  // Bloquant tant qu'il n'est pas **acté et sain** : un barrage encore ouvert (même
                  // sur d'autres tireurs) ou **périmé** (fût-il acté) fait refuser l'annonce côté
                  // serveur. Offrir le bouton conduisait à deux cartes « acté » au même rang, aux
                  // verdicts inversés, sans le moindre signal — l'organisateur prenant le gros
                  // bouton plutôt que la phrase qui lui disait d'annuler d'abord.
                  (!barrage.clos || barrage.perime),
              )}
            />
          ))}
        </ul>
      )}
      {tous.map((barrage) => (
        <BarrageEnCours key={barrage.id} tournoiId={tournoiId} barrage={barrage} nomDe={nomDe} />
      ))}
    </section>
  )
}

/** Une égalité signalée par le format, avec le bouton qui l'ouvre. */
function EgaliteALancer({
  tournoiId,
  egalite,
  nomDe,
  dejaOuvert,
}: {
  tournoiId: number
  egalite: EgaliteADepartager
  nomDe: (archerId: number) => string
  dejaOuvert: boolean
}) {
  const annoncer = useAnnoncerBarrage(tournoiId)
  return (
    <li className="barrages__egalite">
      <span>
        <strong>{egalite.rang}ᵉ place</strong> — {egalite.archer_ids.map(nomDe).join(', ')}
      </span>
      {!dejaOuvert && (
        <button
          type="button"
          onClick={() => annoncer.mutate({ rang: egalite.rang })}
          disabled={annoncer.isPending}
        >
          Faire tirer
        </button>
      )}
      {annoncer.isError && (
        <span className="carte__etat carte__etat--erreur" role="alert">
          {annoncer.error.message}
        </span>
      )}
    </li>
  )
}

/** Un barrage ouvert : ce qu'il reste à faire tirer, son verdict, et les deux portes de sortie. */
function BarrageEnCours({
  tournoiId,
  barrage,
  nomDe,
}: {
  tournoiId: number
  barrage: Barrage
  nomDe: (archerId: number) => string
}) {
  const clore = useCloreBarrage(tournoiId)
  const annuler = useAnnulerBarrage(tournoiId)
  const [correction, setCorrection] = useState(false)
  const derniere = barrage.manches.length
  const titre =
    barrage.rang_dispute !== null
      ? `${barrage.rang_dispute}ᵉ place`
      : LIBELLE_PORTEE[barrage.portee]

  return (
    <article className="barrage">
      <h4 className="barrage__titre">
        {titre}
        {barrage.portee !== 'qualification' && barrage.rang_dispute !== null && (
          // Un barrage de poule **portant un rang** s'affichait « 2ᵉ place », indiscernable de
          // celui de qualification au même rang.
          <span className="barrage__portee">{` · ${LIBELLE_PORTEE[barrage.portee]}`}</span>
        )}
        {barrage.clos ? ' — acté' : ` — manche ${derniere + 1}`}
        {barrage.reference && (
          // La **reference** (numero de poule, de manche) est le seul champ qui distingue deux
          // barrages de meme portee : la saisir sans jamais la reafficher laissait l'organisateur
          // piloter un discriminant invisible.
          <span className="barrage__portee">{` · ${barrage.reference}`}</span>
        )}
        {barrage.incoherent && (
          <span className="carte__etat carte__etat--erreur" role="alert">
            {' · '}Saisie incohérente : corrigez une manche ou annulez ce barrage.
          </span>
        )}
      </h4>
      {barrage.perime ? (
        // Périmé : le groupe d'ex æquo a changé depuis l'annonce. On **retire** le formulaire de
        // saisie et « Acter » — les laisser conduisait à faire tirer un groupe incomplet, à
        // l'acter en 200, et à ne voir aucun rang bouger, sans un mot d'explication.
        <p className="carte__etat carte__etat--erreur" role="alert">
          Ce barrage ne porte plus sur les archers à départager : le classement a bougé depuis son
          annonce. Annulez-le, puis relancez le barrage depuis l&apos;égalité signalée.
        </p>
      ) : barrage.est_resolu ? (
        <>
          <p className="barrage__verdict">
            Départagé : {barrage.ordre.map(nomDe).join(' devant ')}
          </p>
          {!barrage.clos && (
            <button
              type="button"
              onClick={() => clore.mutate(barrage.id)}
              disabled={clore.isPending}
            >
              Acter le résultat
            </button>
          )}
        </>
      ) : (
        // Un groupe par égalité restante : ils se retirent **séparément**, et les fusionner
        // ferait passer un tireur à 8 devant un tireur à 10 que le tir précédent avait départagé.
        barrage.groupes_a_rejouer.map((groupe) => (
          <SaisieGroupe
            // ⚠️ **La clé porte le numéro de manche.** Un retir non concluant rend *le même*
            // groupe, donc la même clé : React réutilisait l'instance et la manche suivante
            // s'ouvrait **pré-remplie** avec les scores précédents, bouton déjà actif. Un clic
            // réflexe enregistrait alors le tir précédent comme retir.
            key={`${derniere}-${groupe.join('-')}`}
            tournoiId={tournoiId}
            barrageId={barrage.id}
            groupe={groupe}
            nomDe={nomDe}
          />
        ))
      )}
      <div className="barrage__actions">
        {derniere > 0 && (
          <button type="button" onClick={() => setCorrection((ouvert) => !ouvert)}>
            {correction ? 'Fermer la correction' : `Corriger la manche ${derniere}`}
          </button>
        )}
        {/* Geste **irreversible** : les manches saisies partent avec le barrage, et le bouton est
            colle a « Corriger la manche N » sur une interface tactile. On confirme des qu'il y a
            quelque chose a perdre, et on laisse le clic unique sur un barrage vierge — un dialogue
            sur un barrage vide serait une friction sans enjeu. Vrai dialogue depuis A15 (04/08/2026)
            au lieu d'un `window.confirm` : la perte se chiffre, donc elle se lit. */}
        {derniere > 0 ? (
          <BoutonConfirme
            libelle="Annuler ce barrage"
            className="bouton--danger"
            disabled={annuler.isPending}
            enCours={annuler.isPending}
            titre="Annuler ce barrage ?"
            message={`${derniere} manche(s) deja saisie(s) seront effacees.`}
            detail={barrage.clos && !barrage.perime ? 'Les archers repartageront leur rang.' : null}
            libelleConfirmer="Annuler le barrage"
            ton="danger"
            onConfirmer={() => annuler.mutate(barrage.id)}
          />
        ) : (
          <button
            type="button"
            className="bouton--danger"
            onClick={() => annuler.mutate(barrage.id)}
            disabled={annuler.isPending}
          >
            Annuler ce barrage
          </button>
        )}
      </div>
      {correction && derniere > 0 && (
        // ⚠️ **Corriger la manche N tronque les suivantes** (le serveur s'en charge) : la partition
        // ayant changé, les retirs qui en découlaient n'ont plus d'objet. C'est le geste que
        // promettait le CA — « corriger une flèche corrige le classement » — et qui n'existait dans
        // aucun écran : le formulaire disparaissait dès que le barrage était résolu.
        <SaisieGroupe
          key={`correction-${derniere}`}
          tournoiId={tournoiId}
          barrageId={barrage.id}
          groupe={(barrage.manches[derniere - 1] ?? []).map((tir) => tir.archer_id)}
          nomDe={nomDe}
          manche={derniere}
          initial={barrage.manches[derniere - 1]}
          surSucces={() => setCorrection(false)}
        />
      )}
      {clore.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          {clore.error.message}
        </p>
      )}
      {annuler.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          {annuler.error.message}
        </p>
      )}
    </article>
  )
}

/** Le formulaire d'un groupe à départager : une flèche par tireur, la manche soumise d'un bloc. */
function SaisieGroupe({
  tournoiId,
  barrageId,
  groupe,
  nomDe,
  manche,
  initial,
  surSucces,
}: {
  tournoiId: number
  barrageId: number
  groupe: number[]
  nomDe: (archerId: number) => string
  /** Fourni = on **réécrit** cette manche (correction) ; absent = on ajoute la suivante. */
  manche?: number
  /** Les tirs déjà saisis, pour pré-remplir une correction. */
  initial?: TirBarrage[]
  surSucces?: () => void
}) {
  const [saisies, setSaisies] = useState<Record<number, SaisieTir>>(() => depuisTirs(initial))
  const saisir = useSaisirMancheBarrage(tournoiId)
  const lire = (archerId: number) => saisies[archerId] ?? TIR_VIERGE
  const modifier = (archerId: number, champ: Partial<SaisieTir>) =>
    setSaisies((actuel) => ({ ...actuel, [archerId]: { ...lire(archerId), ...champ } }))

  // Le groupe se retire en entier : tant qu'un tireur n'est ni noté ni déclaré absent, on ne
  // soumet pas. Le serveur refuserait de toute façon (« un groupe se retire en entier ou pas du
  // tout ») — on l'annonce ici plutôt que de laisser partir une requête vouée au 422.
  const complet = mancheComplete(groupe, saisies)

  const soumettre = () =>
    saisir.mutate(
      { barrageId, tirs: versTirs(groupe, saisies), manche },
      { onSuccess: () => surSucces?.() },
    )

  return (
    <div className="barrage__groupe">
      {groupe.map((archerId) => {
        const tir = lire(archerId)
        return (
          <div key={archerId} className="barrage__tireur">
            <span className="barrage__nom">{nomDe(archerId)}</span>
            <label>
              Flèche{' '}
              <input
                type="number"
                inputMode="numeric"
                min={0}
                max={10}
                value={tir.score}
                disabled={tir.absent}
                onChange={(e) => modifier(archerId, { score: e.target.value })}
              />
            </label>
            <label title="Distance du centre à l'impact, en dixièmes de millimètre. À ne renseigner que si les flèches sont à égalité et que le juge a mesuré — une mesure absente n'est pas une distance nulle : le barrage se retire.">
              Distance (⅒ mm){' '}
              <input
                type="number"
                inputMode="numeric"
                min={0}
                value={tir.distance}
                disabled={tir.absent}
                onChange={(e) => modifier(archerId, { distance: e.target.value })}
              />
            </label>
            <label title="Absent au barrage annoncé : l'archer est déclaré perdant (art. B.6.5.2.4).">
              <input
                type="checkbox"
                checked={tir.absent}
                onChange={(e) => modifier(archerId, { absent: e.target.checked })}
              />{' '}
              Absent
            </label>
          </div>
        )
      })}
      <button type="button" onClick={soumettre} disabled={!complet || saisir.isPending}>
        {manche === undefined ? 'Enregistrer la manche' : `Corriger la manche ${manche}`}
      </button>
      {!complet && (
        <p className="carte__etat">
          Un groupe se retire en entier : notez la flèche de chaque tireur, ou déclarez-le absent.
        </p>
      )}
      {saisir.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          {saisir.error.message}
        </p>
      )}
    </div>
  )
}

/** Départager des archers **hors qualification** — poule ou Big Shoot Off (ADR-0066).
 *
 * ⚠️ **Pourquoi un formulaire plutôt qu'un bouton comme en qualification.** Là-haut, l'application
 * *sait* qui est à égalité : elle lit le classement. Ici elle ne le sait pas — aucun classement de
 * poule ni aucun état de Big Shoot Off n'est calculé nulle part (DETTE-028) —, donc c'est
 * l'organisateur qui désigne les tireurs. Le barrage se conduit ensuite exactement pareil ; seul
 * son verdict ne retourne dans aucun classement, faute de classement à alimenter.
 *
 * Vit **hors de la carte d'alerte** et replié par défaut : il doit rester atteignable en
 * permanence (rien ne peut le signaler), sans pour autant allumer une alerte ambre toute la
 * journée sur un tournoi qui ne fait ni poule ni Big Shoot Off.
 */
export function DepartageManuel({
  tournoiId,
  lignes,
}: {
  tournoiId: number
  lignes: LigneClassement[]
}) {
  const [portee, setPortee] = useState<'poule' | 'big_shoot_off'>('poule')
  const [reference, setReference] = useState('')
  const [recherche, setRecherche] = useState('')
  const [choisis, setChoisis] = useState<number[]>([])
  const annoncer = useAnnoncerBarrage(tournoiId)

  const basculer = (archerId: number) =>
    setChoisis((actuel) =>
      actuel.includes(archerId)
        ? actuel.filter((candidat) => candidat !== archerId)
        : [...actuel, archerId],
    )

  // À 120 inscrits, cocher deux noms dans une liste triée par rang est une corvée tactile : on
  // filtre. Les archers **déjà cochés** restent toujours visibles, sinon un filtre les ferait
  // disparaître de l'écran tout en comptant dans la sélection.
  const visibles = lignes.filter(
    (ligne) => choisis.includes(ligne.archer_id) || correspond(ligne.nom, ligne.prenom, recherche),
  )

  const soumettre = () =>
    annoncer.mutate(
      {
        portee,
        archer_ids: choisis,
        reference: reference.trim() === '' ? null : reference.trim(),
      },
      {
        onSuccess: () => {
          setChoisis([])
          setReference('')
        },
      },
    )

  return (
    <details className="barrages__manuel">
      <summary>Départager d&apos;autres archers (poule, Big Shoot Off)</summary>
      <p className="carte__aide">
        L&apos;application ne calcule pas encore les classements de poule ni les manches de Big
        Shoot Off : désignez vous-même les archers à départager. Le barrage se tire ensuite
        normalement, mais son résultat ne remonte dans aucun classement.
      </p>
      <label>
        Départage{' '}
        <select
          value={portee}
          onChange={(e) => setPortee(e.target.value as 'poule' | 'big_shoot_off')}
        >
          <option value="poule">de poule</option>
          <option value="big_shoot_off">de Big Shoot Off</option>
        </select>
      </label>
      <label>
        Repère{' '}
        <input
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          placeholder={portee === 'poule' ? 'ex. Poule A' : 'ex. manche 3'}
        />
      </label>
      <label>
        Chercher{' '}
        <input
          value={recherche}
          onChange={(e) => setRecherche(e.target.value)}
          placeholder="nom de l'archer"
        />
      </label>
      <ul className="barrages__choix">
        {visibles.map((ligne) => (
          <li key={ligne.archer_id}>
            <label>
              <input
                type="checkbox"
                checked={choisis.includes(ligne.archer_id)}
                onChange={() => basculer(ligne.archer_id)}
              />{' '}
              {ligne.nom} {ligne.prenom}
            </label>
          </li>
        ))}
      </ul>
      <button type="button" onClick={soumettre} disabled={choisis.length < 2 || annoncer.isPending}>
        Faire tirer les archers sélectionnés ({choisis.length})
      </button>
      {choisis.length < 2 && (
        <p className="carte__etat">Un barrage départage au moins deux archers.</p>
      )}
      {annoncer.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          {annoncer.error.message}
        </p>
      )}
    </details>
  )
}
