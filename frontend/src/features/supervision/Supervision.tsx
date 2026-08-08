// Console de supervision des postes (E12US001, ADR-0038 ; écrans de salle : E07US004, ADR-0064) —
// l'écran du jour J.
//
// « Ce n'est pas un graphique de progression : c'est une console de supervision. » Elle distingue
// *ils tirent lentement* (en ligne, mais dernière activité ancienne) de *leur tablette est morte*
// (hors ligne). Live par poll court (cf. `useSupervision`). L'état se rend en **couleur + pastille +
// texte** (jamais la couleur seule) ; hors ligne = **ambre**, pas rouge (arbitrage ADR-0038 / DV-03).
//
// Les cibles se lisent en **grille de tuiles** depuis E17US004 (planche A13, variante B retenue) ; le
// tableau qui tenait ce rôle était la variante écartée.
//
// **Les écrans de salle y figurent aussi** (E07US004), dans un second bandeau — pas dans un autre
// écran. Le CA le dit sans détour : *« un écran figé ne se plaint pas, seule la supervision le
// révèle »*. C'est aussi d'ici que l'organisateur **impose une vue** sans traverser le gymnase, et
// qu'il voit, en rouge, les prises de contrôle qu'il a oublié de rendre.

import { ErreurApi } from '../../shared/api/client'
import { BoutonConfirme } from '../../shared/ui/BoutonConfirme'
import { GroupeRepliable } from '../../shared/ui/GroupeRepliable'
import type { PosteSupervision } from './api'
import { PiloterEcrans } from './PiloterEcrans'
import { afficheEtat, avancementLibelle, fractionAvancement, voleeCourte } from './etat'
import { useRevoquerPoste, useSupervision } from './hooks'
import { tempsRelatif } from './tempsRelatif'

export function Supervision({ tournoiId }: { tournoiId: number }) {
  const supervision = useSupervision(tournoiId)
  // Les deux natures de poste, séparées **une fois** : elles alimentent chacune leur bandeau, et
  // chaque bandeau a besoin de son décompte d'anomalies avant même d'être déplié (A12).
  const postes = supervision.data?.postes ?? []
  const cibles = postes.filter((poste) => poste.type === 'cible')
  const ecrans = postes.filter((poste) => poste.type === 'ecran')
  // ⚠️ **Anomalie = `hors_ligne`, jamais `non_rattache`.** Un poste non rattaché est l'état
  // **nominal** de la préparation : compter les 30 cibles avant distribution des tablettes faisait
  // hurler « 30 à vérifier » toute la matinée, et un signal qui hurle dans l'état normal cesse
  // d'être lu le jour où il dit vrai — l'inverse d'A13, « seuls les problèmes sautent aux yeux ».
  // Hors ligne, en revanche, c'est un poste **rattaché qui s'est tu** : là, il y a quelqu'un à
  // envoyer. (Revue du 05/08/2026, axe C1.)
  const muets = (liste: typeof postes) => liste.filter((p) => p.etat === 'hors_ligne').length

  return (
    <section className="carte carte--large">
      <h2 className="carte__titre">Supervision des postes</h2>

      {supervision.isPending && <p className="carte__etat">Chargement…</p>}
      {/* DETTE-050 : rendu ad hoc non rallié à `shared/ui/texteErreur` — `error.message` brut.
          (Le rendu de `revoquer`, plus bas, est déjà gardé par `instanceof ErreurApi`.) */}
      {supervision.isError && (
        <p className="carte__etat carte__etat--erreur" role="alert">
          Supervision injoignable — {supervision.error.message}
        </p>
      )}

      {supervision.data && (
        <>
          <p className="supervision__compteur" role="status">
            <strong>
              {supervision.data.nb_en_ligne}/{supervision.data.nb_total}
            </strong>{' '}
            en ligne
          </p>

          {supervision.data.nb_total === 0 ? (
            <p className="carte__etat">
              Aucun poste préparé pour ce tournoi (préparez les codes de cible dans «&nbsp;Postes de
              cible&nbsp;»).
            </p>
          ) : (
            <GroupeRepliable
              titre="Écrans de cible"
              resume={`${supervision.data.nb_en_ligne}/${supervision.data.nb_total} en ligne`}
              nbAnomalies={muets(cibles)}
              libelleAnomalies="à vérifier"
              enfants={
                <>
                  <p className="supervision__legende">
                    Chaque tuile&nbsp;: cible, volée en cours, dernier signe de vie.
                  </p>
                  <ul className="supervision__grille">
                    {cibles.map((poste) => (
                      <TuilePoste key={poste.poste_id} poste={poste} tournoiId={tournoiId} />
                    ))}
                  </ul>
                </>
              }
            />
          )}

          {/* Second bandeau : les écrans de salle. Deux natures de poste, deux groupes — c'est
              exactement le découpage qu'A12 demande (« chaque type d'écran est sous un bandeau
              repliable de type »), et il existait déjà en substance ici, sans repli ni remontée
              d'alerte. */}
          <GroupeRepliable
            titre="Écrans de salle"
            resume={`${supervision.data.nb_ecrans_en_ligne}/${supervision.data.nb_ecrans} en ligne`}
            nbAnomalies={muets(ecrans)}
            libelleAnomalies="à vérifier"
            enfants={
              <PiloterEcrans
                tournoiId={tournoiId}
                ecrans={ecrans}
                nbEnLigne={supervision.data.nb_ecrans_en_ligne}
              />
            }
          />
        </>
      )}
    </section>
  )
}

