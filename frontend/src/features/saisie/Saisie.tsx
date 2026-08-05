// Écran de saisie du poste de cible (E04US002) — le poste du **marqueur**.
//
// « La tablette appartient à la cible, pas à la personne » (CDC UX §7.2). Un marqueur (un archer de
// la cible, désigné FFTA B.6.1.1) tape ce que chacun annonce : une grille des 3–4 archers, un pavé
// **déduit du blason** (touches illégales absentes), le **grain de validation** affiché (D-11), le
// marqueur **discret et tapable** (D-04 : l'interface ne s'organise pas autour d'un changement rare).
//
// Périmètre de cette tranche : la **saisie** (et la ré-édition avant validation). La **validation**
// et la **correction** sont l'acte du **scoreur**, sur sa propre surface (§7.3) — hors d'ici. La
// **file hors-ligne** et la **diffusion live** sont E04US009.
//
// Depuis E04US018, l'écran a un **second état** : quand les séries de la cible sont toutes validées,
// il bascule en **panneau de routage** — « où tire-t-on ensuite ». C'est le moment exact où l'archer
// range ses flèches et s'en va : l'information doit partir avec lui. « Retour à la grille » revient
// à la saisie (CA), et le panneau reste rouvrable tant que la cible est close.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { PanneauRoutage } from '../routage/PanneauRoutage'
import { apresRetour, panneauOuvert, serieClose } from '../routage/presentation'
import type { Bareme, LigneGrille } from './api'
import { lireBrouillon, noterBrouillon, type Brouillons } from './brouillons'
import {
  useBareme,
  useDeparts,
  useFixerDepart,
  useGrain,
  useGrille,
  useRejeuFileHorsLigne,
  useSaisirVolee,
  useSerie,
  useSeries,
} from './hooks'
import {
  heureSaisie,
  libelleGrain,
  nouvelIdentifiant,
  prochaineASaisir,
  quelSaisiePar,
  totalVolee,
  voleeExistante,
} from './volees'

