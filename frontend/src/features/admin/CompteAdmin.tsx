// Écran « Compte administrateur » (E10US006) : changer l'identifiant et/ou le mot de passe.
// Les règles (mot de passe actuel, rien d'inchangé, autres sessions fermées) sont au serveur.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { ChampConnexion } from './ConnexionAdmin'
import { useModifierIdentifiants } from './hooks'

export function CompteAdmin() {
  const [actuel, setActuel] = useState('')
  const [login, setLogin] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const modifier = useModifierIdentifiants()

  const rienDemande = login.trim() === '' && motDePasse === ''
  const discordance = motDePasse !== confirmation
  const incomplet = actuel === '' || rienDemande

  // Une nouvelle saisie rend caduc le dernier succès ou refus affiché. ⚠️ Jamais pendant l'envoi :
  // `reset()` détacherait la requête en cours, et un succès réel ne s'afficherait pas.
  const saisir = (setter: (valeur: string) => void) => (e: React.ChangeEvent<HTMLInputElement>) => {
    if (modifier.isSuccess || modifier.isError) modifier.reset()
    setter(e.target.value)
  }

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (incomplet || discordance) return
    modifier.mutate(
      {
        mot_de_passe_actuel: actuel,
        ...(login.trim() !== '' && { nouveau_login: login.trim() }),
        ...(motDePasse !== '' && { nouveau_mot_de_passe: motDePasse }),
      },
      {
        onSuccess: () => {
          setActuel('')
          setLogin('')
          setMotDePasse('')
          setConfirmation('')
        },
      },
    )
  }

  return (
    <section className="carte">
      <h2 className="carte__entete">Compte administrateur</h2>
      <div className="connexion__corps">
        <form onSubmit={soumettre}>
          <ChampConnexion libelle="Mot de passe actuel">
            <input
              className="formulaire__champ"
              type="password"
              value={actuel}
              onChange={saisir(setActuel)}
              autoComplete="current-password"
            />
          </ChampConnexion>
          <ChampConnexion libelle="Nouvel identifiant (vide = inchangé)">
            <input
              className="formulaire__champ"
              value={login}
              onChange={saisir(setLogin)}
              autoComplete="off"
            />
          </ChampConnexion>
          <ChampConnexion libelle="Nouveau mot de passe (vide = inchangé)">
            <input
              className="formulaire__champ"
              type="password"
              value={motDePasse}
              onChange={saisir(setMotDePasse)}
              autoComplete="new-password"
            />
          </ChampConnexion>
          <ChampConnexion libelle="Confirmer le nouveau mot de passe">
            <input
              className="formulaire__champ"
              type="password"
              value={confirmation}
              onChange={saisir(setConfirmation)}
              autoComplete="new-password"
            />
          </ChampConnexion>
          <button
            type="submit"
            className="connexion__envoi"
            disabled={modifier.isPending || incomplet || discordance}
          >
            Enregistrer
          </button>
        </form>
        {confirmation !== '' && discordance && (
          <p className="carte__etat carte__etat--erreur" role="alert">
            Les deux nouveaux mots de passe ne correspondent pas.
          </p>
        )}
        {modifier.isSuccess && (
          <p className="carte__etat carte__etat--ok" role="status">
            Identifiants modifiés. Les autres appareils connectés en administrateur ont été
            déconnectés ; celui-ci reste connecté.
          </p>
        )}
        <MessageErreur erreur={modifier.error} />
      </div>
    </section>
  )
}
