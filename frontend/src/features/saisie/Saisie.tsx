// Écran de saisie du poste de cible (E04US002) — le poste du **marqueur**.
//
// « La tablette appartient à la cible, pas à la personne » (CDC UX §7.2) : une grille des 3-4
// archers, un pavé **déduit du blason**, le grain de validation affiché (D-11), le marqueur discret
// et tapable (D-04). ⚠️ Périmètre : la **saisie** et la ré-édition avant validation — la validation
// et la correction sont l'acte du scoreur, sur sa propre surface. Depuis E04US018, second état :
// cible entièrement validée → **panneau de routage**, au moment où l'archer range ses flèches.

import { useEffect, useRef, useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { PanneauRoutage } from '../routage/PanneauRoutage'
import { apresRetour, panneauOuvert } from '../routage/presentation'
import type { Bareme, LigneGrille } from './api'
import { noterBrouillon, type Brouillons } from './brouillons'
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
import { etatLigne, libelleCase, totalAffiche } from './ligneArcher'
import { classesPastille, complementMeta, estRefusDePreseance, etatPave } from './pave'
import {
  affichagePoste,
  archerActifParmi,
  cibleClose as estCibleClose,
  marqueurActifParmi,
  ouvertureDeLArcher,
  signatureComposition,
  type Ouverture,
} from './poste'
import {
  libelleGrain,
  nouvelIdentifiant,
  voleeApresEnregistrement,
  quelSaisiePar,
  cumulSaisi,
  flecheVisee,
  frapper,
  totalVolee,
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
  // volée en cours sans un mot, et quatre chemins le démontent — changer d'archer, ouvrir le
  // panneau de routage, changer de départ, fermer le pavé. Remonter l'état d'un cran **supprime la
  // classe entière de défauts** au lieu d'en garder les chemins un par un, et la confirmation de
  // fermeture disparaît avec. Clé `archerId:numeroDeVolee` ; un brouillon est effacé **à
  // l'enregistrement**, la vérité repassant alors au serveur.
  const [brouillons, setBrouillons] = useState<Brouillons>({})
  const changerBrouillon = (archerId: number, numero: number, valeurs: string[] | null) =>
    setBrouillons((actuels) => noterBrouillon(actuels, archerId, numero, valeurs))
  // Quelle volée est ouverte, et quelle flèche la prochaine frappe remplace (E17US011). Détenu ici
  // pour la même raison que les brouillons — le pavé est remonté à chaque changement d'archer — et
  // **un seul** : la ligne de l'archer actif et le pavé le lisent tous deux (`voleeOuverte`).
  const [ouverture, setOuverture] = useState<Ouverture | null>(null)

  const lignes = grille.data ?? []
  const affichage = affichagePoste({
    enErreur: grille.isError,
    erreur: grille.error,
    succes: grille.isSuccess,
    nbLignes: lignes.length,
  })

  // **Le pavé est appelé, pas permanent** (S02, cf. `archerActifParmi`) : la grille des quatre
  // archers, celle qu'on lit pour savoir où l'on en est, n'est plus repoussée sous un pavé d'office.
  const archerActif = archerActifParmi(lignes, archerChoisi)
  const marqueurActif = marqueurActifParmi(lignes, marqueur)

  const ligneActive = lignes.find((l) => l.archer_id === archerActif) ?? null
  // Ajustement au rendu, comme `panneauFerme` : cf. `ouvertureDeLArcher`.
  const ouvertureActive = ouvertureDeLArcher(ouverture, archerActif)
  if (ouverture !== null && ouvertureActive === null) setOuverture(null)

  // Bascule en panneau de routage (E04US018), cf. `cibleClose`. Les séries sont relues via le
  // **même** cache que les lignes de la grille (`useSeries`), donc sans requête en plus.
  const archerIds = lignes.map((l) => l.archer_id)
  const series = useSeries(tournoiId, archerIds)
  const cibleClose = estCibleClose(
    lignes,
    series.map((serie) => serie.data?.volees),
    bareme.data?.nb_volees ?? null,
  )

  // Ouverture **automatique** quand la cible a fini (CA), « Retour à la grille » qui referme, et
  // panneau **ouvrable à la main** en toutes circonstances : un cas imprévu ne doit pas condamner
  // la fonctionnalité pour les trois autres archers — une porte automatique a toujours besoin d'une
  // poignée. ⚠️ Refermer une consultation **manuelle** ne consomme pas la bascule automatique à
  // venir, sans quoi jeter un œil au panneau éteindrait le CA central. `panneauFerme` est
  // réinitialisé quand la grille change de **composition**, pas d'**ordre**. Ajustement au rendu.
  const signatureGrille = signatureComposition(archerIds)
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
          <h2 className="saisie__cible">Cible {cibleIndex}</h2>
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
      {/* ⚠️ **La confirmation, pas « zéro ligne ».** `lignes.length === 0` seul couvrait aussi le
          chargement et l'erreur dure : le numéro s'affichait en 48 px puis retombait à 22 px à
          chaque montage, et au-dessus d'un message d'erreur. Ici, l'état « Rattaché » de S01 — le
          départ reste à choisir, ou la grille est vide et le serveur a répondu. */}
      <div
        className={`saisie__entete${affichage.confirmation ? ' saisie__entete--confirmation' : ''}`}
      >
        {/* `h2` et non `strong` : c'est le seul titre de l'écran de travail, donc le point d'entrée
            d'une navigation par titres — la coquille ne porte plus que le `h1` de l'application. */}
        <h2 className="saisie__cible">Cible {cibleIndex}</h2>
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

      {affichage.selecteurDepart ? (
        <SelecteurDepart tournoiId={tournoiId} obligatoire={affichage.besoinDepart} />
      ) : null}

      {affichage.messageErreur && <MessageErreur erreur={grille.error} />}

      {affichage.grilleVide && (
        <p className="saisie__vide" role="status">
          Aucun archer placé sur cette cible pour ce départ.
        </p>
      )}

      {affichage.travail && (
        // ⚠️ Cette enveloppe n'est pas cosmétique : elle **ancre le pavé en bas** (`App.css`). Empilé
        // sans ancrage, il s'ouvrait sous la ligne de flottaison — invisible sans défiler, pour le
        // geste que S03 dit « répété ~4 300 fois par départ ». Le pavé reste **appelé** (S02).
        <div className="saisie__travail">
          <ul className="saisie__grille">
            {lignes.map((ligne) => (
              <LigneArcher
                key={ligne.archer_id}
                tournoiId={tournoiId}
                ligne={ligne}
                bareme={bareme.data ?? null}
                brouillons={brouillons}
                actif={ligne.archer_id === archerActif}
                ouverture={ouvertureActive?.archerId === ligne.archer_id ? ouvertureActive : null}
                onViser={(numero, fleche) => {
                  setArcherChoisi(ligne.archer_id)
                  setOuverture({ archerId: ligne.archer_id, numero, fleche })
                }}
                // ⚠️ **Pas une bascule** : re-taper la ligne ouverte ne referme pas le pavé. Sur une
                // cible ce tap arrive tout seul (on re-touche le nom pour lire le cumul), et une
                // fermeture accidentelle ferait perdre le fil de la volée en cours. La fermeture
                // passe par **un geste explicite**, le bouton « Fermer ».
                // ⚠️ Le motif historique — « le refermer jette le tampon de frappe » — **ne vaut
                // plus** : les brouillons vivent dans `Saisie` depuis, donc refermer ne perd rien
                // (cf. `brouillons` plus haut). Le geste reste, sa raison a changé.
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
              ouverture={ouvertureActive}
              onOuvrir={(o) => setOuverture({ archerId: ligneActive.archer_id, ...o })}
              onFermer={() => {
                setArcherChoisi(null)
                setOuverture(null)
              }}
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
        </div>
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
  const conteneur = useRef<HTMLDivElement>(null)

  // ⚠️ **Le panneau recouvre la première ligne d'archer** depuis qu'il est hors du flux (il poussait
  // la grille de ~90 px, cf. `App.css`). Un recouvrement sans porte de sortie bloque la cible
  // tactile la plus tapée de l'écran : « j'ouvre pour vérifier, je referme » doit exister.
  useEffect(() => {
    if (!ouvert) return
    const fermer = (e: MouseEvent) => {
      if (!conteneur.current?.contains(e.target as Node)) setOuvert(false)
    }
    const auClavier = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOuvert(false)
    }
    document.addEventListener('pointerdown', fermer)
    document.addEventListener('keydown', auClavier)
    return () => {
      document.removeEventListener('pointerdown', fermer)
      document.removeEventListener('keydown', auClavier)
    }
  }, [ouvert])

  return (
    <div className="saisie__marqueur" ref={conteneur}>
      <button
        type="button"
        className="lien saisie__marqueur-libelle"
        aria-expanded={ouvert}
        onClick={() => setOuvert((o) => !o)}
      >
        Marqueur : <strong>{marqueur ?? '—'}</strong> ▾
      </button>
      {ouvert && (
        <div className="saisie__marqueur-panneau">
          {/* S04 : la planche porte cette phrase et son verdict dit pourquoi — « sans elle, le geste
              paraît administratif ». Une liste nue de quatre noms ne dit pas ce qu'on engage. */}
          <p className="saisie__marqueur-pourquoi">
            Le marqueur est l’archer qui tient la tablette. Son nom accompagne chaque volée saisie :
            c’est la première marque, celle que le scoreur vient contresigner. Les volées déjà
            saisies gardent le nom de qui les a entrées.
          </p>
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
        </div>
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

// Une ligne de la grille — S02 : `pos | nom | fl fl fl | somme`, la volée **en cours** portée par
// la ligne elle-même (E17US011), plus l'avancement et le cumul **saisi** (cf. `cumulSaisi`). Le nom
// désigne l'archer actif ; une case de flèche le désigne **et** vise cette flèche.
function LigneArcher({
  tournoiId,
  ligne,
  bareme,
  brouillons,
  actif,
  ouverture,
  onSelectionner,
  onViser,
}: {
  tournoiId: number
  ligne: LigneGrille
  bareme: Bareme | null
  brouillons: Brouillons
  actif: boolean
  // L'ouverture de `Saisie`, pour l'archer actif seulement.
  ouverture: { numero: number | null; fleche: number | null } | null
  onSelectionner: () => void
  onViser: (numero: number, fleche: number | null) => void
}) {
  const serie = useSerie(tournoiId, ligne.archer_id)
  const volees = serie.data?.volees ?? []
  const nbVolees = bareme?.nb_volees ?? null
  const table = bareme?.points_par_zone ?? null
  const { nbSaisies, cumul, numero, enCours, verrouillee, caseEnCours } = etatLigne({
    archerId: ligne.archer_id,
    volees,
    serieLue: serie.isSuccess,
    bareme,
    brouillons,
    ouverture,
    actif,
  })

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
          {nbSaisies}/{nbVolees ?? '?'} volées · cumul
        </span>
        {/* Le cumul de série, **en permanence** (S02, question 3 : *« en permanence, c'est un bon
            rappel sur la cible »*). ⚠️ Le cumul **saisi**, pas celui du serveur : voir `cumulSaisi`
            — l'officiel ne compte que les volées validées et restait à 0 toute la série. */}
        <span className="saisie__cumul">{cumul}</span>
      </button>

      {/* ⚠️ **Des boutons voisins du bouton de ligne, jamais imbriqués** : un `<button>` dans un
          `<button>` est invalide, et le tap remonterait jusqu'à `setArcherChoisi`. Ici chaque case
          désigne l'archer ET la flèche, par son propre geste. */}
      {numero !== null && bareme !== null && (
        <span
          className="saisie__volee-en-cours"
          role="group"
          aria-label={`Volée ${numero} de ${ligne.nom}`}
        >
          {Array.from({ length: bareme.nb_fleches_par_volee }, (_, i) => (
            <button
              key={i}
              type="button"
              className={i === caseEnCours ? 'saisie__case saisie__case--en-cours' : 'saisie__case'}
              aria-label={libelleCase(i, ligne.nom, enCours[i])}
              // ⚠️ Série pas encore lue : `numero` vaudrait 1 et le toucher figerait le pavé sur la
              // volée 1 — le garde-fou `serieChargee` du pavé (`etatPave`), repris ici.
              disabled={!serie.isSuccess || verrouillee}
              onClick={() => onViser(numero, flecheVisee(i, enCours))}
            >
              {enCours[i] ?? ''}
            </button>
          ))}
          <span className="saisie__somme">{totalAffiche(enCours, table)}</span>
        </span>
      )}

      {/* **Relecture par les autres archers** (S02, question 2 — contre-vérification FFTA
          B.6.1.1). Chaque volée montre son total, en lecture seule ; le cadenas dit ce que le
          scoreur a déjà verrouillé, donc ce qui n'est plus discutable à la cible. */}

      {/* ⚠️ **Hors du bouton, et c'est le point.** Placée dedans, cette bande — la plus large
          zone tapable de la ligne — ferait **changer d'archer actif** au moindre coup d'œil aux
          volées : le `onClick` de la ligne est `setArcherChoisi`. `role=group` : sans rôle, le
          libellé était ignoré des lecteurs d'écran.
          ⚠️ Le motif d'origine (« cela démontait `PaveArcher` avec son tampon de frappe ») **ne
          vaut plus** depuis que les brouillons vivent dans `Saisie`. */}
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
                <span className="saisie__relecture-total">
                  {totalAffiche(volee.valeurs, table)}
                </span>
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
  ouverture,
  onOuvrir,
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
  // L'ouverture détenue par `Saisie` : la volée choisie (`null` = la prochaine à saisir) et la
  // flèche que la prochaine frappe remplace (`null` = à la suite).
  ouverture: { numero: number | null; fleche: number | null } | null
  onOuvrir: (ouverture: { numero: number | null; fleche: number | null }) => void
  // Depuis que le pavé est **appelé** (S02), il doit aussi pouvoir se refermer sans passer par la
  // ligne : sur un téléphone, la grille est parfois hors de l'écran quand le pavé est ouvert.
  onFermer: () => void
}) {
  const serie = useSerie(tournoiId, ligne.archer_id)
  const saisir = useSaisirVolee(tournoiId, ligne.archer_id)
  const volees = serie.data?.volees ?? []
  const {
    numeroActif,
    fleche,
    existante,
    verrouillee,
    buffer,
    frappable,
    zonesActives,
    effacable,
    enregistrable,
  } = etatPave({
    archerId: ligne.archer_id,
    volees,
    bareme,
    brouillons,
    ouverture,
    serieChargee: serie.isSuccess,
    envoiEnCours: saisir.isPending,
  })

  if (ligne.zones.length === 0) {
    return (
      <p className="saisie__vide" role="status">
        Pavé indisponible pour {ligne.nom} : blason non configuré.
      </p>
    )
  }

  const ajouter = (valeur: string) => {
    if (!frappable) return
    const suivant = frapper(buffer, valeur, fleche, bareme.nb_fleches_par_volee)
    if (suivant === null) return
    onBrouillon(ligne.archer_id, numeroActif, suivant)
    // La correction faite, retour au fil de la volée — sur la **même** volée.
    if (fleche !== null) onOuvrir({ numero: numeroActif, fleche: null })
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
          onOuvrir({ numero: voleeApresEnregistrement(volees, numeroActif), fleche: null })
        },
        // ⚠️ Le brouillon s'efface AUSSI sur un refus de préséance, sans quoi le pavé continuait
        // d'afficher les flèches refusées sous le message « le score affiché fait foi » — qui
        // devenait faux à l'écran même qui l'affiche (relevé en revue). Le tampon retombe alors
        // sur la valeur serveur, que l'invalidation d'`onError` vient de rafraîchir.
        onError: (erreur: Error) => {
          if (estRefusDePreseance(erreur)) onBrouillon(ligne.archer_id, numeroActif, null)
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
        onChoisir={(numero) => onOuvrir({ numero, fleche: null })}
      />

      <div className="saisie__pave-entete">
        <span>
          Volée {numeroActif}/{bareme.nb_volees} — <strong>{ligne.nom}</strong>
        </span>
        {/* Le cumul de série **suit le pavé** (S02) : quand la grille est repoussée hors de l'écran
            sur un téléphone, c'est ici qu'on relit « où j'en suis ». */}
        <span className="saisie__cumul-serie">
          Cumul saisi {cumulSaisi(serie.data?.volees ?? [], bareme.points_par_zone)}
        </span>
        <span className="saisie__total">
          {buffer.length}/{bareme.nb_fleches_par_volee} ·{' '}
          {totalVolee(buffer, bareme.points_par_zone)} pts
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
          {complementMeta(existante)}
        </p>
      )}

      {verrouillee && (
        <p className="saisie__vide" role="status">
          Volée validée par {existante?.validee_par ?? 'le scoreur'} — sa correction relève du
          scoreur.
        </p>
      )}

      {existante?.en_correction === true && (
        <p className="saisie__rendue" role="status">
          Volée <strong>en correction</strong> — rendue par{' '}
          {existante.correction_ouverte_par ?? 'le scoreur'}. Ressaisissez-la ; son score reste au
          classement, et le scoreur la revalidera.
        </p>
      )}

      {/* La volée tapée et ses actions sur un rang, les touches sur le suivant : le pavé est ancré
          en bas de l'écran (E17US011), chaque rang pris sur la grille se paie en archers cachés. */}
      <div className="saisie__pave-frappe">
        <div className="saisie__buffer" aria-live="polite">
          {Array.from({ length: bareme.nb_fleches_par_volee }, (_, i) => (
            <span
              key={i}
              className={i === fleche ? 'saisie__fleche saisie__fleche--visee' : 'saisie__fleche'}
            >
              {buffer[i] ?? '·'}
            </span>
          ))}
        </div>

        <div className="saisie__actions">
          <button type="button" className="bouton--discret" disabled={!effacable} onClick={effacer}>
            Effacer
          </button>
          <button type="button" disabled={!enregistrable} onClick={enregistrer}>
            {saisir.isPending ? 'Enregistrement…' : 'Enregistrer la volée'}
          </button>
        </div>
      </div>

      <div className="saisie__zones">
        {ligne.zones.map((zone) => (
          <button
            key={zone}
            type="button"
            className="saisie__zone"
            disabled={!zonesActives}
            onClick={() => ajouter(zone)}
          >
            {zone}
          </button>
        ))}
      </div>

      <MessageErreurSaisie erreur={saisir.error} />
    </div>
  )
}

// Message d'erreur d'une saisie de volée. Un `409 ecriture_de_role_inferieur` (E16US020) n'est pas
// un incident dur mais un **arbitrage** : ton ambre (DV-03), non bloquant. Le serveur nomme déjà le
// rôle qui a écrit ; l'écran ajoute le recours, sans quoi le marqueur ne sait pas quoi faire de ce
// refus. Le reste passe par `MessageErreur`.
// ⚠️ DETTE-100 : ce rendu n'est atteignable par AUCUN écran — la tablette est le seul appelant de
// `saisirVolee`, et deux postes sont à rôle égal (ADR-0107 §3). Il sert le jour où l'admin saisit.
function MessageErreurSaisie({ erreur }: { erreur: Error | null }) {
  if (estRefusDePreseance(erreur)) {
    return (
      <p className="placement__alerte" role="alert">
        {erreur.message} Le score affiché est celui qui fait foi : signalez l’erreur à
        l’organisateur.
      </p>
    )
  }
  return <MessageErreur erreur={erreur} />
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
        const classes = classesPastille(numero, volee, numeroActif)
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
