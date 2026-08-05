/* ═══════════════════════════════════════════════════════════════════════════
   Kervignarc — ossature des maquettes plein écran
   ---------------------------------------------------------------------------
   Ce fichier fait deux choses, et rien d'autre :

   1. il CONSTRUIT le cadre applicatif autour de chaque planche (bande d'en-tête,
      coquille, navigation, bandeau de contexte, aide) à partir des attributs
      `data-*` posés sur la planche ;
   2. il CALCULE l'échelle `--k` pour que le cadre tienne dans la page.

   Il ne touche JAMAIS au contenu de `.ecran` : ce nœud est écrit à la main dans
   la page et seulement DÉPLACÉ dans la zone de contenu (appendChild). C'est ce
   qui permet de corriger une maquette en séance sans passer par un générateur.

   ---------------------------------------------------------------------------
   SOURCE DE LA NAVIGATION — relevée le 05/08/2026 dans :
     frontend/src/features/admin/axes.ts        (AXES, AXE_PAR_DESTINATION)
     frontend/src/features/admin/CoquilleAdmin.tsx (ordre et libellés)
     frontend/src/app/App.css                   (dimensions)
   Toute US qui ajoute ou renomme une destination désynchronise ce fichier.
   Le point de reprise du README porte la consigne de resynchronisation.

   ---------------------------------------------------------------------------
   JEU DE CHIFFRES UNIQUE — le même tournoi sur les 145 planches, sinon la
   critique portera sur l'incohérence plutôt que sur la mise en page :

     Tournoi     « Challenge des champions » — 22/11/2026, salle de Kervignarc
     Inscrits    156          Cibles      30 (2 archers par cible en qualif)
     Départs     3            Scoreurs    4
     Départ 2    09 h 30, en tir          Blasons     trispot 40 / mono 40
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict'

  // — Cadres physiques ——————————————————————————————————————————————————————
  // L'écran est NU : pas de chrome navigateur. Exact pour la cible et le
  // vidéoprojecteur (plein écran le jour J) ; optimiste d'environ 120 px sur PC
  // et téléphone, où une barre d'adresse mange le haut. Décision assumée.
  var APPAREILS = {
    pc:        { libelle: 'PC',              large: 1600, haut: 900 },
    tablette:  { libelle: 'Tablette',        large: 1280, haut: 800 },
    salle:     { libelle: 'Vidéoprojecteur', large: 1920, haut: 1080 },
    telephone: { libelle: 'Téléphone',       large: 390,  haut: 844 },
  }

  var AXES = {
    pilotage: { libelle: 'Pilotage', besoinTournoi: true },
    gestion:  { libelle: 'Gestion',  besoinTournoi: true },
    atelier:  { libelle: 'Atelier',  besoinTournoi: false },
  }

  // Ordre = celui du tableau `destinations` de CoquilleAdmin.tsx, filtré par axe.
  var DESTINATIONS = {
    pilotage: [
      ['accueil', 'Accueil (tableau de bord)'],
      ['assemblage', 'Assemblage'],
      ['plan', 'Plan de salle'],
      ['bareme', 'Barème & validation'],
      ['phases', 'Phases (format)'],
      ['departs', 'Départs & tarifs'],
      ['scoreurs', 'Scoreurs'],
      ['placement', 'Placement'],
      ['duels', 'Plan de duels'],
      ['postes', 'Postes de cible'],
      ['simulation', 'Simulation'],
      ['supervision', 'Supervision'],
      ['ecrans', 'Écrans de salle'],
      ['suivi-deroule', 'Suivi du déroulé'],
      ['feu-vert', 'Feu vert'],
      ['completude', 'Complétude'],
      ['classement', 'Classement en direct'],
      ['palmares', 'Palmarès'],
    ],
    gestion: [
      ['inscriptions', 'Inscriptions'],
      ['doublons', 'Doublons'],
      ['paiements', 'Paiements'],
      ['exports', 'Exports'],
      ['archive', 'Archive'],
    ],
    atelier: [
      ['categories', 'Catégories'],
      ['blasons', 'Blasons'],
      ['formats', 'Formats (déroulés)'],
      ['deroule', 'Composer un déroulé'],
      ['gabarits', 'Gabarits (modèles)'],
      ['clubs', 'Clubs'],
      ['jeu-essai', 'Jeu d’essai'],
    ],
  }

  // — Fabrique ——————————————————————————————————————————————————————————————
  function el(balise, classe, texte) {
    var n = document.createElement(balise)
    if (classe) n.className = classe
    if (texte !== undefined && texte !== null) n.textContent = texte
    return n
  }

  function lire(p, nom, defaut) {
    var v = p.getAttribute('data-' + nom)
    return v === null || v === '' ? defaut : v
  }

  function enteteAppli(p, titre, avecRole) {
    var e = el('div', 'app__entete')
    e.appendChild(el('p', 'app__titre', titre))
    var actions = el('div', 'app__actions')
    if (avecRole) actions.appendChild(el('span', 'app__changer-role', 'Changer de rôle'))
    var hors = lire(p, 'connexion', 'connecte') === 'hors-ligne'
    var conn = el('span', 'conn' + (hors ? ' off' : ''))
    conn.appendChild(el('span', 'point'))
    conn.appendChild(el('span', null, hors ? 'Hors ligne' : 'Connecté'))
    actions.appendChild(conn)
    e.appendChild(actions)
    return e
  }

  function bandeauContexte(p, axeLib, ecranLib) {
    var b = el('div', 'bandeau-contexte')
    b.appendChild(el('span', 'bandeau-contexte__tournoi', lire(p, 'tournoi', 'Challenge des champions')))
    b.appendChild(el('span', 'pas marque', lire(p, 'statut', 'en cours').toUpperCase()))
    b.appendChild(el('span', 'bandeau-contexte__date', lire(p, 'date', '22 novembre 2026')))
    var dep = lire(p, 'depart', 'Départ 2 · 09 h 30 — en tir')
    if (dep !== 'aucun') b.appendChild(el('span', 'bandeau-contexte__depart', dep))
    b.appendChild(el('span', 'bandeau-contexte__fil', axeLib + ' › ' + ecranLib))
    return b
  }

  function navigationAdmin(p, axe, ecranActif) {
    var def = AXES[axe]
    var nav = el('nav', 'coquille__nav')
    nav.setAttribute('aria-label', "Navigation d'administration")
    nav.appendChild(el('button', 'coquille__retour', '← Accueil'))
    nav.appendChild(el('p', 'coquille__axe', def.libelle))

    if (def.besoinTournoi) {
      var rech = el('div', 'coquille__recherche')
      rech.appendChild(el('span', 'mini', 'Chercher un archer'))
      rech.appendChild(el('div', 'champ', 'Nom, licence…'))
      nav.appendChild(rech)

      var sel = el('div', 'coquille__selecteur')
      sel.appendChild(el('span', 'mini', 'Tournoi'))
      var rang = el('div', 'rang-select')
      rang.appendChild(el('div', 'champ plein', lire(p, 'tournoi', 'Challenge des champions') + '  ▾'))
      rang.appendChild(el('span', 'pas ok', lire(p, 'statut', 'en cours').toUpperCase()))
      sel.appendChild(rang)
      nav.appendChild(sel)
    }

    var liste = el('ul', 'coquille__liens')
    var trouve = false
    DESTINATIONS[axe].forEach(function (d) {
      var li = el('li')
      var actif = d[0] === ecranActif
      if (actif) trouve = true
      var b = el('button', 'coquille__lien' + (actif ? ' coquille__lien--actif' : ''), d[1])
      li.appendChild(b)
      liste.appendChild(li)
    })
    // Un écran maquetté sans équivalent livré : il apparaît, mais en pointillés.
    // Sans ça la maquette ferait passer pour acquis un écran qui n'existe pas.
    if (!trouve && ecranActif) {
      var li2 = el('li')
      var b2 = el('button', 'coquille__lien coquille__lien--actif coquille__lien--absent',
        lire(p, 'ecran-libelle', ecranActif))
      b2.appendChild(el('span', 'marque-absente', 'non livrée'))
      li2.appendChild(b2)
      liste.appendChild(li2)
      p.setAttribute('data-invente', '')
    }
    nav.appendChild(liste)
    return nav
  }

  function libelleEcran(axe, id, p) {
    var liste = DESTINATIONS[axe] || []
    for (var i = 0; i < liste.length; i++) if (liste[i][0] === id) return liste[i][1]
    return lire(p, 'ecran-libelle', id || '—')
  }

  // — Assemblage par monde ——————————————————————————————————————————————————
  function construire(planche) {
    var ui = planche.querySelector('.ui')
    var ecran = planche.querySelector('.ecran')
    if (!ui || !ecran || planche.hasAttribute('data-sans-ossature')) return

    var monde = lire(planche, 'monde', 'admin')
    ui.setAttribute('data-monde', monde)

    var app = el('div', 'app')
    var contenu = el('div', 'app__contenu')

    if (monde === 'admin') {
      app.appendChild(enteteAppli(planche, 'Kervignarc', true))
      var axe = lire(planche, 'axe', null)
      if (axe && AXES[axe]) {
        var ecranId = lire(planche, 'ecran', null)
        var lib = libelleEcran(axe, ecranId, planche)
        var coquille = el('div', 'coquille')
        coquille.appendChild(navigationAdmin(planche, axe, ecranId))
        var zone = el('div', 'coquille__contenu')
        if (AXES[axe].besoinTournoi) zone.appendChild(bandeauContexte(planche, AXES[axe].libelle, lib))
        zone.appendChild(el('div', 'aide-ecran', '▸ ' + lire(planche, 'aide', "Aide de l'écran")))
        zone.appendChild(ecran)
        coquille.appendChild(zone)
        contenu.appendChild(coquille)
      } else {
        contenu.appendChild(ecran)   // accueil admin : pas de coquille, il n'y a pas d'axe ouvert
      }
    } else if (monde === 'salle') {
      var bande = el('div', 'salle__bandeau')
      bande.appendChild(el('span', 'titre', lire(planche, 'lieu', 'KERVIGNARC · SALLE')))
      bande.appendChild(el('span', 'second', lire(planche, 'vue', 'Classement en direct')))
      var fin = el('span', 'fin second')
      fin.textContent = lire(planche, 'cadence', 'Vue suivante dans 12 s')
      bande.appendChild(fin)
      app.appendChild(bande)
      contenu.className = 'salle__scene'
      contenu.appendChild(ecran)
    } else {
      // tablette (cible), scoreur, public — pas de sidebar.
      // Sur la cible, « Changer de rôle » disparaît dès le rattachement (verrou D-13).
      var role = lire(planche, 'changer-role', monde === 'public' ? 'oui' : 'non') === 'oui'
      app.appendChild(enteteAppli(planche, lire(planche, 'titre', 'Kervignarc'), role))
      contenu.appendChild(ecran)
    }

    app.appendChild(contenu)
    ui.appendChild(app)
  }

  // — Échelle ———————————————————————————————————————————————————————————————
  function jeton(planche, cadre) {
    var legende = planche.querySelector('figcaption')
    if (!legende) return null
    var j = el('span', 'jeton-appareil')
    var texte = el('span')
    j.appendChild(texte)
    var b = el('button', null, 'taille réelle')
    b.type = 'button'
    b.addEventListener('click', function () {
      var r = document.documentElement
      if (r.getAttribute('data-echelle') === 'reelle') r.removeAttribute('data-echelle')
      else r.setAttribute('data-echelle', 'reelle')
      tout()
    })
    j.appendChild(b)
    legende.appendChild(j)
    cadre._texteJeton = texte
    return texte
  }

  function ajuster(cadre) {
    var parent = cadre.parentNode
    var appareil = APPAREILS[cadre.getAttribute('data-appareil') || 'pc']
    var reelle = document.documentElement.getAttribute('data-echelle') === 'reelle'
    var k = 1
    if (!reelle) {
      var dispo = parent.clientWidth
      // Arrondi par le bas au centième : jamais de débordement d'un demi-pixel.
      k = Math.min(1, Math.floor((dispo / appareil.large) * 100) / 100)
      if (!isFinite(k) || k <= 0) k = 1
      cadre.style.setProperty('--k', String(k))
    } else {
      cadre.style.removeProperty('--k')
    }
    if (cadre._texteJeton) {
      cadre._texteJeton.textContent =
        appareil.libelle + ' · ' + appareil.large + ' × ' + appareil.haut +
        (reelle ? ' · taille réelle' : ' · affiché à ' + Math.round(k * 100) + ' %')
    }
    mesurerFlottaison(cadre)
  }

  // Ce qui dépasse de l'écran est une INFORMATION, pas un défaut d'affichage :
  // c'est la question « le bouton est-il visible sans défiler ? ».
  function mesurerFlottaison(cadre) {
    if (cadre.hasAttribute('data-deroule')) return
    var zone = cadre.querySelector('.coquille__contenu, .app__contenu, .salle__scene')
    var nav = cadre.querySelector('.coquille__nav')
    var debord = 0
    if (zone) debord = Math.max(debord, zone.scrollHeight - zone.clientHeight)
    if (nav) debord = Math.max(debord, nav.scrollHeight - nav.clientHeight)
    if (debord > 8) cadre.setAttribute('data-sous-la-ligne', '↓ ' + debord + ' px sous la ligne de flottaison')
    else cadre.removeAttribute('data-sous-la-ligne')
  }

  var cadres = []
  function tout() { cadres.forEach(ajuster) }

  function init() {
    var planches = document.querySelectorAll('.planche')
    Array.prototype.forEach.call(planches, construire)

    cadres = Array.prototype.slice.call(document.querySelectorAll('.cadre'))
    cadres.forEach(function (c) {
      var p = c.closest ? c.closest('.planche') : null
      if (p) jeton(p, c)
    })
    tout()

    if (window.ResizeObserver) {
      var ro = new ResizeObserver(function () { tout() })
      cadres.forEach(function (c) { if (c.parentNode) ro.observe(c.parentNode) })
    } else {
      window.addEventListener('resize', tout)
    }

    var avert = document.querySelector('.sans-js')
    if (avert && avert.parentNode) avert.parentNode.removeChild(avert)
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init)
  else init()
})()
