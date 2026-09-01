// Réglage des podiums du **tournoi** (E16US014, A16) : ce que le club récompense, et sur combien
// de places.
//
// ⚠️ **Rendu par l'admin seulement**, jamais par `VuePalmares` — ce composant-là sert aussi l'appli
// publique et l'écran de salle (`interactif` ne distingue que le projeté).
//
// Aucun état local : ce qui est coché est **ce que le serveur a accepté**. Un état local recalé par
// `useEffect` afficherait un réglage non encore retenu (défaut relevé en revue d'E06US006).

import type { PorteePodium } from './api'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useReglagePodiums, useReglerPodiums } from './hooks'

/** Le défaut d'E06US004, répété ici pour l'affichage d'avant la première réponse du serveur — la
 *  valeur qui fait foi est celle de la base (migration 0052), jamais celle-ci. */
const PROFONDEUR_PAR_DEFAUT = 4

/** Miroir de `PROFONDEUR_PODIUM_MAX` (`domain/podium.py`) : le serveur reste seul juge, le
 *  champ ne fait qu'éviter d'envoyer une valeur qu'on sait refusée. */
const PROFONDEUR_MAX = 64

const PORTEES: { valeur: PorteePodium; libelle: string; aide: string }[] = [
  {
    valeur: 'scratch',
    // ⚠️ Pas « Scratch » : le glossaire réserve ce mot à un libellé de **catégorie** (arc nu). Le
    // code de la portée reste `scratch`, l'écran dit ce qu'il montre.
    libelle: 'Toutes catégories',
    aide: 'Le podium du tournoi, toutes catégories mêlées.',
  },
  { valeur: 'categorie', libelle: 'Par catégorie', aide: 'Un podium par catégorie présente.' },
  { valeur: 'club', libelle: 'Par club', aide: 'Les archers de chaque club, classés entre eux.' },
]

export function ReglagePodiums({ tournoiId }: { tournoiId: number }) {
  const reglage = useReglagePodiums(tournoiId)
  const regler = useReglerPodiums(tournoiId)
  // ⚠️ **Ce qui est EN VOL prime sur le cache**, sinon un second geste part d'un réglage périmé et
  // efface le premier : `isPending` retombe dès que le PUT répond, avant que le refetch atterrisse.
  // Le verrou seul ne suffisait pas — il était même faux de le dire (relevé en revue).
  const enVol = regler.isPending ? regler.variables : undefined
  const portees = enVol?.portees ?? reglage.data?.portees ?? []
  const profondeur = enVol?.profondeur ?? reglage.data?.profondeur ?? PROFONDEUR_PAR_DEFAUT
  // Figé sur la seule lecture : verrouiller aussi pendant l'écriture avalait le clic suivant, le
  // `blur` du champ profondeur désactivant le `fieldset` avant que le `click` ne soit dispatché.
  const fige = reglage.isPending || reglage.isError

  const basculer = (portee: PorteePodium) => {
    const retenues = portees.includes(portee)
      ? portees.filter((p) => p !== portee)
      : [...portees, portee]
    regler.mutate({ portees: retenues, profondeur })
  }

  return (
    <section className="palmares-reglage" aria-label="Réglage des podiums">
      <h4 className="palmares-section">Ce que ce tournoi récompense</h4>
      <fieldset className="palmares-reglage__portees" disabled={fige}>
        <legend className="palmares-reglage__legende">Podiums affichés</legend>
        {PORTEES.map((portee) => (
          <label key={portee.valeur} className="palmares-reglage__portee">
            <input
              type="checkbox"
              checked={portees.includes(portee.valeur)}
              onChange={() => basculer(portee.valeur)}
            />
            <span className="palmares-reglage__portee-libelle">{portee.libelle}</span>
            <span className="palmares-reglage__portee-aide">{portee.aide}</span>
          </label>
        ))}
      </fieldset>

      <label className="palmares-reglage__profondeur" htmlFor="profondeur-podium">
        Places récompensées
      </label>
      {/* ⚠️ Champ **non contrôlé**, seule exception au principe ci-dessus, et il n'y en a pas
          d'autre : une case à cocher se valide au clic, un nombre se tape — « 12 » passe par « 1 ».
          Un `value` sans `onChange` rend le champ impossible à saisir en React ; un état local
          recalé par `useEffect` rouvrirait la divergence. Le `key` remonte le champ sur la valeur
          **du serveur** dès qu'elle change : la frappe vit dans le DOM, la vérité reste au-dessus. */}
      <input
        // La clé porte aussi les échecs : sans `failureCount`, un PUT refusé laissait à l'écran le
        // nombre que le serveur venait de rejeter, à côté du message d'erreur qui le contredit.
        key={`${profondeur}-${regler.failureCount}`}
        id="profondeur-podium"
        className="formulaire__champ"
        type="number"
        min={1}
        max={PROFONDEUR_MAX}
        defaultValue={profondeur}
        disabled={fige}
        onBlur={(e) => {
          const saisie = Number(e.target.value)
          if (
            Number.isInteger(saisie) &&
            saisie >= 1 &&
            saisie <= PROFONDEUR_MAX &&
            saisie !== profondeur
          ) {
            regler.mutate({ portees, profondeur: saisie })
            return
          }
          // Saisie vide, hors bornes ou inchangée : on **ramène** l'affichage au réglage retenu
          // plutôt que de laisser à l'écran un nombre que le serveur refuserait.
          e.target.value = String(profondeur)
        }}
      />

      <p className="carte__etat">
        {/* ⚠️ Rien tant que le serveur n'a pas répondu : `portees` vaut `[]` pendant la lecture,
            donc la phrase « aucun podium affiché » clignotait — fausse — à chaque ouverture. */}
        {reglage.isError
          ? 'Réglage indisponible — les podiums affichés restent ceux du serveur.'
          : reglage.data === undefined
            ? 'Lecture du réglage…'
            : portees.length === 0
              ? 'Aucun podium affiché — le palmarès ne montrera que le classement complet.'
              : 'Les podiums réglés ici sont ceux de l’écran, de l’affichage public et du PDF.'}{' '}
        Changer ce réglage <strong>ne modifie aucun résultat</strong> : le palmarès se recalcule à
        chaque lecture, seul ce qu’il affiche change. Le nombre de places récompensées ne commande
        pas le nombre de duels tirés — cela reste le réglage de chaque phase.
      </p>
      <MessageErreur erreur={reglage.error} />
      <MessageErreur erreur={regler.error} />
    </section>
  )
}
