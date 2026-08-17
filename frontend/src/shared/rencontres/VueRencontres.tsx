// La vue **commune** des formats sans arbre qui apparient des rencontres (E05US031, ADR-0089 §1) :
// les poules et le système suisse aujourd'hui, la colline demain (`E05US027`).
//
// Un seul composant pour deux surfaces, comme l'arbre (E07US005) et les affectations (E07US008) :
// l'appli publique (interactive) et l'**écran de salle** (projeté, `interactif=false`, aucune
// interaction — CA E07US004). Les dessiner séparément les ferait diverger sur la seule chose qui
// compte, l'appariement affiché.
//
// ⚠️ **Ce composant ne lit aucun store.** `mode` et `suivis` descendent en props, parce qu'il sert
// aussi l'écran de salle, où il n'y a personne à suivre — et parce qu'abonner la salle à un store
// public est exactement le défaut qu'E16US004 a dû corriger en revue sur `VueTableaux`.

import { type ModeAffichage } from '../suivis/focus'
import {
  cheminDe,
  engagesParmi,
  LIBELLE_STATUT,
  nomComplet,
  nomDeArcher,
  rangDe,
  type BlocRencontres,
  type FormatPublic,
  type LigneClassement,
  type RencontreVue,
  type TourVue,
} from './modele'

export function VueRencontres({
  format,
  interactif = true,
  mode = 'tout',
  suivis = [],
}: {
  format: FormatPublic
  interactif?: boolean
  mode?: ModeAffichage
  suivis?: number[]
}) {
  // Sur l'écran de salle il n'y a personne à suivre : la lecture y est **toujours** complète (CA
  // E07US004). Dans l'appli publique, c'est l'interrupteur d'en-tête qui décide (ADR-0079).
  const centrerSurSuivis = interactif && mode === 'suivis'

  if (format.blocs.length === 0) {
    return <p className="carte__etat">Cette phase n’a pas encore de rencontres.</p>
  }

  return (
    <div className="rencontres">
      {format.conflits.map((conflit) => (
        <p key={conflit} className="rencontres__conflit">
          {conflit}
        </p>
      ))}

      {centrerSurSuivis ? (
        <MesArchers format={format} suivis={suivis} />
      ) : (
        format.blocs.map((bloc) => <Bloc key={bloc.cle} bloc={bloc} />)
      )}
    </div>
  )
}

/** Un bloc autonome : une poule, ou l'unique plateau d'un système suisse. */
function Bloc({ bloc }: { bloc: BlocRencontres }) {
  return (
    <section className="rencontres__bloc">
      {bloc.titre !== null && <h4 className="rencontres__titre">{bloc.titre}</h4>}

      {bloc.notes.map((note) => (
        <p key={note} className="rencontres__note">
          {note}
        </p>
      ))}

      {/* **Tous** les tours, pas seulement celui en cours : c'est le CA « l'historique des tours
          reste lisible » (cadrage du 17/08/2026). Un spectateur qui arrive à la ronde 4 doit
          pouvoir lire les trois premières. */}
      {bloc.tours.map((tour) => (
        <Tour key={tour.libelle} tour={tour} />
      ))}

      {bloc.classement.length > 0 && <Classement bloc={bloc} />}
    </section>
  )
}

function Tour({ tour }: { tour: TourVue }) {
  return (
    <section className="rencontres__tour">
      <h5 className="rencontres__tour-titre">
        {tour.libelle}
        {/* « En cours » plutôt que rien : sur un format sans arbre, c'est la seule marque qui
            distingue le tour qu'on regarde tirer de ceux qui sont derrière. */}
        {!tour.clos && <span className="rencontres__en-cours">en cours</span>}
      </h5>

      {tour.rencontres.length === 0 ? (
        <p className="carte__etat">Aucune rencontre à afficher pour ce tour.</p>
      ) : (
        <ul className="rencontres__liste">
          {tour.rencontres.map((rencontre) => (
            <LigneRencontre key={rencontre.numero} rencontre={rencontre} />
          ))}
        </ul>
      )}

      {/* Le **bye** se nomme. Un archer absent de tous les appariements d'une ronde, sans un mot,
          se lit comme un oubli — alors qu'il marque comme s'il avait gagné. */}
      {tour.exempt !== null && (
        <p className="rencontres__exempt">Exempt : {nomComplet(tour.exempt)}</p>
      )}
    </section>
  )
}