export function Saisie({ tournoiId, cibleIndex }: { tournoiId: number; cibleIndex: number }) {
  // Rejeu de la file hors-ligne à la reconnexion (E04US009) : monté ici, sur l'écran du poste, seul
  // endroit où l'on saisit — inutile de le faire tourner sur les écrans admin/public.
  useRejeuFileHorsLigne()

  const grille = useGrille()
  const bareme = useBareme(tournoiId)
  const grain = useGrain(tournoiId)

  const [archerChoisi, setArcherChoisi] = useState<number | null>(null)
  const [marqueur, setMarqueur] = useState<string | null>(null)

  // ⚠️ **Les frappes en cours vivent ici, pas dans le pavé.** Elles étaient un `useState` de
  // `PaveArcher`, monté avec `key={archer_id}` : **tout** ce qui démontait ce composant jetait la
  // volée en cours sans un mot, et quatre chemins le démontent — changer d'archer (le geste le plus
  // fréquent d'une cible à quatre), ouvrir « Où tire-t-on ensuite ? », changer de départ, fermer le
  // pavé. Une première correction n'avait gardé que le quatrième, le plus rare, et affirmait en
  // commentaire les avoir tous couverts (2ᵉ passe de revue, 05/08/2026).
  //
  // Remonter l'état d'un cran **supprime la classe entière de défauts** au lieu d'en garder les
  // chemins un par un : le brouillon survit au démontage, donc changer d'archer et revenir retrouve
  // la frappe telle qu'on l'avait laissée. Et comme plus rien ne se perd, la confirmation de
  // fermeture disparaît — elle criait de toute façon au loup à chaque fin de série, le tampon étant
  // pré-rempli avec la volée déjà enregistrée.
  //
  // Clé `archerId:numeroDeVolee`. Un brouillon est effacé **à l'enregistrement** : la vérité repasse
  // alors au serveur. Les brouillons d'archers disparus de la grille sont inertes (personne ne les
  // lit) et partent au prochain démontage de l'écran.
  const [brouillons, setBrouillons] = useState<Brouillons>({})
  const changerBrouillon = (archerId: number, numero: number, valeurs: string[] | null) =>
    setBrouillons((actuels) => noterBrouillon(actuels, archerId, numero, valeurs))

  // Départ courant non fixé : le serveur refuse la grille (409, ADR-0034 §1). C'est un état attendu,
  // pas un incident — on invite à choisir un départ plutôt que d'afficher une erreur.
  const besoinDepart =
    grille.isError &&
    grille.error instanceof ErreurApi &&
    grille.error.code === 'depart_courant_non_defini'

  const lignes = grille.data ?? []

  // **Le pavé est appelé, pas permanent** — retour maquettes du 04/08/2026 (S02) : la variante
  // retenue est « grille complète, pavé appelé », et l'évolution demandée est explicite, écrite deux
  // fois dans le questionnaire — *« l'appel du pavé doit se faire à la sélection de la zone de
  // saisie »*.
  //
  // L'écran ouvrait le pavé d'office sur l'archer en position A. C'était une commodité (« le pavé est
  // utilisable tout de suite ») qui coûte cher sur une cible : la grille des quatre archers, celle
  // qu'on lit pour savoir où l'on en est, était repoussée sous un pavé que personne n'avait demandé,
  // et un tap malheureux saisissait pour l'archer A — celui qu'on n'avait jamais choisi.
  //
  // `archerActif` n'a donc **plus de repli** : il vaut `null` tant qu'aucune ligne n'a été tapée. Un
  // choix devenu obsolète (changement de départ, archer retiré) referme le pavé au lieu de glisser
  // silencieusement sur un autre archer — ce qui était le vrai danger du repli.
  const premier = lignes[0]
  const archerActif =
    archerChoisi !== null && lignes.some((l) => l.archer_id === archerChoisi) ? archerChoisi : null
  // Le marqueur, lui, **garde** son repli : c'est une signature, pas une cible de frappe. Sans nom
  // par défaut, la première volée de la journée partirait avec `saisie_par: null`.
  const marqueurActif =
    marqueur !== null && lignes.some((l) => l.nom === marqueur) ? marqueur : (premier?.nom ?? null)

  const ligneActive = lignes.find((l) => l.archer_id === archerActif) ?? null

  // Bascule en panneau de routage (E04US018). « Close » = toutes les volées du barème saisies **et**
  // verrouillées par le scoreur (c'est lui qui clôt une série, pas le marqueur) — **ou** l'archer
  // est forfait (E04US015 : il reste dans la grille et sa série ne se complétera jamais ; sans cette
  // clause, une seule DSQ priverait toute la cible du panneau). Les séries sont relues via le
  // **même** cache que les lignes de la grille (`useSeries`), donc sans requête en plus.
  const archerIds = lignes.map((l) => l.archer_id)
  const series = useSeries(tournoiId, archerIds)
  const nbVolees = bareme.data?.nb_volees ?? null
  const cibleClose =
    lignes.length > 0 &&
    lignes.every((ligne, i) => serieClose(series[i]?.data?.volees ?? [], nbVolees, ligne.forfait))

  // Ouverture **automatique** quand la cible a fini (CA), et « Retour à la grille » qui referme
  // (CA). Le panneau reste **ouvrable à la main** en toutes circonstances : un archer absent, une
  // série restée en erreur ou un cas qu'on n'a pas prévu ne doit pas pouvoir condamner la
  // fonctionnalité pour les trois autres archers — une porte automatique a toujours besoin d'une
  // poignée. Refermer une consultation **manuelle** ne consomme pas la bascule automatique à venir
  // (`apresRetour`) : sans cette nuance, jeter un œil au panneau en pleine saisie éteindrait
  // silencieusement le CA central de l'US. `panneauFerme` est par ailleurs réinitialisé quand la
  // grille change de **composition** (changement de départ), pas quand elle change d'**ordre** (un
  // échange de positions A↔B au plan ne doit pas rouvrir sous les doigts un panneau qu'on vient de
  // fermer). Ajustement d'état **au rendu** (pas en effet), comme le tampon du pavé.
  const signatureGrille = [...archerIds].sort((a, b) => a - b).join(',')
  const [ancreGrille, setAncreGrille] = useState(signatureGrille)
  const [panneauFerme, setPanneauFerme] = useState(false)
  const [panneauForce, setPanneauForce] = useState(false)
  if (ancreGrille !== signatureGrille) {
    setAncreGrille(signatureGrille)
    setPanneauFerme(false)
    setPanneauForce(false)
  }
  const ouvert = panneauOuvert({ cibleClose, ferme: panneauFerme, force: panneauForce })

  if (ouvert) {
    return (
      <div className="saisie">
        <div className="saisie__entete">
          <strong>Cible {cibleIndex}</strong>
        </div>
        <PanneauRoutage
          tournoiId={tournoiId}
          archerIds={archerIds}
          titrePanneau="Où tire-t-on ensuite ?"
          onRetour={() => {
            const suite = apresRetour({ cibleClose })
            setPanneauForce(suite.force)
            setPanneauFerme(suite.ferme)
          }}
        />
      </div>
    )
  }

  return (
    <div className="saisie">
      <div className="saisie__entete">
        <strong>Cible {cibleIndex}</strong>
        {lignes.length > 0 && (
          <SelecteurMarqueur lignes={lignes} marqueur={marqueurActif} onChoisir={setMarqueur} />
        )}
      </div>

      {lignes.length > 0 && (
        <button
          type="button"
          className="lien"
          onClick={() => {
            setPanneauFerme(false)
            setPanneauForce(true)
          }}
        >
          Où tire-t-on ensuite ?
        </button>
      )}

      {besoinDepart || grille.isSuccess ? (
        <SelecteurDepart tournoiId={tournoiId} obligatoire={besoinDepart} />
      ) : null}

      {grille.isError && !besoinDepart && <MessageErreur erreur={grille.error} />}

      {grille.isSuccess && lignes.length === 0 && (
        <p className="saisie__vide" role="status">
          Aucun archer placé sur cette cible pour ce départ.
        </p>
      )}

      {grille.isSuccess && lignes.length > 0 && (
        <>
          <ul className="saisie__grille">
            {lignes.map((ligne) => (
              <LigneArcher
                key={ligne.archer_id}
                tournoiId={tournoiId}
                ligne={ligne}
                nbVolees={bareme.data?.nb_volees ?? null}
                actif={ligne.archer_id === archerActif}
                // ⚠️ **Pas une bascule.** Une première version refermait le pavé quand on re-tapait
                // la ligne ouverte — geste « inverse » séduisant, mais `PaveArcher` porte son tampon
                // de frappe en état local : le refermer **jette la volée en cours**, sans un mot.
                // Sur une cible, ce tap arrive tout seul (on re-touche le nom pour lire le cumul).
                // La fermeture passe donc par **un seul geste explicite**, le bouton « Fermer » du
                // pavé, qui sait ce qu'il y a dans le tampon et demande confirmation s'il n'est pas
                // vide (revue du 05/08/2026, axes C1 et adversarial).
                onSelectionner={() => setArcherChoisi(ligne.archer_id)}
              />
            ))}
          </ul>

          {ligneActive !== null && bareme.data !== null && bareme.data !== undefined ? (
            <PaveArcher
              key={ligneActive.archer_id}
              tournoiId={tournoiId}
              ligne={ligneActive}
              bareme={bareme.data}
              marqueur={marqueurActif}
              brouillons={brouillons}
              onBrouillon={changerBrouillon}
              onFermer={() => setArcherChoisi(null)}
            />
          ) : bareme.isSuccess && bareme.data === null ? (
            <p className="saisie__vide" role="status">
              Barème de qualification non défini pour ce tournoi : configurez la phase avant de
              saisir.
            </p>
          ) : (
            // Sans cette invite, une grille sans pavé se lit comme un écran en lecture seule : rien
            // ne dit que taper un nom ouvre la saisie.
            <p className="saisie__invite" role="status">
              Touchez un archer pour ouvrir le pavé de saisie.
            </p>
          )}
        </>
      )}

      <p className="saisie__grain">{libelleGrain(grain.data ?? null)}</p>
    </div>
  )
}

