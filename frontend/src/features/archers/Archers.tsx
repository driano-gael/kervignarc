// Écran d'administration des archers (E02US003) — réservé à l'admin.
//
// Liste des inscrits, édition des quatre champs, désinscription à confirmation. C'est la surface où
// le **club inconnu** devient corrigeable. **Trois signalements, même protocole (ADR-0015), une
// conséquence à part** : `homonyme_archer`, `changement_categorie_archer_engage` et `archer_engage`
// — le troisième est le seul dont la confirmation **détruit** (flèches et placement), d'où un
// bouton `--danger`. ⚠️ Un archer qui **abandonne** ne se supprime pas : c'est un forfait tracé
// (ADR-0050), qui conserve ses résultats.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useBlasons } from '../blasons/hooks'
import { useCategories } from '../categories/hooks'
import { useClubs } from '../clubs/hooks'
import { InscriptionsArcher } from '../inscriptions/InscriptionsArcher'
import type { Archer, ModifierArcher } from './api'
import { useArchers, useDefinirHandicap, useModifierArcher, useSupprimerArcher } from './hooks'

export function Archers({ tournoiId }: { tournoiId: number }) {
  const archers = useArchers(tournoiId)

  return (
    <section>
      <h3 className="carte__soustitre">Archers inscrits</h3>
      {archers.isError && <MessageErreur erreur={archers.error} />}
      {/* `isSuccess` et non `data ?? []` : tant que la requête court, `data` est `undefined` et
          le message s'afficherait à tort sur un tournoi qui a bel et bien des inscrits. */}
      {archers.isSuccess && archers.data.length === 0 && (
        <p className="carte__etat">Aucun archer inscrit pour l'instant.</p>
      )}
      {archers.data && archers.data.length > 0 && (
        <ul className="liste-archers">
          {archers.data.map((archer) => (
            <LigneArcher key={archer.id} archer={archer} tournoiId={tournoiId} />
          ))}
        </ul>
      )}
    </section>
  )
}