function LigneRencontre({ rencontre }: { rencontre: RencontreVue }) {
  const score =
    rencontre.points_haut === null || rencontre.points_bas === null
      ? null
      : `${rencontre.points_haut} — ${rencontre.points_bas}`
  // ⚠️ **`validee`, pas `termine`** pour marquer le gagnant : tant que le scoreur n'a pas scellé,
  // rien n'est acquis. Le même piège que l'arbre, et il se paie ici sur un classement.
  const gagnant = rencontre.validee ? rencontre.vainqueur : null
  return (
    <li className="rencontres__rencontre">
      <span className={gagnant === 'haut' ? 'rencontres__gagnant' : undefined}>
        {rencontre.haut === null ? '—' : nomComplet(rencontre.haut)}
      </span>
      <span className="rencontres__vs">{score ?? 'vs'}</span>
      <span className={gagnant === 'bas' ? 'rencontres__gagnant' : undefined}>
        {rencontre.bas === null ? '—' : nomComplet(rencontre.bas)}
      </span>
      {/* La **cible** est ce que le CA demande explicitement : « les rencontres du tour en cours,
          avec leur cible ». C'est ce qu'un spectateur cherche d'abord — où regarder. */}
      {rencontre.couloirs !== null && (
        <span className="rencontres__cible">
          Cible {rencontre.couloirs[0][0]}
          {rencontre.couloirs[0][1]}/{rencontre.couloirs[1][1]}
        </span>
      )}
      {rencontre.termine && !rencontre.validee && (
        <span className="rencontres__attente">En attente de validation</span>
      )}
    </li>
  )
}

