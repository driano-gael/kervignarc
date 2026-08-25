// Identité visuelle du tournoi (E16US006, absorbe E01US016) — écran de préparation, admin.
//
// « L'identité est une **destination de préparation** » (`D-28`), et `P-6` le redit : *tout ce qui
// s'identifie se prépare à l'avance*. L'organisateur y fournit **un logo par marque et deux couleurs
// d'accent, rien d'autre** — le reste du chrome est dérivé par le serveur (`DV-06`).
//
// ⚠️ **Cet écran ne s'habille pas lui-même.** `D-27` : l'identité touche l'appli publique et l'écran
// de salle, jamais l'admin ni la saisie — « le jour J, un bénévole n'a pas le temps de réapprendre
// des repères visuels ». L'organisateur voit donc le rendu dans des **vignettes d'aperçu**, pas en
// repeignant la page sous ses pieds. C'est aussi ce que demande `DV-05` : « aperçu sur les surfaces
// réelles, pas un nuancier ».

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { AccentDecline, EmplacementLogo, Identite as IdentiteDTO, JetonsDeMarque } from './api'
import { urlDuLogo } from './api'
import {
  useApercuIdentite,
  useDeposerLogo,
  useEnregistrerAccents,
  useIdentite,
  useRetirerLogo,
} from './hooks'
import './identite.css'

export function Identite({ tournoiId }: { tournoiId: number }) {
  const identite = useIdentite(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Identité visuelle du tournoi</h3>
      <p className="carte__aide">
        Deux couleurs et deux logos, c’est tout : le reste des nuances est calculé pour rester
        lisible en thème sombre comme en thème clair. Cette identité habille{' '}
        <strong>l’écran de salle et l’appli du public</strong> — jamais l’administration ni la
        saisie, qui restent l’outil.
      </p>
      {identite.isPending && <p className="carte__etat">Chargement…</p>}
      {identite.isError && <MessageErreur erreur={identite.error} />}
      {identite.isSuccess && (
        <>
          <ReglageDesAccents
            tournoiId={tournoiId}
            identite={identite.data}
            // Clé sur les valeurs serveur : le formulaire se re-sème si l'identité change côté
            // serveur, sans état à synchroniser à la main. Même patron que `BaremeQualification`.
            key={`${identite.data.primaire.couleur}-${identite.data.secondaire.couleur}`}
          />
          <LesDeuxLogos tournoiId={tournoiId} identite={identite.data} />
        </>
      )}
    </section>
  )
}

// —————————————————————————————————————————————————————————————————————————————————————————————
// Les deux accents

function ReglageDesAccents({ tournoiId, identite }: { tournoiId: number; identite: IdentiteDTO }) {
  const [primaire, setPrimaire] = useState(identite.primaire.couleur)
  const [secondaire, setSecondaire] = useState(identite.secondaire.couleur)
  const apercu = useApercuIdentite({ primaire, secondaire })
  const enregistrer = useEnregistrerAccents(tournoiId)

  // L'aperçu tant qu'il répond, l'identité enregistrée sinon (première frappe, saisie incomplète).
  // Jamais de zone vide : le contrôle est « à la saisie », il doit rester affiché pendant la frappe.
  const affiche = apercu.data ?? identite

  return (
    <form
      onSubmit={(evenement) => {
        evenement.preventDefault()
        enregistrer.mutate({ primaire, secondaire })
      }}
    >
      {!identite.reglee && (
        <p className="carte__etat">
          Aucune couleur choisie : ce tournoi <strong>hérite de l’identité du club</strong>.
        </p>
      )}
      <div className="identite__paire">
        <ChampAccent
          libelle="Couleur principale"
          valeur={primaire}
          onChange={setPrimaire}
          decline={affiche.primaire}
          seuilTexte={affiche.seuil_texte}
        />
        <ChampAccent
          libelle="Couleur secondaire"
          valeur={secondaire}
          onChange={setSecondaire}
          decline={affiche.secondaire}
          seuilTexte={affiche.seuil_texte}
        />
      </div>

      <div className="identite__apercus">
        <VignetteApercu theme="sombre" identite={affiche} />
        <VignetteApercu theme="clair" identite={affiche} />
      </div>

      <p>
        <button type="submit" disabled={enregistrer.isPending}>
          {enregistrer.isPending ? 'Enregistrement…' : 'Enregistrer les couleurs'}
        </button>
      </p>
      <MessageErreur erreur={enregistrer.error} />
      <MessageErreur erreur={apercu.error} />
    </form>
  )
}

function ChampAccent({
  libelle,
  valeur,
  onChange,
  decline,
  seuilTexte,
}: {
  libelle: string
  valeur: string
  onChange: (valeur: string) => void
  decline: AccentDecline
  seuilTexte: number
}) {
  return (
    <div className="identite__accent">
      <label className="identite__saisie">
        <span>{libelle}</span>
        {/* Le sélecteur natif et le champ texte disent la **même** valeur : le premier sert au
            geste (souris, doigt), le second à coller une référence lue sur une charte — c'est le
            cas réel décrit par le CDC. */}
        <input
          type="color"
          className="identite__pastille"
          value={valeur}
          onChange={(e) => onChange(e.target.value)}
          aria-label={`${libelle} — sélecteur`}
        />
        <input
          type="text"
          className="identite__hex"
          value={valeur}
          onChange={(e) => onChange(e.target.value)}
          spellCheck={false}
          aria-label={`${libelle} — code hexadécimal`}
        />
      </label>
      <Mesures decline={decline} seuilTexte={seuilTexte} />
    </div>
  )
}