/**
 * Une cible, en tuile — planche A13, variante **B « grille de tuiles (30 d'un œil) »**, retenue au
 * questionnaire du 04/08/2026 et **validée sans réserve** (E17US004).
 *
 * Le tableau qui tenait ce rôle était la variante **A**, écartée. Le motif du choix est dans le nom
 * de la variante : trente lignes ne se balaient pas d'un regard, trente tuiles si — et cet écran
 * n'existe que pour répondre à « qui s'est tu ? » en traversant le gymnase le moins possible.
 *
 * **Deux informations que la planche ne montre pas sont conservées** : l'IP (diagnostic `D-06` —
 * c'est elle qui permet de retrouver *physiquement* une tablette) et la révocation. Les perdre aurait
 * été troquer une régression fonctionnelle contre une ressemblance ; la planche est une maquette à
 * données fictives, elle n'a pas vocation à énumérer les actions.
 */
function TuilePoste({ poste, tournoiId }: { poste: PosteSupervision; tournoiId: number }) {
  const revoquer = useRevoquerPoste(tournoiId)
  const { classe, libelle } = afficheEtat(poste.etat)
  const rattache = poste.etat !== 'non_rattache'
  const volee = voleeCourte(poste.avancement)
  const fraction = fractionAvancement(poste.avancement)
  const vu = poste.derniere_saisie === null ? null : tempsRelatif(poste.derniere_saisie, new Date())

  // La pastille porte **toujours** le temps écoulé quand il existe — y compris sur un poste muet.
  //
  // La première version l'y remplaçait par l'état, sur une lecture fausse de la planche : sa tuile
  // hors ligne (A13, tuile 7) porte **« 14 min » ET** un bandeau « hors ligne ». Elle superpose, elle
  // ne substitue pas. Et c'est bien le temps qui compte ici : « muet depuis 90 s » (coupure wifi, on
  // attend) et « muet depuis 25 min » (tablette morte, on traverse le gymnase) appellent deux gestes
  // opposés — c'est la seule décision que cet écran sert à prendre. L'ancien tableau les portait dans
  // deux colonnes distinctes ; les fondre en une seule marque était une régression. (Revue E17US004.)
  //
  // Quand le poste est **muet**, le mot est porté par le bandeau : la pastille n'a donc pas à le
  // redire — elle affiche « — » si le serveur ne connaît aucun temps (cas réel : une cible rattachée
  // qui se tait **avant d'avoir saisi quoi que ce soit**, `derniere_saisie` étant l'horodatage de la
  // dernière volée et non un battement de cœur). Sans cette nuance, « Hors ligne » apparaissait deux
  // fois dans une tuile de 150 px.
  const signe = vu ?? (poste.etat === 'hors_ligne' ? '—' : libelle)

  return (
    <li className={`supervision__tuile supervision__tuile--${classe}`}>
      <p className="supervision__tuile-tete">
        <span className="supervision__cible">
          <span className="sr-only">Cible </span>
          {poste.cible_index ?? '—'}
        </span>
        {volee !== null && <span className="supervision__volee">{volee}</span>}
        <span className={`supervision__etat supervision__etat--${classe} supervision__signe`}>
          <span className="indicateur__pastille" aria-hidden="true" />
          {/* Le préfixe **suit la nature de la valeur**, il ne la précède pas d'office : `signe` vaut
              le temps écoulé quand il y en a un, l'état sinon. Annoncer « dernier signe de vie : Non
              rattaché » serait faux — et le cas est atteignable, `derniere_saisie` étant l'horodatage
              de la dernière volée, nul tant que la cible n'a rien saisi. */}
          <span className="sr-only">
            {vu === null ? 'signe de vie : ' : 'dernier signe de vie : '}
          </span>
          {signe}
        </span>
      </p>

      {/* Un poste **muet** porte le bandeau d'alerte de la planche **à la place** de sa jauge : un
          avancement figé n'apprend rien, et c'est le mot qui doit rester lisible sans la couleur
          (`DV-03`). **Seulement `hors_ligne`** : « non rattaché » est l'état *nominal* de la matinée,
          le crier trente fois apprendrait à ne plus lire l'alerte le jour où elle dit vrai. */}
      {poste.etat === 'hors_ligne' ? (
        <p className="supervision__alerte">{libelle}</p>
      ) : (
        /* La jauge est une image d'information : sans équivalent textuel, un lecteur d'écran ne lit
           qu'une boîte vide. L'`aria-label` reprend le libellé **du tableau**, mot pour mot. */
        fraction !== null && (
          <p className="jauge" role="img" aria-label={avancementLibelle(poste.avancement)}>
            <span style={{ width: `${Math.round(fraction * 100)}%` }} />
          </p>
        )
      )}

      {/* `<div>` et non `<p>` : `BoutonConfirme` rend un `<dialog>`, que le contenu phrasé d'un
          paragraphe n'admet pas. Rendu inchangé, HTML valide. */}
      <div className="supervision__pied">
        {/* L'IP est rendue même sans rattachement — comme le faisait la colonne du tableau : « — »
            dit que la tablette n'a pas encore parlé, ce que l'absence de ligne ne dit pas. */}
        <span className="supervision__ip">{poste.ip ?? '—'}</span>
        {/* Garde-fou tactile : révoquer un poste en cours de tir le coupe. Vrai dialogue depuis
            le retour maquettes du 04/08/2026 (A15) ; le calcul d'impact chiffré reste E12US007. */}
        {rattache && (
          <BoutonConfirme
            libelle="Révoquer"
            className="lien supervision__revoquer"
            disabled={revoquer.isPending}
            enCours={revoquer.isPending}
            titre={`Révoquer la cible ${poste.cible_index ?? '?'} ?`}
            message="L’appareil repasse à l’écran de rattachement. S’il est en cours de saisie, il est coupé."
            libelleConfirmer="Révoquer"
            ton="danger"
            onConfirmer={() => revoquer.mutate(poste.poste_id)}
          />
        )}
      </div>

      {revoquer.isError && (
        <p className="carte__etat--erreur" role="alert">
          {revoquer.error instanceof ErreurApi ? revoquer.error.message : 'Échec de la révocation.'}
        </p>
      )}
    </li>
  )
}
