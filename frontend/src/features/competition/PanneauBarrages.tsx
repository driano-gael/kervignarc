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
import { usePhases } from '../saisie-duels/hooks'
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
  departId,
  egalites,
  lignes,
}: {
  tournoiId: number
  /** Le créneau dont on affiche le classement : un barrage s'y rattache (ADR-0075). */
  departId: number
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
  //
  // ⚠️ **…mais uniquement ceux de CE créneau** (ADR-0075, revue E01US025, axe adversarial). La
  // route reste au niveau tournoi ; le filtre est donc ici. Le serveur avait été corrigé sur ce
  // point (`ServiceBarrage._meme_endroit` lit `par_depart`), le miroir client ne l'avait pas suivi.
  // Sans lui, deux créneaux ayant chacun une égalité au **même rang** — cas ordinaire, les rangs se
  // répètent d'un départ à l'autre — se voyaient comme « le même endroit » : `dejaOuvert` passait à
  // `true` et **retirait du DOM** le bouton « Faire tirer » de l'après-midi. Le serveur aurait
  // accepté l'annonce ; l'organisateur n'avait plus aucun chemin pour départager sa dernière place
  // qualificative. Les cartes du matin s'affichaient de surcroît sous l'en-tête de l'après-midi,
  // sans rien qui les distingue, et allumaient l'alerte ambre.
  const tous = (barrages.data ?? []).filter((barrage) => barrage.depart_id === departId)
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
              departId={departId}
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
  departId,
  egalite,
  nomDe,
  dejaOuvert,
}: {
  tournoiId: number
  /** Le créneau où se dispute cette place (ADR-0075) : le serveur l'exige à l'annonce. */
  departId: number
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
          onClick={() => annoncer.mutate({ depart_id: departId, rang: egalite.rang })}
          disabled={annoncer.isPending}
        >
          Faire tirer
        </button>
      )}
      {/* DETTE-050 : ce fichier porte **cinq** rendus ad hoc non ralliés à
          `shared/ui/texteErreur` (celui-ci, `clore`, `annuler`, `saisir`, et le second
          `annoncer` plus bas) — `error.message` interpolé brut, donc « TypeError: Failed to
          fetch » à l'écran sur coupure LAN. À traiter d'un bloc, pas au fil de l'eau. */}
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
            message={`${derniere} manche(s) déjà saisie(s) seront effacées.`}
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
        // DETTE-050
        <p className="carte__etat carte__etat--erreur" role="alert">
          {clore.error.message}
        </p>
      )}
      {annuler.isError && (
        // DETTE-050
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
        // DETTE-050
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
 * *sait* qui est à égalité : elle lit le classement, donc elle propose. Ici l'organisateur désigne
 * les tireurs lui-même.
 *
 * ⚠️ **Ce paragraphe disait « aucun classement de poule n'est calculé nulle part » — c'est faux
 * depuis E05US023** (ADR-0083). Le classement de poule existe, l'écran de saisie l'affiche, et le
 * verdict d'un barrage de portée `poule` **referme** ce classement (`ServicePoules`
 * `_verdicts_de_barrage`). Ce qui reste vrai, et qui justifie le formulaire : la **désignation**
 * n'est pas automatisée ici — l'écran de saisie des poules *annonce* le barrage requis, il n'ouvre
 * pas le formulaire à la place de l'organisateur. Le Big Shoot Off, lui, reste entièrement manuel
 * jusqu'à `E05US028` (reste de `DETTE-028`).
 *
 * Vit **hors de la carte d'alerte** et replié par défaut : il doit rester atteignable en
 * permanence (rien ne peut le signaler), sans pour autant allumer une alerte ambre toute la
 * journée sur un tournoi qui ne fait ni poule ni Big Shoot Off.
 */
export function DepartageManuel({
  tournoiId,
  departId,
  lignes,
}: {
  tournoiId: number
  /** Le créneau dont on affiche le classement : un barrage s'y rattache (ADR-0075). */
  departId: number
  lignes: LigneClassement[]
}) {
  const [portee, setPortee] = useState<'poule' | 'big_shoot_off'>('poule')
  const [reference, setReference] = useState('')
  const [recherche, setRecherche] = useState('')
  const [choisis, setChoisis] = useState<number[]>([])
  // `phaseId` et `rang` **situent** le barrage de poule, et ils sont l'un et l'autre indispensables
  // au verdict — c'est le correctif du bloquant relevé en revue d'E05US023. Sans `phase_id`,
  // `ServicePoules._verdicts_de_barrage` écarte le barrage (il filtre sur l'égalité des phases, et
  // `None` n'égale aucune phase) ; sans `rang`, `Barrage.verdict()` rend un ordre vide, donc
  // `_appliquer_verdicts` n'a rien à appliquer. Deux pannes indépendantes, l'une et l'autre
  // silencieuses : le barrage se tirait, se clôturait, et le classement de la poule restait ex æquo.
  const [phaseId, setPhaseId] = useState<number | null>(null)
  const [rang, setRang] = useState('')
  const phases = usePhases(departId)
  const poulesDispo = (phases.data ?? []).filter((phase) => phase.type === 'poules')
  const annoncer = useAnnoncerBarrage(tournoiId)

  // Un barrage de poule n'est annonçable que **situé**. On le vérifie ici plutôt que de laisser
  // partir la requête : le serveur l'accepterait (les deux champs sont facultatifs au DTO, parce
  // qu'un Big Shoot Off désigne un sortant et non une place), et l'organisateur croirait le barrage
  // opérant jusqu'à découvrir, la poule close, qu'il n'a rien refermé.
  const rangSaisi = Number(rang)
  const situe =
    portee !== 'poule' ||
    (phaseId !== null && rang.trim() !== '' && Number.isInteger(rangSaisi) && rangSaisi >= 1)

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
        depart_id: departId,
        portee,
        archer_ids: choisis,
        reference: reference.trim() === '' ? null : reference.trim(),
        // Uniquement en poule : en Big Shoot Off, `_coherence_du_regime` accepte `phase_id`, mais il
        // n'y a aucune phase où retourner un verdict, et le `rang` n'y désigne pas une place.
        ...(portee === 'poule' ? { phase_id: phaseId, rang: rangSaisi } : {}),
      },
      {
        onSuccess: () => {
          setChoisis([])
          setReference('')
          setRang('')
        },
      },
    )

  return (
    <details className="barrages__manuel">
      <summary>Départager d&apos;autres archers (poule, Big Shoot Off)</summary>
      <p className="carte__aide">
        Désignez les archers à départager. En <strong>poule</strong>, l&apos;écran de saisie vous
        signale quand un barrage est requis, et le verdict <strong>referme le classement</strong> de
        la poule concernée. Pour un Big Shoot Off, le résultat ne remonte encore dans aucun
        classement.
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
      {portee === 'poule' && (
        <>
          <label>
            Phase de poules{' '}
            <select
              value={phaseId ?? ''}
              onChange={(e) => setPhaseId(e.target.value === '' ? null : Number(e.target.value))}
            >
              <option value="">Choisir une phase…</option>
              {poulesDispo.map((phase) => (
                <option key={phase.id} value={phase.id}>
                  Phase {phase.ordre} — poules
                </option>
              ))}
            </select>
          </label>
          <label>
            Rang disputé{' '}
            <input
              type="number"
              min={1}
              inputMode="numeric"
              value={rang}
              onChange={(e) => setRang(e.target.value)}
              placeholder="ex. 2"
            />
          </label>
          <p className="carte__aide">
            Le rang <strong>dans la poule</strong> — celui que l&apos;écran de saisie marque
            d&apos;un « = ». C&apos;est lui que le verdict départage : sans lui, le barrage se tire
            sans rien refermer.
          </p>
          {phases.isSuccess && poulesDispo.length === 0 && (
            <p className="carte__etat">Aucune phase de poules dans ce créneau.</p>
          )}
        </>
      )}
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
      <button
        type="button"
        onClick={soumettre}
        disabled={choisis.length < 2 || !situe || annoncer.isPending}
      >
        Faire tirer les archers sélectionnés ({choisis.length})
      </button>
      {choisis.length < 2 && (
        <p className="carte__etat">Un barrage départage au moins deux archers.</p>
      )}
      {choisis.length >= 2 && !situe && (
        <p className="carte__etat">
          Indiquez la phase de poules et le rang disputé : c&apos;est ce qui permet au verdict de
          refermer le classement de la poule.
        </p>
      )}
      {annoncer.isError && (
        // DETTE-050
        <p className="carte__etat carte__etat--erreur" role="alert">
          {annoncer.error.message}
        </p>
      )}
    </details>
  )
}