/**
 * Le contrôle de contraste : **chiffré et non bloquant** (`P-4`, `D-16`).
 *
 * ⚠️ Il ne dit jamais « couleur refusée » — rien n'est refusé. Il dit que la couleur brute ne
 * tiendrait pas en texte sur tel thème, **et** que le produit y pourvoit en dérivant une variante.
 * Sans cette seconde moitié, l'organisateur lirait une alerte sans savoir qu'elle est déjà traitée,
 * et changerait sa marque pour rien.
 */
function Mesures({ decline, seuilTexte }: { decline: AccentDecline; seuilTexte: number }) {
  return (
    <div className="identite__mesures">
      <Mesure libelle="sur fond sombre" ratio={decline.contraste_sur_sombre} seuil={seuilTexte} />
      <Mesure libelle="sur fond clair" ratio={decline.contraste_sur_clair} seuil={seuilTexte} />
    </div>
  )
}

function Mesure({ libelle, ratio, seuil }: { libelle: string; ratio: number; seuil: number }) {
  const faible = ratio < seuil
  return (
    <span className={`identite__mesure${faible ? ' identite__mesure--faible' : ''}`}>
      <span className="identite__ratio">{ratio.toFixed(2)}:1</span> {libelle}
      {faible
        ? ` — trop faible pour du texte (${seuil}:1 attendu) : une variante plus claire est utilisée pour les libellés, votre couleur reste l’aplat.`
        : ' — lisible partout.'}
    </span>
  )
}

/**
 * Une vignette « surface réelle » — l'écran de salle en thème sombre, le téléphone en thème clair.
 *
 * `style` en ligne plutôt qu'une classe : ces couleurs sont des **données** (elles viennent de la
 * réponse serveur), pas une variante d'apparence, et il n'existe aucune feuille de style capable de
 * les connaître d'avance.
 */
function VignetteApercu({ theme, identite }: { theme: 'sombre' | 'clair'; identite: IdentiteDTO }) {
  const primaire: JetonsDeMarque =
    theme === 'sombre' ? identite.primaire.sombre : identite.primaire.clair
  const secondaire: JetonsDeMarque =
    theme === 'sombre' ? identite.secondaire.sombre : identite.secondaire.clair

  return (
    <div className={`identite__apercu identite__apercu--${theme}`}>
      <p className="identite__apercu-titre">
        {theme === 'sombre' ? 'Écran de salle (thème sombre)' : 'Téléphone du public (thème clair)'}
      </p>
      <div className="identite__scene">
        <div
          className="identite__bandeau-apercu"
          style={{ color: primaire.texte, borderBlockEndColor: primaire.contour }}
        >
          Challenge des Champions
        </div>
        <div>
          <span
            className="identite__pastille-apercu"
            style={{ background: primaire.surface, color: primaire.encre }}
          >
            Podium
          </span>{' '}
          <span
            className="identite__pastille-apercu"
            style={{ background: secondaire.surface, color: secondaire.encre }}
          >
            Départ 2
          </span>
        </div>
      </div>
    </div>
  )
}

// —————————————————————————————————————————————————————————————————————————————————————————————
// Les deux logos

function LesDeuxLogos({ tournoiId, identite }: { tournoiId: number; identite: IdentiteDTO }) {
  return (
    <>
      <h4 className="carte__soustitre">Logos</h4>
      <p className="carte__aide">
        Deux logos, tous deux facultatifs : celui de l’<strong>édition</strong> et celui du{' '}
        <strong>club organisateur</strong>. Formats acceptés : SVG ou PNG, 512 Ko au maximum. Le
        fichier est utilisé tel quel — il n’est ni recadré ni détouré.
      </p>
      <div className="identite__logos">
        <DepotDeLogo
          tournoiId={tournoiId}
          emplacement="evenement"
          libelle="Logo du tournoi"
          identite={identite}
        />
        <DepotDeLogo
          tournoiId={tournoiId}
          emplacement="club"
          libelle="Logo du club organisateur"
          identite={identite}
        />
      </div>
    </>
  )
}

function DepotDeLogo({
  tournoiId,
  emplacement,
  libelle,
  identite,
}: {
  tournoiId: number
  emplacement: EmplacementLogo
  libelle: string
  identite: IdentiteDTO
}) {
  const deposer = useDeposerLogo(tournoiId)
  const retirer = useRetirerLogo(tournoiId)
  const present = identite.logos.includes(emplacement)
  const identiteQuery = useIdentite(tournoiId)

  return (
    <div className="identite__logo">
      <strong>{libelle}</strong>
      <div className="identite__logo-vignette">
        {present ? (
          <img
            className="logo-tournoi"
            src={urlDuLogo(tournoiId, emplacement, identiteQuery.dataUpdatedAt)}
            alt={`${libelle} déposé`}
          />
        ) : (
          <span className="identite__logo-absent">Aucun logo</span>
        )}
      </div>
      <label>
        <span className="carte__aide">
          {present ? 'Remplacer le fichier' : 'Choisir un fichier'}
        </span>
        <input
          type="file"
          accept="image/png,image/svg+xml"
          aria-label={`${libelle} — choisir un fichier`}
          onChange={(evenement) => {
            const fichier = evenement.target.files?.[0]
            // Le champ est remis à zéro pour que **redéposer le même fichier** déclenche bien un
            // changement : sans cela, corriger le fichier sur le disque puis le rechoisir ne
            // produirait aucun événement, et l'organisateur croirait le dépôt fait.
            evenement.target.value = ''
            if (fichier !== undefined) deposer.mutate({ emplacement, fichier })
          }}
        />
      </label>
      {present && (
        <p>
          <button type="button" onClick={() => retirer.mutate(emplacement)}>
            Retirer ce logo
          </button>
        </p>
      )}
      <MessageErreur erreur={deposer.error} />
      <MessageErreur erreur={retirer.error} />
    </div>
  )
}
