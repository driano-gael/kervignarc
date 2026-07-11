// Client WebSocket temps réel (E00US010) — se connecte à `/ws`, se reconnecte seul.
//
// Le serveur pousse des `LiveEvent` après commit (E00US008) ; le message d'accueil
// `connected` confirme l'abonnement. En cas de coupure, reconnexion automatique
// (CDC technique §6.3) — encaisser les coupures brèves du wifi de compétition.

import type { StatutConnexion } from '../stores/connexionStore'
import type { LiveEvent } from './types'

export interface OptionsRealtime {
  onStatut: (statut: StatutConnexion) => void
  onEvenement: (evenement: LiveEvent) => void
}

const DELAI_RECONNEXION_MS = 1000

export class RealtimeClient {
  private readonly options: OptionsRealtime
  private ws: WebSocket | null = null
  private actif = true
  private timerReconnexion: number | undefined

  constructor(options: OptionsRealtime) {
    this.options = options
  }

  connecter(): void {
    this.options.onStatut('connexion')
    const protocole = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocole}//${window.location.host}/ws`)
    this.ws = ws

    ws.onopen = () => this.options.onStatut('connecte')

    ws.onmessage = (message) => {
      const evenement = JSON.parse(message.data as string) as LiveEvent
      // Le message d'accueil ne porte pas de mise à jour de données.
      if (evenement.type !== 'connected') this.options.onEvenement(evenement)
    }

    ws.onclose = () => {
      this.options.onStatut('deconnecte')
      if (this.actif) this.programmerReconnexion()
    }

    ws.onerror = () => ws.close()
  }

  fermer(): void {
    this.actif = false
    if (this.timerReconnexion !== undefined) window.clearTimeout(this.timerReconnexion)
    this.ws?.close()
  }

  private programmerReconnexion(): void {
    this.timerReconnexion = window.setTimeout(() => this.connecter(), DELAI_RECONNEXION_MS)
  }
}