function Classement({ bloc }: { bloc: BlocRencontres }) {
  return (
    <div className="rencontres__classement">
      <h5 className="rencontres__tour-titre">Classement</h5>
      {/* Le tableau défile **dans son propre conteneur** : cinq critères de départage ne tiennent
          pas sur 360 px, et faire défiler la page entière casse la lecture des tours au-dessus. */}
      <div className="rencontres__table-defilante">
        <table className="rencontres__table">
          <thead>
            <tr>
              <th scope="col">Rang</th>
              <th scope="col">Archer</th>
              {bloc.colonnes.map((colonne) => (
                <th key={colonne.cle} scope="col" title={colonne.aide}>
                  {colonne.libelle}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bloc.classement.map((ligne) => (
              <LigneDeClassement key={ligne.archer_id} ligne={ligne} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function LigneDeClassement({ ligne }: { ligne: LigneClassement }) {
  return (
    <tr>
      <td>
        {ligne.rang}
        {/* L'ex æquo se **dit**, il ne se déduit pas de deux rangs identiques : la convention
            « 1224 » laisse un rang vacant, et un lecteur qui voit passer 2, 2, 4 sans explication
            conclut à un bug. Un mot, jamais une couleur seule (`DV-03`). */}
        {ligne.ex_aequo && <span className="rencontres__ex-aequo"> ex æquo</span>}
      </td>
      <td>{ligne.nom}</td>
      {/* Clé = l'index : `valeurs` est alignée sur `colonnes`, dont l'ordre est figé par
          l'adaptateur du format — c'est donc la seule identité stable, et deux critères peuvent
          porter la même valeur. */}
      {ligne.valeurs.map((valeur, index) => (
        <td key={index}>{valeur}</td>
      ))}
    </tr>
  )
}

/** La lecture centrée sur les archers suivis (ADR-0079). */
function MesArchers({ format, suivis }: { format: FormatPublic; suivis: number[] }) {
  if (suivis.length === 0) {
    // Défense en profondeur : l'interrupteur d'en-tête ne rend « suivis » qu'avec au moins un archer
    // suivi (`modeEffectif`). On ne bascule pas d'autorité sur l'autre lecture — ce serait répondre
    // à côté sans le dire — et l'on nomme le geste manquant.
    return (
      <p className="carte__etat">
        Aucun archer suivi. Ajoutez-en dans l’onglet « Suivi » pour voir son parcours ici, ou
        repassez l’affichage sur « Tout le tournoi ».
      </p>
    )
  }
  const engages = engagesParmi(format, suivis)
  if (engages.length === 0) {
    // ⚠️ **« Aucun de vos archers ici » ≠ « rien à afficher »** (ADR-0089 §6). Le cas est banal — on
    // suit des archers d'une catégorie, on regarde la poule d'une autre — et c'est précisément
    // celui qu'E16US004 avait manqué sur l'arbre.
    return (
      <p className="carte__etat">
        Aucun des archers que vous suivez n’est engagé dans cette phase. Passez à « Tout le tournoi
        » pour voir toutes les rencontres.
      </p>
    )
  }
  return (
    <>
      <ul className="rencontres__chemins">
        {engages.map((archerId) => (
          <CheminArcher key={archerId} format={format} archerId={archerId} />
        ))}
      </ul>
      {engages.length < suivis.length && (
        <p className="carte__etat">
          {suivis.length - engages.length === 1
            ? 'Un autre archer suivi n’est pas engagé dans cette phase.'
            : `${suivis.length - engages.length} autres archers suivis ne sont pas engagés dans cette phase.`}
        </p>
      )}
    </>
  )
}

function CheminArcher({ format, archerId }: { format: FormatPublic; archerId: number }) {
  const etapes = cheminDe(format, archerId)
  const classe = rangDe(format, archerId)
  const nom = nomDeArcher(format, archerId)

  return (
    <li className="rencontres__chemin">
      <span className="rencontres__chemin-nom">{nom ?? 'Archer suivi'}</span>

      {/* Dans un format sans arbre, **le rang est la position** : c'est lui qui remplace la branche.
          Le taire livrerait une liste de résultats sans jamais dire où en est l'archer. */}
      {classe !== null && (
        <p className="rencontres__chemin-rang">
          {classe.bloc.titre === null ? '' : `${classe.bloc.titre} · `}
          {classe.ligne.rang}
          <sup>{classe.ligne.rang === 1 ? 'er' : 'e'}</sup>
          {classe.ligne.ex_aequo ? ' ex æquo' : ''}
          {classe.bloc.colonnes.map((colonne, index) => (
            <span key={colonne.cle} className="rencontres__chemin-critere">
              {' · '}
              {colonne.libelle} {classe.ligne.valeurs[index] ?? '—'}
            </span>
          ))}
        </p>
      )}

      {etapes.length === 0 ? (
        <p className="carte__etat">Pas encore de rencontre dans cette phase.</p>
      ) : (
        // Clé = l'index : deux étapes peuvent partager le même libellé de tour (un archer dispute
        // plusieurs rencontres d'un même tour de poule), donc l'ordre du chemin est la seule
        // identité stable.
        <ol className="rencontres__etapes">
          {etapes.map((etape, index) => (
            <li
              key={index}
              className={`rencontres__etape rencontres__etape--${etape.statut.replace('_', '-')}`}
            >
              <span className="rencontres__tour-nom">
                {etape.bloc === null ? etape.libelle : `${etape.bloc} · ${etape.libelle}`}
              </span>
              <span className="rencontres__contre">
                {etape.adversaire === null ? '—' : nomComplet(etape.adversaire)}
                {etape.score !== null && (
                  <strong className="rencontres__score"> {etape.score}</strong>
                )}
              </span>
              <span className="rencontres__statut">{LIBELLE_STATUT[etape.statut]}</span>
            </li>
          ))}
        </ol>
      )}
    </li>
  )
}