function LigneArcher({ archer, tournoiId }: { archer: Archer; tournoiId: number }) {
  const [edition, setEdition] = useState(false)
  const [confirmationSuppression, setConfirmationSuppression] = useState(false)
  const [inscriptionsOuvertes, setInscriptionsOuvertes] = useState(false)
  const supprimer = useSupprimerArcher(tournoiId)
  const clubs = useClubs()
  const categories = useCategories(tournoiId)
  const blasons = useBlasons(tournoiId)

  const engagementSignale =
    supprimer.error instanceof ErreurApi && supprimer.error.code === 'archer_engage'

  // Passer en édition **efface** le signalement de suppression en cours. Sans cela, il n'est que
  // masqué par le formulaire : à la sortie d'édition, le bloc rouge et son « Supprimer
  // définitivement » réapparaîtraient, armés, sur une ligne que l'admin vient de corriger — et
  // portant sur des faits qui ont pu changer entre-temps. C'est le seul endroit de l'écran où un
  // geste destructeur se proposerait sans qu'on l'ait demandé.
  const ouvrirEdition = () => {
    supprimer.reset()
    setConfirmationSuppression(false)
    setEdition(true)
  }

  if (edition) {
    return (
      <li>
        <FormulaireArcher
          archer={archer}
          tournoiId={tournoiId}
          onTermine={() => setEdition(false)}
        />
      </li>
    )
  }

  // Nom **et** prénom : deux homonymes confirmés (un père et son fils) peuvent coexister depuis
  // E02US002 — les distinguer à l'œil est le minimum vital sur un écran de correction.
  const identite = `${archer.nom} ${archer.prenom}`
  const categorie = categories.data?.find((c) => c.id === archer.categorie_id)
  const club = clubs.data?.find((c) => c.id === archer.club_id)
  // Blason **hérité de la catégorie** (E01US022) : lecture seule, jamais un champ par archer (la
  // surcharge par archer reste hors périmètre). `blason_id` peut être null (catégorie sans défaut,
  // ex. tournoi non pré-chargé FFTA) → on n'affiche alors rien.
  const blason =
    categorie?.blason_id != null
      ? blasons.data?.find((b) => b.id === categorie.blason_id)
      : undefined

  return (
    <li>
      <div className="archer__ligne">
        <span className="archer__identite">
          {identite}
          {/* Même signal qu'au classement (`table__anomalie`) : un seul vocabulaire visuel pour
              une seule anomalie. Ici, il est enfin actionnable — « Modifier » ouvre le select. */}
          {archer.club_id === null && (
            <span
              className="table__anomalie"
              title="Renseignez son club pour compléter l'inscription"
            >
              {' '}
              Club inconnu
            </span>
          )}
        </span>
        <span className="archer__details">
          {categorie?.libelle ?? '—'}
          {blason !== undefined && ` · ${blason.nom}`}
          {club !== undefined && ` · ${club.nom}`}
          {archer.cible !== null && ` · cible ${archer.cible}`}
          {/* Handicap (E05US015) : on affiche le **dérivé** calculé par le serveur, et l'on signale
              d'un astérisque qu'une surcharge prime le handicap officiel du club — sans quoi
              l'organisateur ne saurait pas pourquoi la valeur diffère de la fiche club. `0` n'est
              pas affiché : un archer non évalué concourt au scratch, ce n'est pas une information. */}
          {archer.handicap !== 0 && ` · handicap ${archer.handicap}`}
          {archer.handicap_surcharge !== null && (
            <span
              title={`Surcharge de ce tournoi ; handicap du club : ${archer.handicap_officiel ?? '—'}`}
            >
              {' '}
              *
            </span>
          )}
        </span>
        <span className="archer__actions">
          <button
            type="button"
            className="bouton--discret"
            aria-expanded={inscriptionsOuvertes}
            onClick={() => setInscriptionsOuvertes((ouvert) => !ouvert)}
          >
            Départs
          </button>
          <button type="button" className="bouton--discret" onClick={ouvrirEdition}>
            Modifier
          </button>
          {confirmationSuppression ? (
            <>
              <button
                type="button"
                className="bouton--danger"
                disabled={supprimer.isPending}
                onClick={() => supprimer.mutate({ id: archer.id })}
              >
                Confirmer la suppression
              </button>
              <button
                type="button"
                className="bouton--discret"
                onClick={() => {
                  // `reset()` : sans lui, le signalement resterait affiché sur une ligne où
                  // l'admin vient justement de renoncer.
                  supprimer.reset()
                  setConfirmationSuppression(false)
                }}
              >
                Annuler
              </button>
            </>
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
      </div>
      {/* `archer_engage` : un signalement, comme les deux autres — mais le seul dont la
          confirmation **détruit** (les flèches et le placement partent avec l'archer). D'où un
          bouton `--danger` et non neutre : les trois blocs se ressemblent, leurs conséquences
          non. Le message du serveur énumère ce qui sera effacé et rappelle qu'un abandon est un
          forfait (E04US015 / ADR-0050, ex-E12US004), pas une suppression — le lire est le
          geste utile ici. */}
      {engagementSignale ? (
        <div className="carte__etat" role="alert">
          <p>{supprimer.error?.message}</p>
          <button
            type="button"
            className="bouton--danger"
            disabled={supprimer.isPending}
            onClick={() => supprimer.mutate({ id: archer.id, autoriserSuppressionEngage: true })}
          >
            Supprimer définitivement, avec ses résultats
          </button>
        </div>
      ) : (
        <MessageErreur erreur={supprimer.error} />
      )}
      {inscriptionsOuvertes && <InscriptionsArcher archerId={archer.id} tournoiId={tournoiId} />}
    </li>
  )
}

function FormulaireArcher({
  archer,
  tournoiId,
  onTermine,
}: {
  archer: Archer
  tournoiId: number
  onTermine: () => void
}) {
  const [nom, setNom] = useState(archer.nom)
  const [prenom, setPrenom] = useState(archer.prenom)
  const [categorieId, setCategorieId] = useState(String(archer.categorie_id))
  const [clubId, setClubId] = useState(archer.club_id === null ? '' : String(archer.club_id))
  // Handicap (E05US015) : **ressource séparée**, donc état et mutation séparés. Le mêler à
  // `modifier` obligerait à renvoyer nom/prénom/catégorie à chaque ajustement de handicap — et
  // écraserait une correction d'état civil faite entre-temps depuis un autre poste.
  const [handicapOfficiel, setHandicapOfficiel] = useState(
    archer.handicap_officiel === null ? '' : String(archer.handicap_officiel),
  )
  const [handicapSurcharge, setHandicapSurcharge] = useState(
    archer.handicap_surcharge === null ? '' : String(archer.handicap_surcharge),
  )
  const clubs = useClubs()
  const categories = useCategories(tournoiId)
  const modifier = useModifierArcher(tournoiId)
  const reglerHandicap = useDefinirHandicap(tournoiId)

  // Reprend la règle du domaine (nom et prénom non vides) pour éviter une requête vouée au 422 ;
  // le serveur reste l'autorité (revalidation à la frontière).
  const incomplet = nom.trim() === '' || prenom.trim() === '' || categorieId === ''

  const code = modifier.error instanceof ErreurApi ? modifier.error.code : null
  const homonymeSignale = code === 'homonyme_archer'
  const categorieSignalee = code === 'changement_categorie_archer_engage'

  // Les confirmations **s'accumulent** : le serveur teste les deux signalements à chaque appel et
  // n'en lève qu'un à la fois. Un bouton qui n'enverrait que *son* drapeau relancerait l'autre
  // 409 indéfiniment — l'archer engagé dont on corrige à la fois l'identité et la catégorie ne
  // serait alors jamais enregistrable. C'est le cas d'usage nominal du CA croisé avec celui
  // d'ADR-0014 (renseigner le club change `cle_identite`), pas un cas tordu.
  const [confirmations, setConfirmations] = useState<Partial<ModifierArcher>>({})

  // Un 409 porte sur **les valeurs exactes** envoyées. Dès qu'un champ change, le signalement ne
  // s'y applique plus : on l'efface — et avec lui les confirmations déjà données, qui portaient
  // sur ces valeurs-là. Sinon « Enregistrer quand même » confirmerait une saisie que le serveur
  // n'a jamais examinée, et le doublon que l'US refuse passerait par le bouton même prévu pour
  // l'autoriser. Même parti qu'à l'inscription (E02US002) : `reset()` plutôt que de comparer les
  // clés, ce qui exigerait de réimplémenter `cle_nom` en TS.
  const surChamp = (poser: (valeur: string) => void) => (valeur: string) => {
    if (modifier.error !== null) modifier.reset()
    setConfirmations({})
    poser(valeur)
  }

  const enregistrer = (nouvelles: Partial<ModifierArcher>) => {
    const cumul = { ...confirmations, ...nouvelles }
    setConfirmations(cumul)
    modifier.mutate(
      {
        id: archer.id,
        entree: {
          nom,
          prenom,
          categorie_id: Number(categorieId),
          club_id: clubId === '' ? null : Number(clubId),
          ...cumul,
        },
      },
      { onSuccess: onTermine },
    )
  }

  // ⚠️ Enregistrer l'état civil **ferme le panneau** (`onTermine`), donc emporte la saisie du
  // formulaire de handicap resté en attente. On avertit au lieu de perdre en silence : les deux
  // formulaires se remplissent naturellement l'un après l'autre, et rien ne signalait la perte.
  const handicapModifie =
    handicapOfficiel !==
      (archer.handicap_officiel === null ? '' : String(archer.handicap_officiel)) ||
    handicapSurcharge !==
      (archer.handicap_surcharge === null ? '' : String(archer.handicap_surcharge))

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (incomplet) return
    enregistrer({})
  }

  // Champ vide = **efface** le handicap, jamais « laisse en l'état » : même convention que
  // `club_id`. Le serveur reste l'autorité sur les **bornes**. ⚠️ **Mais il ne peut pas être
  // l'autorité sur ce qu'il ne voit jamais** : un `Number()` nu rend `NaN` sur `12,5` (la virgule
  // décimale que propose un pavé numérique en locale FR), et `JSON.stringify` sérialise `NaN` en
  // `null` — le serveur recevait « efface ce handicap », répondait **200**, et la surcharge
  // disparaissait pendant que l'écran affichait un succès.
  const lireEntier = (saisie: string): number | null | 'invalide' => {
    const texte = saisie.trim()
    if (texte === '') return null
    const valeur = Number(texte)
    return Number.isInteger(valeur) ? valeur : 'invalide'
  }

  const officielLu = lireEntier(handicapOfficiel)
  const surchargeLue = lireEntier(handicapSurcharge)
  const handicapIllisible = officielLu === 'invalide' || surchargeLue === 'invalide'

  const soumettreHandicap = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (officielLu === 'invalide' || surchargeLue === 'invalide') return
    reglerHandicap.mutate({
      id: archer.id,
      entree: { officiel: officielLu, surcharge: surchargeLue },
    })
  }

  return (
    <div>
      <h4 className="carte__soustitre">Modifier l'archer</h4>
      <form className="formulaire" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={nom}
          onChange={(e) => surChamp(setNom)(e.target.value)}
          placeholder="Nom de l'archer"
          aria-label="Nom de l'archer"
        />
        <input
          className="formulaire__champ"
          value={prenom}
          onChange={(e) => surChamp(setPrenom)(e.target.value)}
          placeholder="Prénom de l'archer"
          aria-label="Prénom de l'archer"
        />
        <select
          className="formulaire__champ"
          value={categorieId}
          onChange={(e) => surChamp(setCategorieId)(e.target.value)}
          aria-label="Catégorie de l'archer"
        >
          <option value="">Choisir une catégorie…</option>
          {(categories.data ?? []).map((categorie) => (
            <option key={categorie.id} value={categorie.id}>
              {categorie.libelle}
            </option>
          ))}
        </select>
        <select
          className="formulaire__champ"
          value={clubId}
          onChange={(e) => surChamp(setClubId)(e.target.value)}
          aria-label="Club de l'archer"
        >
          <option value="">Club inconnu</option>
          {(clubs.data ?? []).map((club) => (
            <option key={club.id} value={club.id}>
              {club.nom}
            </option>
          ))}
        </select>
        <div className="formulaire__actions">
          <button type="submit" disabled={modifier.isPending || incomplet}>
            Enregistrer
          </button>
          <button type="button" className="bouton--discret" onClick={onTermine}>
            Annuler
          </button>
        </div>
        {handicapModifie && (
          <p className="carte__etat" role="status">
            Le handicap saisi ci-dessous n'est pas encore enregistré : utilisez son propre bouton
            avant de valider l'état civil.
          </p>
        )}
      </form>
      {/* Le handicap se règle **à part** de l'état civil : deux formulaires, deux enregistrements.
          C'est le pendant à l'écran de la ressource séparée côté API, et cela évite qu'un
          ajustement de handicap ne renvoie (donc n'écrase) l'identité de l'archer. */}
      <form className="formulaire" onSubmit={soumettreHandicap}>
        <p className="carte__aide">
          Handicap : il s'ajoute au score réalisé. Laissez vide si l'archer n'est pas évalué. La
          surcharge, si elle est renseignée, remplace le handicap du club pour ce seul tournoi.
        </p>
        <input
          className="formulaire__champ"
          inputMode="numeric"
          value={handicapOfficiel}
          onChange={(e) => setHandicapOfficiel(e.target.value)}
          placeholder="Handicap officiel (club)"
          aria-label="Handicap officiel de l'archer"
        />
        <input
          className="formulaire__champ"
          inputMode="numeric"
          value={handicapSurcharge}
          onChange={(e) => setHandicapSurcharge(e.target.value)}
          placeholder="Surcharge pour ce tournoi"
          aria-label="Surcharge de handicap de l'archer"
        />
        <div className="formulaire__actions">
          <button type="submit" disabled={reglerHandicap.isPending || handicapIllisible}>
            Enregistrer le handicap
          </button>
        </div>
        {handicapIllisible && (
          <p className="carte__etat carte__etat--erreur" role="alert">
            Un handicap est un nombre entier de points (sans virgule).
          </p>
        )}
        {/* Un retour de succès explicite : sans lui, rien ne distingue « enregistré » de « pas
            cliqué ». Le formulaire ne se referme pas — on règle souvent les deux valeurs à la
            suite. */}
        {reglerHandicap.isSuccess && !handicapIllisible && (
          <p className="carte__etat carte__etat--ok" role="status">
            Handicap enregistré.
          </p>
        )}
      </form>
      {reglerHandicap.isError && <MessageErreur erreur={reglerHandicap.error} />}
      {/* Ton **neutre** (pas de `--erreur`) et une action : ces deux-là ne sont pas des erreurs,
          l'édition reste possible. Chaque bouton ne confirme que **son** motif — jamais les deux
          d'un coup, ce qui ferait acquiescer à un motif jamais affiché — mais les confirmations
          **s'ajoutent** (cf. `cumul` ci-dessus) : si les deux faits sont vrais, l'admin lève le
          premier signalement, voit le second, le lève à son tour, et l'édition passe.
          Examiné en E00US013 : laissé tel quel — c'est une confirmation à action, pas un
          affichage d'erreur, donc hors du `MessageErreur` partagé (le token `--erreur` ne s'y
          applique pas). */}
      {homonymeSignale && (
        <div className="carte__etat" role="alert">
          <p>{modifier.error?.message}</p>
          <button
            type="button"
            onClick={() => enregistrer({ autoriser_homonyme: true })}
            disabled={modifier.isPending || incomplet}
          >
            Enregistrer quand même
          </button>
        </div>
      )}
      {categorieSignalee && (
        <div className="carte__etat" role="alert">
          <p>{modifier.error?.message}</p>
          <button
            type="button"
            onClick={() => enregistrer({ autoriser_changement_categorie: true })}
            disabled={modifier.isPending || incomplet}
          >
            Changer quand même de catégorie
          </button>
        </div>
      )}
      {!homonymeSignale && !categorieSignalee && <MessageErreur erreur={modifier.error} />}
    </div>
  )
}
