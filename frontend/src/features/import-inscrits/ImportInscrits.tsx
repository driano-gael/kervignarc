// « Importer une liste » (E02US007, maquette A09) : déposer un export Ianseo ou Résult'Arc, lire le
// rapport, cocher les homonymes à garder, confirmer. ⚠️ Rien n'est écrit avant « Importer » : le
// dépôt ne produit qu'un aperçu, et la confirmation écrit tout le fichier ou rien (ADR-0115).

import { useState } from 'react'
import { useCategories } from '../categories/hooks'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import type { LigneRapport, RapportImport } from './api'
import { useApercuImport, useConfirmerImport } from './hooks'

const SOURCES: Record<RapportImport['source'], string> = {
  ianseo: 'Export Ianseo',
  resultarc: "Classeur Résult'Arc",
}

export function ImportInscrits({ tournoiId }: { tournoiId: number }) {
  const [fichier, setFichier] = useState<File | null>(null)
  const [cochees, setCochees] = useState<number[]>([])
  const apercu = useApercuImport(tournoiId)
  const confirmer = useConfirmerImport(tournoiId)
  const categories = useCategories(tournoiId)
  const libelleCategorie = (id: number | null) =>
    categories.data?.find((c) => c.id === id)?.libelle ?? '—'

  const deposer = (choisi: File | null) => {
    setFichier(choisi)
    setCochees([])
    confirmer.reset()
    if (choisi !== null) apercu.mutate(choisi)
  }

  const basculer = (numero: number) =>
    setCochees((actuelles) =>
      actuelles.includes(numero) ? actuelles.filter((n) => n !== numero) : [...actuelles, numero],
    )

  // Après confirmation, c'est le rapport **final** qui s'affiche : le plan est recalculé côté
  // serveur, il peut différer de l'aperçu si un inscrit a été ajouté entre-temps.
  const rapport = confirmer.data ?? apercu.data
  const aEcrire = (apercu.data?.importables ?? 0) + cochees.length

  return (
    <section className="carte" aria-label="Importer une liste">
      <h3>Importer une liste</h3>
      <p className="carte__etat">
        Export Ianseo (.csv) ou classeur Résult&apos;Arc (.xls). Rien n&apos;est enregistré avant «
        Importer » ; le fichier est alors écrit en entier, ou pas du tout.
      </p>
      <input
        type="file"
        accept=".csv,.xls,text/csv,application/vnd.ms-excel"
        aria-label="Fichier d'inscrits"
        onChange={(e) => deposer(e.target.files?.[0] ?? null)}
      />
      {apercu.isPending && <p className="carte__etat">Lecture du fichier…</p>}
      <MessageErreur erreur={apercu.error ?? confirmer.error} />
      {rapport !== undefined && (
        <>
          <p className="carte__etat" role="status">
            {confirmer.isSuccess ? 'Import terminé — ' : `${SOURCES[rapport.source]} — `}
            {confirmer.isSuccess
              ? `${rapport.importables} ligne${rapport.importables > 1 ? 's' : ''} importée${rapport.importables > 1 ? 's' : ''}`
              : `${rapport.importables} à importer`}
            , {rapport.rejetees} rejetée{rapport.rejetees > 1 ? 's' : ''}, {rapport.homonymes}{' '}
            homonyme{rapport.homonymes > 1 ? 's' : ''} à trancher.
          </p>
          {rapport.colonnes_ignorees.length > 0 && (
            <p className="carte__etat">
              Colonnes lues mais non reprises : {rapport.colonnes_ignorees.join(', ')}.
            </p>
          )}
          <div className="table-defilement">
            <table className="table">
              <thead>
                <tr>
                  <th>Ligne</th>
                  <th>Archer</th>
                  <th>Licence</th>
                  <th>Départ</th>
                  <th>Catégorie</th>
                  <th>Club</th>
                  <th>Suite donnée</th>
                </tr>
              </thead>
              <tbody>
                {rapport.lignes.map((ligne) => (
                  <tr key={ligne.numero}>
                    <td>{ligne.numero}</td>
                    <td>{identite(ligne)}</td>
                    <td>{ligne.licence ?? '—'}</td>
                    <td>{ligne.depart_numero ?? '—'}</td>
                    <td>
                      {ligne.categorie_id === null ? '—' : libelleCategorie(ligne.categorie_id)}
                    </td>
                    <td>
                      {ligne.club ?? '—'}
                      {ligne.club_a_creer && ' (nouveau)'}
                    </td>
                    <td>
                      <SuiteDonnee
                        ligne={ligne}
                        cochee={cochees.includes(ligne.numero)}
                        modifiable={!confirmer.isSuccess}
                        onBasculer={() => basculer(ligne.numero)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!confirmer.isSuccess && fichier !== null && (
            <button
              type="button"
              disabled={aEcrire === 0 || confirmer.isPending || apercu.isPending}
              onClick={() => confirmer.mutate({ fichier, homonymes: cochees })}
            >
              Importer {aEcrire} ligne{aEcrire > 1 ? 's' : ''}
            </button>
          )}
        </>
      )}
    </section>
  )
}

function identite(ligne: LigneRapport): string {
  const nom = [ligne.prenom, ligne.nom].filter(Boolean).join(' ')
  return nom === '' ? '—' : nom
}

function SuiteDonnee({
  ligne,
  cochee,
  modifiable,
  onBasculer,
}: {
  ligne: LigneRapport
  cochee: boolean
  modifiable: boolean
  onBasculer: () => void
}) {
  switch (ligne.decision) {
    case 'creer':
      return (
        <>
          {ligne.homonyme_de
            ? `Nouvelle fiche (homonyme de ${ligne.homonyme_de} confirmé)`
            : 'Nouvelle fiche'}
        </>
      )
    case 'inscrire':
      return <>Fiche existante, inscrite sur ce départ</>
    case 'rejetee':
      return <span className="table__anomalie">Rejetée : {ligne.motif}</span>
    case 'homonyme':
      return (
        <label>
          <input type="checkbox" checked={cochee} disabled={!modifiable} onChange={onBasculer} />{' '}
          Homonyme de {ligne.homonyme_de} — cocher s&apos;il s&apos;agit d&apos;une autre personne
        </label>
      )
  }
}
