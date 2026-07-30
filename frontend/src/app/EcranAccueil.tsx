// Écran d'accueil : choisir son appareil / rôle — E00US017, ADR-0042.
//
// Au 1ᵉʳ lancement (aucun rôle mémorisé), l'app présente **quatre portes explicites** au lieu de
// deviner le rôle d'une session ouverte. Le choix est mémorisé (`sessionRoleStore`) : on n'y revient
// qu'en changeant de rôle. Habillage **club/neutre** (jetons de thème existants, clair/sombre
// système) — l'identité *par tournoi* est hors périmètre ici (écran pré-tournoi, cf. E01US016).

import type { Role } from '../shared/stores/sessionRoleStore'
import './EcranAccueil.css'

// Une porte = un rôle, une icône, un intitulé et une phrase qui dit **à qui c'est** et **ce qu'on y
// fait** — pour qu'un bénévole choisisse sans hésiter.
const PORTES: { role: Role; icone: string; titre: string; description: string }[] = [
  {
    role: 'tablette',
    icone: '🎯',
    titre: 'Tablette de cible',
    description: 'Cette tablette saisit les scores d’une cible.',
  },
  {
    role: 'public',
    icone: '📱',
    titre: 'Téléphone (public)',
    description: 'Suivre le tournoi : classements, plans, mes archers.',
  },
  {
    role: 'scoreur',
    icone: '✅',
    titre: 'Scoreur',
    description: 'Valider les scores avec mon code.',
  },
  {
    role: 'admin',
    icone: '🖥️',
    titre: 'Administration (PC)',
    description: 'Organiser et piloter le tournoi.',
  },
]

// Depuis E14US003, le choix n'est plus posé ici : franchir une porte doit **aussi** changer l'adresse
// (`/cible`, `/public`…), et les deux gestes ne peuvent pas se séparer sans risquer de diverger. Le
// shell fait les deux d'un coup et passe le résultat en `onChoisir`.
export function EcranAccueil({ onChoisir }: { onChoisir: (role: Role) => void }) {
  return (
    <div className="accueil">
      <p className="accueil__intro">
        Choisissez comment cet appareil sera utilisé. Ce choix est mémorisé : on ne vous le
        redemandera pas au prochain lancement.
      </p>
      <ul className="accueil__portes">
        {PORTES.map((p) => (
          <li key={p.role}>
            <button type="button" className="accueil__porte" onClick={() => onChoisir(p.role)}>
              <span className="accueil__icone" aria-hidden="true">
                {p.icone}
              </span>
              <span className="accueil__titre">{p.titre}</span>
              <span className="accueil__description">{p.description}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
