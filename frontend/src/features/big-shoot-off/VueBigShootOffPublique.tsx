// Vue publique du **Big Shoot Off** (E05US031, ADR-0089 §1) — appli publique et écran de salle.
//
// ⚠️ **Vue propre, et non la forme commune des formats appariés.** Une manche de Big Shoot Off est
// un **tir collectif sans adversaire** : pas de rencontre, pas d'appariement, pas de vainqueur de
// rencontre. La plier dans `shared/rencontres/` demanderait d'y inventer des champs vides porteurs
// de sens implicite — le défaut nommé par ADR-0089 §1, et déjà par ADR-0064 §2 (*« quand une valeur
// doit signifier deux choses selon le contexte, elle finit par mentir dans l'un des deux »*).
//
// Ce que le format donne à lire tient en trois choses, et l'écran ne dit rien d'autre : **l'échelle**
// annoncée (12 → 8 → 6 → 5), **qui est encore en lice**, et **ce que chacun a marqué manche par
// manche**. Le reste — quelle volée saisir, combien de flèches — est de la saisie.

import { type ModeAffichage } from '../../shared/suivis/focus'
import { estSorti, libelleSort, lignesTireurs, nbEnLice, type LigneTireur } from './publique'
import type { EtatBigShootOffPublic } from './api'

export function VueBigShootOffPublique({
  etat,
  interactif = true,
  mode = 'tout',
  suivis = [],
}: {
  etat: EtatBigShootOffPublic
  interactif?: boolean
  mode?: ModeAffichage
  suivis?: number[]
}) {
  // Sur l'écran de salle il n'y a personne à suivre (CA E07US004) ; dans l'appli publique, c'est
  // l'interrupteur d'en-tête qui décide (ADR-0079). Jamais le store, ce composant sert les deux.
  const centrerSurSuivis = interactif && mode === 'suivis'
  const toutes = lignesTireurs(etat)
  const lignes = centrerSurSuivis ? toutes.filter((l) => suivis.includes(l.archer_id)) : toutes
  const nbManches = etat.manches.length

  return (
    <div className="bso-public">
      <Echelle etat={etat} />

      {/* Le **barrage suspend la phase**, et c'est lui qui explique pourquoi rien n'avance. Le taire
          laisserait le public devant une finale figée sans raison visible. */}
      {etat.barrage !== null && (
        <p className="bso-public__barrage">
          Égalité à départager : {etat.barrage.noms.join(', ')} —{' '}
          {etat.barrage.places === 1 ? 'une place' : `${etat.barrage.places} places`} en jeu. La
          manche suivante attend ce barrage.
        </p>
      )}

      {centrerSurSuivis && suivis.length === 0 ? (
        <p className="carte__etat">
          Aucun archer suivi. Ajoutez-en dans l’onglet « Suivi » pour voir son parcours ici, ou
          repassez l’affichage sur « Tout le tournoi ».
        </p>
      ) : lignes.length === 0 ? (
        // ⚠️ « Aucun de vos archers ici » ≠ « personne en finale » (ADR-0089 §6) : une finale à six
        // ne contient presque jamais les archers qu'on suit, et confondre les deux vides ferait
        // croire à un écran cassé.
        <p className="carte__etat">
          {centrerSurSuivis
            ? 'Aucun des archers que vous suivez n’est en finale. Passez à « Tout le tournoi » pour voir les finalistes.'
            : 'Aucun finaliste n’est encore désigné pour cette phase.'}
        </p>
      ) : (
        <Finalistes lignes={lignes} nbManches={nbManches} etat={etat} />
      )}
    </div>
  )
}

/** L'échelle annoncée du format : « 12 → 8 → 6 → 5 ». C'est ce qui rend le format lisible d'emblée
 * — sans elle, un spectateur voit des archers disparaître sans savoir combien sortent à chaque fois. */
function Echelle({ etat }: { etat: EtatBigShootOffPublic }) {
  const { effectif, paliers } = etat.projection
  const enLice = nbEnLice(etat)
  // ⚠️ `termine` est rendu **vrai sur une phase encore vide** (`_photo` d'une population nulle est
  // une photo terminée, pas une erreur) : c'est l'état nominal du matin. Sans la population, le
  // badge « terminé » s'affichait au-dessus de « Aucun finaliste n'est encore désigné » — deux
  // affirmations contradictoires, dont une fausse, sur l'écran projeté.
  const acheve = etat.termine && etat.tireurs.length > 0
  return (
    <p className="bso-public__echelle">
      <span className="bso-public__palier">{effectif}</span>
      {/* Clé = l'index, et c'est **correct ici** : deux paliers peuvent valoir le même nombre (une
          manche qui n'élimine personne), donc le rang dans la suite est la seule identité stable. */}
      {paliers.map((palier, index) => (
        <span key={index} className="bso-public__palier">
          {palier}
        </span>
      ))}
      {acheve && <span className="bso-public__termine">terminé</span>}
      {!acheve && enLice > 0 && (
        <span className="bso-public__restants">
          {enLice === 1 ? '1 archer en lice' : `${enLice} archers en lice`}
        </span>
      )}
    </p>
  )
}

function Finalistes({
  lignes,
  nbManches,
  etat,
}: {
  lignes: LigneTireur[]
  nbManches: number
  etat: EtatBigShootOffPublic
}) {
  return (
    // Le tableau défile dans son **propre** conteneur : au-delà de quatre manches, il déborde de
    // 360 px, et faire défiler la page entière casserait la lecture de l'échelle au-dessus.
    <div className="bso-public__table-defilante">
      <table className="bso-public__table">
        <thead>
          <tr>
            <th scope="col">Archer</th>
            {Array.from({ length: nbManches }, (_, index) => (
              <th key={index} scope="col">
                M{index + 1}
              </th>
            ))}
            <th scope="col">Sort</th>
          </tr>
        </thead>
        <tbody>
          {lignes.map((ligne) => (
            <tr key={ligne.archer_id} className={estSorti(ligne) ? 'bso-public__sorti' : undefined}>
              <td>{ligne.nom}</td>
              {Array.from({ length: nbManches }, (_, index) => (
                // `scores` ne porte que les manches **entièrement validées** : un total partiel
                // ferait lire « 12 » pour une manche dont deux volées manquent, et le spectateur
                // croirait l'archer en difficulté. Une manche non validée affiche un tiret.
                <td key={index}>{ligne.scores[index] ?? '—'}</td>
              ))}
              {/* Un mot, jamais une couleur seule (`DV-03`). Le libellé vit dans `publique.ts` :
                  « en lice » et « vainqueur » se distinguent par `termine`, que le JSX n'a pas à
                  arbitrer (et ne le faisait pas — le champion restait « En lice »). */}
              <td>{libelleSort(ligne, etat)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