// Le marqueur : discret par défaut (« Marqueur : NOM »), une liste qui se déplie au besoin (D-04).
// Chaque volée enregistrera ce nom (`saisie_par`) — l'équivalent numérique de la signature.
function SelecteurMarqueur({
  lignes,
  marqueur,
  onChoisir,
}: {
  lignes: LigneGrille[]
  marqueur: string | null
  onChoisir: (nom: string) => void
}) {
  const [ouvert, setOuvert] = useState(false)
  return (
    <div className="saisie__marqueur">
      <button
        type="button"
        className="lien saisie__marqueur-libelle"
        aria-expanded={ouvert}
        onClick={() => setOuvert((o) => !o)}
      >
        Marqueur : <strong>{marqueur ?? '—'}</strong> ▾
      </button>
      {ouvert && (
        <ul className="saisie__marqueur-choix" role="listbox" aria-label="Choisir le marqueur">
          {lignes.map((ligne) => (
            <li key={ligne.archer_id}>
              <button
                type="button"
                className="lien"
                aria-selected={ligne.nom === marqueur}
                onClick={() => {
                  onChoisir(ligne.nom)
                  setOuvert(false)
                }}
              >
                {ligne.nom} {ligne.prenom}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// « Mettre le poste en mode départ X » (ADR-0034). Affiché en grand tant que le départ n'est pas
// fixé (`obligatoire`), sinon repliable (« Changer de départ ») — un poste sert le même départ toute
// la matinée, le sélecteur ne doit pas encombrer.
function SelecteurDepart({ tournoiId, obligatoire }: { tournoiId: number; obligatoire: boolean }) {
  const departs = useDeparts(tournoiId)
  const fixer = useFixerDepart()
  const [ouvert, setOuvert] = useState(false)
  const deplie = obligatoire || ouvert

  return (
    <div className="saisie__departs">
      {obligatoire ? (
        <p className="saisie__vide" role="status">
          Choisissez le départ que sert cette cible pour afficher la grille.
        </p>
      ) : (
        <button type="button" className="lien" onClick={() => setOuvert((o) => !o)}>
          Changer de départ
        </button>
      )}
      {deplie && (
        <div className="saisie__departs-liste">
          {departs.data?.map((depart) => (
            <button
              key={depart.id}
              type="button"
              className="bouton--discret"
              disabled={fixer.isPending}
              aria-pressed={fixer.data?.depart_id === depart.id}
              onClick={() => {
                fixer.mutate(depart.id, { onSuccess: () => setOuvert(false) })
              }}
            >
              Départ {depart.numero}
              {depart.horaire !== null ? ` — ${depart.horaire}` : ''}
            </button>
          ))}
          <MessageErreur erreur={fixer.error} />
        </div>
      )}
    </div>
  )
}

// Une ligne de la grille : position, nom, cumul (validé) et avancement. Tapable pour devenir
// l'archer **actif** (celui dont le pavé saisit). Cible tactile ≥ 48 px (écran de saisie).
function LigneArcher({
  tournoiId,
  ligne,
  nbVolees,
  actif,
  onSelectionner,
}: {
  tournoiId: number
  ligne: LigneGrille
  nbVolees: number | null
  actif: boolean
  onSelectionner: () => void
}) {
  const serie = useSerie(tournoiId, ligne.archer_id)
  const volees = serie.data?.volees ?? []
  const nbSaisies = volees.length
  const cumul = serie.data?.cumul ?? 0

  return (
    <li>
      <button
        type="button"
        className={`saisie__ligne${actif ? ' saisie__ligne--actif' : ''}`}
        // `aria-current` et non `aria-pressed` : le bouton **désigne**, il ne bascule plus. Annoncer
        // « pressé » promettrait un dépressage que le code ne fait pas (2ᵉ passe de revue).
        aria-current={actif ? 'true' : undefined}
        onClick={onSelectionner}
      >
        <span className="saisie__position">{ligne.position}</span>
        <span className="saisie__nom">
          {ligne.nom} <span className="saisie__prenom">{ligne.prenom}</span>
        </span>
        <span className="saisie__avancement">
          {nbSaisies}/{nbVolees ?? '?'} volées
        </span>
        {/* Le cumul de série, **en permanence** (S02, question 3 : *« en permanence, c'est un bon
            rappel sur la cible »*). Il l'était déjà ; il le reste maintenant que le pavé ne masque
            plus la grille. */}
        <span className="saisie__cumul">{cumul}</span>
      </button>

      {/* **Relecture par les autres archers** (S02, question 2 : *« oui »* — contre-vérification
          FFTA B.6.1.1). Chaque volée montre son total, en lecture seule ; le cadenas dit ce que le
          scoreur a déjà verrouillé, donc ce qui n'est plus discutable à la cible.
          ⚠️ **Hors du `<button>`, et c'est le point.** Placée dedans, cette bande — la plus large
          zone tapable de la ligne — déclenchait `onSelectionner`, donc **fermait le pavé** (le bouton
          est une bascule) et **démontait `PaveArcher` avec son tampon de frappe** : l'archer qui se
          penchait pour vérifier ses volées faisait disparaître les flèches que le marqueur venait de
          taper, sans un mot. Le geste de *vérifier* ne doit rien changer à l'état de *saisir* —
          c'était l'intention de départ, elle n'était pas tenue (revue du 05/08/2026, axes C1 et
          adversarial). `role="group"` plutôt qu'`aria-label` sur un `<span>` nu : sans rôle, le
          libellé était ignoré des lecteurs d'écran. */}
      {nbVolees !== null && nbVolees > 0 && (
        <span className="saisie__relecture" role="group" aria-label={`Volées de ${ligne.nom}`}>
          {Array.from({ length: nbVolees }, (_, i) => {
            const volee = volees.find((v) => v.numero === i + 1)
            if (volee === undefined) {
              return (
                <span key={i} className="saisie__relecture-volee saisie__relecture-volee--vide">
                  ·
                </span>
              )
            }
            const classes = volee.verrouillee
              ? 'saisie__relecture-volee saisie__relecture-volee--verrou'
              : 'saisie__relecture-volee'
            // Les valeurs flèche par flèche sont **écrites**, pas mises en `title` : une infobulle au
            // survol n'existe pas sur une tablette, c'est-à-dire sur l'appareil visé. B.6.1.1 porte
            // sur les valeurs, pas sur un cumul (revue, axe B).
            return (
              <span key={i} className={classes}>
                <span className="saisie__relecture-total">{totalVolee(volee.valeurs)}</span>
                <span className="saisie__relecture-detail">{volee.valeurs.join(' ')}</span>
              </span>
            )
          })}
        </span>
      )}
    </li>
  )
}

// Le pavé de l'archer actif : les zones **de son blason** (touches illégales absentes), la volée en
// cours de frappe, correction (Effacer) et enregistrement. La saisie passe par la file d'écriture
// serveur ; l'identifiant rend le geste **idempotent** (ADR-0036) — un identifiant neuf par volée.
// Un **navigateur de volées** permet de revenir sur une volée déjà saisie tant qu'elle n'est pas
// verrouillée (CA « édition avant validation »).
function PaveArcher({
  tournoiId,
  ligne,
  bareme,
  marqueur,
  brouillons,
  onBrouillon,
  onFermer,
}: {
  tournoiId: number
  ligne: LigneGrille
  bareme: Bareme
  marqueur: string | null
  // Les frappes en cours, **détenues par le parent** (cf. son commentaire) : le pavé les lit et les
  // écrit, il ne les possède pas — c'est ce qui les fait survivre à son démontage.
  brouillons: Brouillons
  onBrouillon: (archerId: number, numero: number, valeurs: string[] | null) => void
  // Depuis que le pavé est **appelé** (S02), il doit aussi pouvoir se refermer sans passer par la
  // ligne : sur un téléphone, la grille est parfois hors de l'écran quand le pavé est ouvert.
  onFermer: () => void
}) {
  const serie = useSerie(tournoiId, ligne.archer_id)
  const saisir = useSaisirVolee(tournoiId, ligne.archer_id)
  const volees = serie.data?.volees ?? []

  // Volée visée : le choix explicite (navigateur), sinon la prochaine non saisie.
  const [numeroChoisi, setNumeroChoisi] = useState<number | null>(null)
  const numeroActif = numeroChoisi ?? prochaineASaisir(volees, bareme.nb_volees)
  const existante = voleeExistante(volees, numeroActif)
  const verrouillee = existante?.verrouillee ?? false
  const valeursExistantes = existante?.valeurs

  // Le tampon est **dérivé** : le brouillon du parent s'il existe, sinon le contenu persisté de la
  // volée visée. Plus d'ancre ni de réinitialisation au rendu — enregistrer efface le brouillon, ce
  // qui fait retomber la lecture sur le serveur. Un état de moins, et le pattern d'ajustement au
  // rendu (délicat) disparaît avec lui.
  const buffer = lireBrouillon(brouillons, ligne.archer_id, numeroActif) ?? valeursExistantes ?? []

  if (ligne.zones.length === 0) {
    return (
      <p className="saisie__vide" role="status">
        Pavé indisponible pour {ligne.nom} : blason non configuré.
      </p>
    )
  }

  // Tant que la série n'est pas chargée, `volees` est vide et `numeroActif` pointerait la volée 1
  // par défaut : on désactive la frappe pour ne pas saisir « à l'aveugle » puis voir le tampon se
  // réinitialiser à l'arrivée des données (perte silencieuse). Fenêtre courte en LAN, verrou franc.
  const chargee = serie.isSuccess
  const complet = buffer.length >= bareme.nb_fleches_par_volee
  const ajouter = (valeur: string) => {
    if (chargee && !complet && !verrouillee) {
      onBrouillon(ligne.archer_id, numeroActif, [...buffer, valeur])
    }
  }
  const effacer = () => onBrouillon(ligne.archer_id, numeroActif, buffer.slice(0, -1))
  const enregistrer = () => {
    saisir.mutate(
      {
        tournoi_id: tournoiId,
        archer_id: ligne.archer_id,
        numero: numeroActif,
        valeurs: buffer,
        // Nouvelle volée → marqueur actif ; ré-édition → `null` (le domaine préserve l'original).
        saisie_par: quelSaisiePar(existante, marqueur),
        identifiant_saisie: nouvelIdentifiant(),
      },
      // De retour en mode « prochaine à saisir » : après avoir enregistré la volée visée, on avance.
      // Le brouillon est **effacé** : la vérité repasse au serveur, et une réouverture du pavé ne
      // ressort pas une frappe déjà enregistrée.
      {
        onSuccess: () => {
          onBrouillon(ligne.archer_id, numeroActif, null)
          setNumeroChoisi(null)
        },
      },
    )
  }

  return (
    <div className="saisie__pave">
      <NavigateurVolees
        nbVolees={bareme.nb_volees}
        volees={volees}
        numeroActif={numeroActif}
        onChoisir={setNumeroChoisi}
      />

      <div className="saisie__pave-entete">
        <span>
          Volée {numeroActif}/{bareme.nb_volees} — <strong>{ligne.nom}</strong>
        </span>
        {/* Le cumul de série **suit le pavé** (S02) : quand la grille est repoussée hors de l'écran
            sur un téléphone, c'est ici qu'on relit « où j'en suis ». */}
        <span className="saisie__cumul-serie">Cumul {serie.data?.cumul ?? 0}</span>
        <span className="saisie__total">
          {buffer.length}/{bareme.nb_fleches_par_volee} · {totalVolee(buffer)} pts
        </span>
        {/* Fermeture **directe, et sans question** : le brouillon est détenu par le parent, donc
            refermer ne perd rien — rouvrir le pavé le retrouve. Une confirmation ici aurait crié au
            loup à chaque fin de série (le tampon est pré-rempli avec la volée déjà enregistrée). */}
        <button
          type="button"
          className="lien saisie__fermer-pave"
          onClick={onFermer}
          aria-label="Fermer le pavé de saisie"
        >
          Fermer
        </button>
      </div>

      {existante !== null && (
        <p className="saisie__meta">
          Saisie par <strong>{existante.saisie_par ?? '—'}</strong>
          {existante.saisie_le !== null ? ` à ${heureSaisie(existante.saisie_le)}` : ''}
          {existante.validee_par !== null ? ` · validée par ${existante.validee_par}` : ''}
          {existante.en_attente === true ? ' · en attente d’envoi' : ''}
        </p>
      )}

      {verrouillee && (
        <p className="saisie__vide" role="status">
          Volée validée par {existante?.validee_par ?? 'le scoreur'} — sa correction relève du
          scoreur.
        </p>
      )}

      <div className="saisie__buffer" aria-live="polite">
        {Array.from({ length: bareme.nb_fleches_par_volee }, (_, i) => (
          <span key={i} className="saisie__fleche">
            {buffer[i] ?? '·'}
          </span>
        ))}
      </div>

      <div className="saisie__zones">
        {ligne.zones.map((zone) => (
          <button
            key={zone}
            type="button"
            className="saisie__zone"
            disabled={!chargee || complet || verrouillee || saisir.isPending}
            onClick={() => ajouter(zone)}
          >
            {zone}
          </button>
        ))}
      </div>

      <div className="saisie__actions">
        <button
          type="button"
          className="bouton--discret"
          disabled={buffer.length === 0 || verrouillee || saisir.isPending}
          onClick={effacer}
        >
          Effacer
        </button>
        <button
          type="button"
          disabled={!chargee || !complet || verrouillee || saisir.isPending}
          onClick={enregistrer}
        >
          {saisir.isPending ? 'Enregistrement…' : 'Enregistrer la volée'}
        </button>
      </div>

      <MessageErreur erreur={saisir.error} />
    </div>
  )
}

// Navigateur de volées : une pastille par volée du barème. Saisie = pleine, verrouillée = cadenassée,
// visée = surlignée. Tapable pour revenir corriger une volée non encore validée (édition avant
// validation), ou repartir sur la suivante.
function NavigateurVolees({
  nbVolees,
  volees,
  numeroActif,
  onChoisir,
}: {
  nbVolees: number
  volees: { numero: number; verrouillee: boolean }[]
  numeroActif: number
  onChoisir: (numero: number) => void
}) {
  return (
    <div className="saisie__nav" role="group" aria-label="Volées">
      {Array.from({ length: nbVolees }, (_, i) => {
        const numero = i + 1
        const volee = volees.find((v) => v.numero === numero)
        const classes = [
          'saisie__nav-volee',
          volee !== undefined ? 'saisie__nav-volee--saisie' : '',
          volee?.verrouillee ? 'saisie__nav-volee--verrou' : '',
          numero === numeroActif ? 'saisie__nav-volee--actif' : '',
        ]
          .filter((c) => c !== '')
          .join(' ')
        return (
          <button
            key={numero}
            type="button"
            className={classes}
            aria-pressed={numero === numeroActif}
            onClick={() => onChoisir(numero)}
          >
            {numero}
          </button>
        )
      })}
    </div>
  )
}
