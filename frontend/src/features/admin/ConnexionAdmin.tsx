// Écran d'accès administrateur (E10US002).
//
// Deux situations, distinguées par l'état renvoyé par le backend :
// - **1ᵉʳ accès** (`configure === false`) : aucun identifiant n'existe encore → l'organisateur
//   *définit* son login + mot de passe (avec confirmation) ; l'app le connecte aussitôt ;
// - **accès existant** (`configure === true`) : l'organisateur *se connecte* (login + mot de passe).
// En cas de succès, le jeton est stocké (store de session) et l'écran appelant bascule vers les
// fonctions admin. La lecture publique n'a jamais besoin de cet écran.

import { useState } from 'react'
import { MessageErreur } from '../../shared/ui/MessageErreur'
import { useConfigurerAdmin, useConnexionAdmin, useEtatAuth } from './hooks'

export function ConnexionAdmin() {
  const etat = useEtatAuth()

  if (etat.isPending) return <p className="carte__etat">Chargement…</p>
  if (etat.isError) {
    return (
      <p className="carte__etat carte__etat--erreur" role="alert">
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
    <>
      <h2 className="carte__entete">Définir l'accès administrateur</h2>
      <div className="connexion__corps">
        <p className="carte__etat">
          Premier lancement : choisissez l'identifiant et le mot de passe de l'organisateur.
        </p>
        <form onSubmit={soumettre}>
          <ChampConnexion libelle="Identifiant">
            <input
              className="formulaire__champ"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              autoComplete="username"
            />
          </ChampConnexion>
          <ChampConnexion libelle="Mot de passe">
            <input
              className="formulaire__champ"
              type="password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              autoComplete="new-password"
            />
          </ChampConnexion>
          <ChampConnexion libelle="Confirmer le mot de passe">
            <input
              className="formulaire__champ"
              type="password"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              autoComplete="new-password"
            />
          </ChampConnexion>
          <button
            type="submit"
            className="connexion__envoi"
            disabled={configurer.isPending || incomplet || discordance}
          >
            Définir l'accès
          </button>
        </form>
        {discordance && (
          <p className="carte__etat carte__etat--erreur" role="alert">
            Les deux mots de passe ne correspondent pas.
          </p>
        )}
        <MessageErreur erreur={configurer.error} />
      </div>
    </>
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
    <>
      <h2 className="carte__entete">Connexion administrateur</h2>
      <div className="connexion__corps">
        <form onSubmit={soumettre}>
          <ChampConnexion libelle="Identifiant">
            <input
              className="formulaire__champ"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              autoComplete="username"
            />
          </ChampConnexion>
          <ChampConnexion libelle="Mot de passe">
            <input
              className="formulaire__champ"
              type="password"
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              autoComplete="current-password"
            />
          </ChampConnexion>
          <button
            type="submit"
            className="connexion__envoi"
            disabled={connexion.isPending || incomplet}
          >
            Se connecter
          </button>
        </form>
        <MessageErreur erreur={connexion.error} />
      </div>
    </>
  )
}

/**
 * Un champ du formulaire de connexion : **libellé visible au-dessus**, comme sur la planche A01
 * (E17US003).
 *
 * Le formulaire n'avait jusqu'ici que des `placeholder` et un `aria-label`. Ce n'est pas seulement un
 * écart de maquette : un `placeholder` **disparaît dès la première frappe**, donc celui qui
 * s'interrompt en cours de saisie n'a plus rien pour savoir quel champ il remplissait — et il n'est
 * pas annoncé comme un libellé. Le `<label>` enveloppant associe le texte au champ sans avoir à
 * gérer d'`id`, et rend le `aria-label` inutile : le laisser en plus **remplacerait** le texte visible
 * pour un lecteur d'écran, donc ferait diverger ce qui est lu de ce qui est vu.
 */
function ChampConnexion({ libelle, children }: { libelle: string; children: React.ReactNode }) {
  return (
    <label className="connexion__champ">
      <span className="connexion__etiquette">{libelle}</span>
      {children}
    </label>
  )
}
