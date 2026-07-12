// Écran d'accès administrateur (E10US002).
//
// Deux situations, distinguées par l'état renvoyé par le backend :
// - **1ᵉʳ accès** (`configure === false`) : aucun identifiant n'existe encore → l'organisateur
//   *définit* son login + mot de passe (avec confirmation) ; l'app le connecte aussitôt ;
// - **accès existant** (`configure === true`) : l'organisateur *se connecte* (login + mot de passe).
// En cas de succès, le jeton est stocké (store de session) et l'écran appelant bascule vers les
// fonctions admin. La lecture publique n'a jamais besoin de cet écran.

import { useState } from 'react'
import { ErreurApi } from '../../shared/api/client'
import { useConfigurerAdmin, useConnexionAdmin, useEtatAuth } from './hooks'

export function ConnexionAdmin() {
  const etat = useEtatAuth()

  if (etat.isPending) return <p className="carte__etat">Chargement…</p>
  if (etat.isError) {
    return (
      <p className="carte__etat carte__etat--erreur">
        Accès admin injoignable — {etat.error.message}
      </p>
    )
  }
  return etat.data.configure ? <FormulaireConnexion /> : <FormulairePremierAcces />
}

function FormulairePremierAcces() {
  const [login, setLogin] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const configurer = useConfigurerAdmin()

  const incomplet = login.trim() === '' || motDePasse === ''
  const discordance = confirmation !== '' && confirmation !== motDePasse

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (incomplet || motDePasse !== confirmation) return
    configurer.mutate({ login: login.trim(), mot_de_passe: motDePasse })
  }

  return (
    <div>
      <h3 className="carte__soustitre">Définir l'accès administrateur</h3>
      <p className="carte__etat">
        Premier lancement : choisissez l'identifiant et le mot de passe de l'organisateur.
      </p>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={login}
          onChange={(e) => setLogin(e.target.value)}
          placeholder="Identifiant"
          aria-label="Identifiant administrateur"
          autoComplete="username"
        />
        <input
          className="formulaire__champ"
          type="password"
          value={motDePasse}
          onChange={(e) => setMotDePasse(e.target.value)}
          placeholder="Mot de passe"
          aria-label="Mot de passe administrateur"
          autoComplete="new-password"
        />
        <input
          className="formulaire__champ"
          type="password"
          value={confirmation}
          onChange={(e) => setConfirmation(e.target.value)}
          placeholder="Confirmer le mot de passe"
          aria-label="Confirmer le mot de passe"
          autoComplete="new-password"
        />
        <button type="submit" disabled={configurer.isPending || incomplet || discordance}>
          Définir l'accès
        </button>
      </form>
      {discordance && (
        <p className="carte__etat carte__etat--erreur">
          Les deux mots de passe ne correspondent pas.
        </p>
      )}
      <MessageErreur erreur={configurer.error} />
    </div>
  )
}

function FormulaireConnexion() {
  const [login, setLogin] = useState('')
  const [motDePasse, setMotDePasse] = useState('')
  const connexion = useConnexionAdmin()

  const incomplet = login.trim() === '' || motDePasse === ''

  const soumettre = (evenement: React.FormEvent) => {
    evenement.preventDefault()
    if (incomplet) return
    connexion.mutate({ login: login.trim(), mot_de_passe: motDePasse })
  }

  return (
    <div>
      <h3 className="carte__soustitre">Connexion administrateur</h3>
      <form className="formulaire formulaire--colonne" onSubmit={soumettre}>
        <input
          className="formulaire__champ"
          value={login}
          onChange={(e) => setLogin(e.target.value)}
          placeholder="Identifiant"
          aria-label="Identifiant administrateur"
          autoComplete="username"
        />
        <input
          className="formulaire__champ"
          type="password"
          value={motDePasse}
          onChange={(e) => setMotDePasse(e.target.value)}
          placeholder="Mot de passe"
          aria-label="Mot de passe administrateur"
          autoComplete="current-password"
        />
        <button type="submit" disabled={connexion.isPending || incomplet}>
          Se connecter
        </button>
      </form>
      <MessageErreur erreur={connexion.error} />
    </div>
  )
}

function MessageErreur({ erreur }: { erreur: Error | null }) {
  if (erreur === null) return null
  const message = erreur instanceof ErreurApi ? erreur.message : 'Une erreur est survenue.'
  return <p className="carte__etat carte__etat--erreur">{message}</p>
}
