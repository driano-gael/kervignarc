// Écran d'accueil : choisir son appareil / rôle — E00US017, ADR-0042.
//
// Au 1ᵉʳ lancement (aucun rôle mémorisé), l'app présente **quatre portes explicites** au lieu de
// deviner le rôle d'une session ouverte. Le choix est mémorisé (`sessionRoleStore`) : on n'y revient
// qu'en changeant de rôle. Habillage **club/neutre** (jetons de thème existants, clair/sombre
// système) — l'identité *par tournoi* est hors périmètre ici (écran pré-tournoi, cf. E01US016).

import type { Porte } from '../shared/navigation/routeur'
import './EcranAccueil.css'

// Une porte = une icône, un intitulé et une phrase qui dit **à qui c'est** et **ce qu'on y fait** —
// pour qu'un bénévole choisisse sans hésiter.
//
// **Cinq portes depuis le retour maquettes du 04/08/2026** (A00). Deux décisions y sont reversées :
//
//  - *« il faudrait quand même ajouter une porte pour le ou les écrans de projections »* → la porte
//    « Écran de salle ». Elle ne crée pas un monde : c'est un poste comme un autre (cf. `Porte` dans
//    `routeur.ts`), mais le bénévole qui installe le vidéoprojecteur doit la **voir**, au lieu de
//    devoir deviner qu'elle se cache derrière « tablette de cible ».
//  - le tableau « Vocabulaire » du même questionnaire : *tablette de cible → **écran de cible***,
//    *téléphone (public) → **public***. Le mot « tablette » promettait un appareil précis alors que
//    la réponse à la question 3 dit l'inverse (*« les tablettes de cible doivent pouvoir s'adapter à
//    un téléphone »*) ; « téléphone (public) » avait le même défaut, dans l'autre sens — le public
//    consulte aussi depuis une tablette posée à l'accueil.
//
// L'ordre suit le parc : les deux appareils **rattachés à un lieu** d'abord (ils s'installent le
// matin, une fois), les appareils **personnels** ensuite, le PC d'organisation en dernier.
const PORTES: { porte: Porte; icone: string; titre: string; description: string }[] = [
  {
    porte: 'tablette',
    icone: '🎯',
    titre: 'Écran de cible',
    description: 'Cet appareil saisit les scores d’une cible.',
  },
  {
    porte: 'salle',
    icone: '📺',
    titre: 'Écran de salle',
    description: 'Projection : classements et plans en continu, sans personne devant.',
  },
  {
    porte: 'public',
    icone: '📱',
    titre: 'Public',
    description: 'Suivre le tournoi : classements, plans, mes archers.',
  },
  {
    porte: 'scoreur',
    icone: '✅',
    titre: 'Scoreur',
    description: 'Valider les scores avec mon code.',
  },
  {
    porte: 'admin',
    icone: '🖥️',
    titre: 'Administration (PC)',
    description: 'Organiser et piloter le tournoi.',
  },
]

// Depuis E14US003, le choix n'est plus posé ici : franchir une porte doit **aussi** changer l'adresse
// (`/cible`, `/public`…), et les deux gestes ne peuvent pas se séparer sans risquer de diverger. Le
// shell fait les deux d'un coup et passe le résultat en `onChoisir`.
export function EcranAccueil({ onChoisir }: { onChoisir: (porte: Porte) => void }) {
  return (
    <div className="accueil">
      <p className="accueil__intro">
        Choisissez comment cet appareil sera utilisé. Ce choix est mémorisé : on ne vous le
        redemandera pas au prochain lancement.
      </p>
      <ul className="accueil__portes">
        {PORTES.map((p) => (
          <li key={p.porte}>
            <button type="button" className="accueil__porte" onClick={() => onChoisir(p.porte)}>
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
