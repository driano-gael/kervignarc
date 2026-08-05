/* ═══════════════════════════════════════════════════════════════════════════
   Kervignarc — moteur de questionnaire (v2, maquettes plein écran)
   ---------------------------------------------------------------------------
   Quatre responsabilités :

   1. LA TRAME            — les sections du questionnaire sont des DONNÉES
      (`TRAME`, ci-dessous), pas du code. Elles servent à la fois à construire
      le formulaire et à produire le markdown : un libellé n'existe donc qu'à
      UN endroit. En v1, l'énoncé de chaque question était écrit deux fois par
      page — une fois en markup, une fois dans le JSON — et rien ne garantissait
      qu'ils disent la même chose.

   2. SAUVEGARDE LOCALE   — chaque frappe est conservée dans le navigateur. Le
      stockage peut être refusé (fichier ouvert en file://, navigateur
      verrouillé) : tout passe par un try/catch et l'échec est DIT, pas masqué.

   3. EXPORT MARKDOWN     — le fichier téléchargé est exactement celui qui doit
      atterrir dans questionnaires/. C'est lui le livrable versionné ; la page
      n'est qu'un moyen de le remplir confortablement.

   4. COPIE               — navigator.clipboard n'existe pas en contexte non
      sécurisé (file://), d'où le repli sur execCommand. Même piège que le jour
      J en http sur le réseau local.

   ---------------------------------------------------------------------------
   POURQUOI LA TRAME A CHANGÉ. Les questions de la v1 arbitraient entre deux
   vignettes de 430 px : « quel parti pris retiens-tu ? » ouvrait le
   questionnaire. Maintenant que l'écran est montré entier à la taille de son
   appareil, ce choix ne peut plus être la PREMIÈRE question — on jugerait
   encore le composant, pas l'écran. Il descend en §5, et quatre rubriques
   apparaissent, qui n'avaient aucun sens sur une vignette : le premier coup
   d'œil, la ligne de flottaison, l'ossature, l'occupation de l'espace.

   Les trois dernières viennent mot pour mot des réponses du 04/08/2026 —
   « je mettrai plus d'espace, on est sur un PC », « un bandeau en haut doit
   permettre de savoir sur quel tournoi on est », « trop tassé ». Elles étaient
   remontées spontanément dans les champs libres, faute de question pour les
   accueillir.

   La clé de stockage est bumpée en `-v2-` : sans ça, un `{variante:1}` de la v1
   re-cocherait silencieusement un bouton dans une section qui a bougé et dont
   les options ont changé — pire que de perdre la réponse. Les 36 jeux de
   réponses du 04/08 restent dans git ; le commanditaire a choisi de tout
   reposer à neuf.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict'

  var TRAME = [
    {
      titre: 'Le premier coup d’œil',
      aide: 'Regarde l’écran deux secondes, puis réponds sans y revenir. C’est la seule question ' +
            'qui se gâte si tu réfléchis : on cherche ce que l’écran donne AVANT qu’on le lise.',
      blocs: [
        { type: 'radio', nom: 'visible', intitule: 'Ce que tu venais chercher est-il là ?', options: [
          'Oui — visible tout de suite, sans chercher',
          'Oui — mais j’ai dû balayer l’écran pour le trouver',
          'Non — c’est à l’écran mais noyé',
          'Non — ce n’est pas à l’écran du tout',
        ] },
        { type: 'texte', champ: 'premier', intitule: 'Qu’as-tu vu en premier, et qu’aurais-tu voulu voir en premier ?' },
      ],
    },
    {
      titre: 'Ce qui passe sous la ligne de flottaison',
      aide: 'Le cadre a la hauteur réelle de l’appareil. Ce qui est en dessous du bord bas n’existe ' +
            'pas tant qu’on n’a pas fait défiler — et le jour J, on ne fait pas défiler.',
      blocs: [
        { type: 'radio', nom: 'flottaison', intitule: 'Ce qui tombe sous la ligne peut-il y rester ?', options: [
          'Oui — rien d’important ne passe dessous',
          'Non — il faut remonter quelque chose au-dessus',
          'L’écran tient entièrement, la question ne se pose pas',
        ] },
        { type: 'texte', champ: 'flottaison_txt', intitule: 'Qu’est-ce qui doit absolument rester visible sans défiler ?' },
      ],
    },
    {
      titre: 'L’ossature',
      aide: 'La navigation, le bandeau de contexte, l’aide d’écran, la bande d’en-tête. Tout ce qui ' +
            'entoure le contenu et qu’on ne voyait pas dans les vignettes.',
      blocs: [
        { type: 'radio', nom: 'nav', intitule: 'La navigation', options: [
          'Elle va', 'Elle est trop longue', 'Elle est mal rangée', 'Il n’en faudrait pas ici',
        ] },
        { type: 'radio', nom: 'bandeau', intitule: 'Le bandeau de contexte (tournoi, statut, départ)', options: [
          'Il va', 'Il lui manque quelque chose', 'Il dit trop de choses', 'Il n’y en a pas ici et il en faudrait un',
        ] },
        { type: 'texte', champ: 'ossature', intitule: 'Ce qui cloche dans le cadre autour du contenu' },
      ],
    },
    {
      titre: 'L’occupation de l’espace',
      aide: 'On est sur l’appareil réel, à sa vraie taille. La question n’est plus « est-ce que ça ' +
            'tient » mais « est-ce qu’on s’en sert bien ».',
      blocs: [
        { type: 'radio', nom: 'espace', intitule: 'La densité', options: [
          'Trop tassé — il faut aérer',
          'Juste',
          'Trop vide — on peut exploiter plus d’espace',
        ] },
        { type: 'texte', champ: 'espace_txt', intitule: 'Que mettrais-tu dans la place gagnée, ou qu’enlèverais-tu ?' },
      ],
    },
    {
      titre: 'Le parti pris',
      // Toutes les planches ne proposent pas d'alternative : certaines montrent un seul écran
      // dans plusieurs états. Sans alternative, la section entière n'a pas d'objet — « pourquoi
      // ce choix » sans choix est une question qui ne veut rien dire.
      siVariantes: true,
      aide: 'Maintenant seulement — après avoir jugé l’écran entier — le choix entre les mises en page ' +
            'proposées. Les mentions « recommandé » sont mon avis argumenté, pas une décision.',
      blocs: [
        { type: 'variantes' },
        { type: 'texte', champ: 'pourquoi', intitule: 'Pourquoi ce choix' },
        { type: 'texte', champ: 'ailleurs', intitule: 'Ce que tu prendrais dans les autres partis pris' },
      ],
    },
    {
      titre: 'Verdict',
      blocs: [
        { type: 'radio', nom: 'verdict', options: [
          '✅ Validé tel quel — on peut coder ça',
          '🟡 Validé avec les réserves ci-dessous',
          '🔴 À refaire — l’écran ne répond pas au besoin',
        ] },
      ],
    },
    { titre: 'Critiques', blocs: [{ type: 'texte', champ: 'critiques' }] },
    { titre: 'Évolutions souhaitées', blocs: [{ type: 'texte', champ: 'evolutions' }] },
    { titre: 'Questions ciblées', blocs: [{ type: 'questions' }] },
    {
      titre: 'Vocabulaire',
      aide: 'Un mot faux à l’écran coûte plus cher qu’une mise en page perfectible : il se propage ' +
            'dans le code, l’API et la doc.',
      blocs: [{ type: 'vocab' }],
    },
    { titre: 'Ce qui manque complètement', blocs: [{ type: 'texte', champ: 'manque' }] },
  ]

  var LIGNES_VOCAB = 3

  var modele = JSON.parse(document.getElementById('q-modele').textContent)
  var cle = 'kervignarc-questionnaire-v2-' + modele.slug
  var form = document.getElementById('q-form')
  var etat = document.getElementById('q-etat')
  var apercu = document.getElementById('q-apercu')
  var stockageOk = true

  /* ------------------------------------------------ construction du formulaire */

  function el(balise, classe, texte) {
    var n = document.createElement(balise)
    if (classe) n.className = classe
    if (texte !== undefined && texte !== null) n.textContent = texte
    return n
  }

  function champTexte(nom, intitule) {
    var lab = el('label', 'q-champ')
    if (intitule) lab.appendChild(el('span', null, intitule))
    var t = document.createElement('textarea')
    t.setAttribute('data-champ', nom)
    lab.appendChild(t)
    return lab
  }

  function groupeRadio(nom, intitule, options) {
    var enveloppe = document.createDocumentFragment()
    if (intitule) {
      var titre = el('p', 'q-aide', intitule)
      titre.style.fontWeight = '700'
      titre.style.marginBottom = '7px'
      enveloppe.appendChild(titre)
    }
    var g = el('div', 'q-choix')
    options.forEach(function (texte, i) {
      var lab = el('label')
      var input = document.createElement('input')
      input.type = 'radio'
      input.name = nom
      input.value = String(i)
      lab.appendChild(input)
      lab.appendChild(el('span', null, texte))
      g.appendChild(lab)
    })
    enveloppe.appendChild(g)
    return enveloppe
  }

  // Le sort des variantes dépend de l'écran : certaines planches n'en ont qu'une.
  function optionsVariantes() {
    var v = modele.variantes || []
    if (v.length < 2) return null
    return v.concat(['Aucun — voir « à refaire » plus bas'])
  }

  function construireFormulaire() {
    TRAME.forEach(function (section, iSection) {
      if (section.siVariantes && !optionsVariantes()) return
      var s = el('section', 'q-bloc')
      var h = el('h2')
      h.appendChild(el('span', 'q-num', String(iSection + 1) + '.'))
      h.appendChild(document.createTextNode(section.titre))
      s.appendChild(h)
      if (section.aide) s.appendChild(el('p', 'q-aide', section.aide))

      section.blocs.forEach(function (bloc) {
        if (bloc.type === 'texte') {
          s.appendChild(champTexte(bloc.champ, bloc.intitule))
        } else if (bloc.type === 'radio') {
          s.appendChild(groupeRadio(bloc.nom, bloc.intitule, bloc.options))
        } else if (bloc.type === 'variantes') {
          var opts = optionsVariantes()
          // La dernière option (« Aucun ») vaut -1 : c'est la valeur qu'attend le markdown.
          if (opts) {
            var g = groupeRadio('variante', null, opts)
            s.appendChild(g)
            var boutons = s.querySelectorAll('input[name="variante"]')
            boutons[boutons.length - 1].value = '-1'
          }
        } else if (bloc.type === 'questions') {
          ;(modele.questions || []).forEach(function (q, i) {
            var d = el('div', 'q-ciblee')
            var p = el('p')
            p.appendChild(el('span', 'q-idx', String(i + 1) + '.'))
            p.appendChild(document.createTextNode(q))
            d.appendChild(p)
            var t = document.createElement('textarea')
            t.setAttribute('data-question', String(i))
            d.appendChild(t)
            s.appendChild(d)
          })
        } else if (bloc.type === 'vocab') {
          var grille = el('div', 'q-vocab')
          grille.appendChild(el('span', 'q-vocab-tete', 'À l’écran'))
          grille.appendChild(el('span', 'q-vocab-tete', 'Le bon mot'))
          for (var i = 0; i < LIGNES_VOCAB; i++) {
            var ligne = el('div', 'q-vocab-ligne')
            ligne.style.display = 'contents'
            var a = document.createElement('input')
            a.type = 'text'; a.setAttribute('data-vocab', 'ecran')
            var b = document.createElement('input')
            b.type = 'text'; b.setAttribute('data-vocab', 'bon')
            ligne.appendChild(a); ligne.appendChild(b)
            grille.appendChild(ligne)
          }
          s.appendChild(grille)
        }
      })
      form.appendChild(s)
    })
  }

  /* ---------------------------------------------------------------- état */

  // Générique : tout groupe de radios est lu par son `name`. Déplacer une section
  // ou en ajouter une ne demande plus de toucher à la lecture ni à l'écriture.
  function lireReponses() {
    var r = { radios: {}, champs: {}, questions: [], vocab: [] }
    var vus = {}
    form.querySelectorAll('input[type="radio"]').forEach(function (i) {
      if (vus[i.name]) return
      vus[i.name] = true
      var choisi = form.querySelector('input[name="' + i.name + '"]:checked')
      r.radios[i.name] = choisi ? parseInt(choisi.value, 10) : null
    })
    form.querySelectorAll('textarea[data-champ]').forEach(function (t) {
      r.champs[t.dataset.champ] = t.value
    })
    form.querySelectorAll('textarea[data-question]').forEach(function (t) {
      r.questions[parseInt(t.dataset.question, 10)] = t.value
    })
    form.querySelectorAll('.q-vocab-ligne').forEach(function (ligne, i) {
      var a = ligne.querySelector('[data-vocab="ecran"]')
      var b = ligne.querySelector('[data-vocab="bon"]')
      r.vocab[i] = { ecran: a ? a.value : '', bon: b ? b.value : '' }
    })
    return r
  }

  function ecrireReponses(r) {
    if (!r) return
    Object.keys(r.radios || {}).forEach(function (nom) {
      var v = r.radios[nom]
      if (v === null || v === undefined) return
      var b = form.querySelector('input[name="' + nom + '"][value="' + v + '"]')
      if (b) b.checked = true
    })
    Object.keys(r.champs || {}).forEach(function (nom) {
      var t = form.querySelector('textarea[data-champ="' + nom + '"]')
      if (t) t.value = r.champs[nom]
    })
    ;(r.questions || []).forEach(function (val, i) {
      var t = form.querySelector('textarea[data-question="' + i + '"]')
      if (t && val) t.value = val
    })
    ;(r.vocab || []).forEach(function (paire, i) {
      var ligne = form.querySelectorAll('.q-vocab-ligne')[i]
      if (!ligne || !paire) return
      var a = ligne.querySelector('[data-vocab="ecran"]')
      var b = ligne.querySelector('[data-vocab="bon"]')
      if (a) a.value = paire.ecran || ''
      if (b) b.value = paire.bon || ''
    })
  }

  /* ------------------------------------------------------------ stockage */

  function charger() {
    try {
      var brut = window.localStorage.getItem(cle)
      if (brut) {
        ecrireReponses(JSON.parse(brut))
        dire('réponses restaurées', true)
        return
      }
    } catch (e) {
      stockageOk = false
      dire('sauvegarde auto indisponible — pensez à télécharger', false)
      return
    }
    dire('rien de saisi', false)
  }

  var minuteur = null
  function sauver() {
    if (!stockageOk) return
    window.clearTimeout(minuteur)
    minuteur = window.setTimeout(function () {
      try {
        window.localStorage.setItem(cle, JSON.stringify(lireReponses()))
        dire('enregistré dans ce navigateur', true)
      } catch (e) {
        stockageOk = false
        dire('sauvegarde auto indisponible — pensez à télécharger', false)
      }
    }, 400)
  }

  function dire(texte, vert) {
    etat.textContent = texte
    etat.className = 'q-etat' + (vert ? ' ok' : '')
  }

  /* ------------------------------------------------------------ markdown */

  function citer(texte) {
    if (!texte || !texte.trim()) return '> _(sans réponse)_'
    return texte.trim().split('\n').map(function (l) { return '> ' + l }).join('\n')
  }

  function cases(options, choisi, valeurs) {
    return options.map(function (o, i) {
      var v = valeurs ? valeurs[i] : i
      return '- [' + (choisi === v ? 'x' : ' ') + '] ' + o
    })
  }

  function construireMarkdown() {
    var r = lireReponses()
    var l = []

    l.push('# ' + modele.code + ' · ' + modele.titre, '')
    l.push('> **Écran** : [' + modele.code + ' — ' + modele.titre + '](../' + modele.slug + '.html)' +
           ' · **Appli** : ' + modele.appli + ' (`' + modele.route + '`)')
    if (modele.appareil) l.push('> **Appareil** : ' + modele.appareil)
    l.push('> **Rôle** : ' + modele.role)
    l.push('>')
    l.push('> Rempli le ' + new Date().toLocaleDateString('fr-FR') + '.')
    l.push('', '---', '')

    var num = 0
    TRAME.forEach(function (section) {
      if (section.siVariantes && !optionsVariantes()) return
      num += 1
      l.push('## ' + num + '. ' + section.titre, '')

      section.blocs.forEach(function (bloc) {
        if (bloc.type === 'texte') {
          if (bloc.intitule) l.push('**' + bloc.intitule + '**', '')
          l.push(citer(r.champs[bloc.champ]), '')
        } else if (bloc.type === 'radio') {
          if (bloc.intitule) l.push('**' + bloc.intitule + '**', '')
          l.push.apply(l, cases(bloc.options, r.radios[bloc.nom]))
          l.push('')
        } else if (bloc.type === 'variantes') {
          var opts = optionsVariantes()
          if (!opts) return
          var valeurs = opts.map(function (_, i) { return i === opts.length - 1 ? -1 : i })
          l.push.apply(l, cases(opts, r.radios.variante, valeurs))
          l.push('')
        } else if (bloc.type === 'questions') {
          ;(modele.questions || []).forEach(function (q, i) {
            l.push('**' + (i + 1) + '. ' + q + '**', '')
            l.push(citer(r.questions[i]), '')
          })
        } else if (bloc.type === 'vocab') {
          var lignes = (r.vocab || []).filter(function (p) {
            return p && (p.ecran.trim() || p.bon.trim())
          })
          l.push('| À l’écran | Le bon mot |')
          l.push('|---|---|')
          if (lignes.length === 0) l.push('|  |  |')
          else lignes.forEach(function (p) { l.push('| ' + p.ecran.trim() + ' | ' + p.bon.trim() + ' |') })
          l.push('')
        }
      })
      l.push('---', '')
    })

    // Le dernier séparateur est de trop : le fichier se termine sur la réponse.
    if (l[l.length - 2] === '---') l.splice(l.length - 2, 2)
    return l.join('\n')
  }

  /* -------------------------------------------------------------- actions */

  function telecharger() {
    var texte = construireMarkdown()
    var blob = new Blob([texte], { type: 'text/markdown;charset=utf-8' })
    var url = URL.createObjectURL(blob)
    var a = document.createElement('a')
    a.href = url
    a.download = modele.slug + '.md'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.setTimeout(function () { URL.revokeObjectURL(url) }, 1000)
    dire('téléchargé — à déposer dans questionnaires/', true)
  }

  function copier() {
    var texte = construireMarkdown()
    // navigator.clipboard exige un contexte sécurisé : absent en file://.
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(texte).then(
        function () { dire('markdown copié', true) },
        function () { copierRepli(texte) }
      )
      return
    }
    copierRepli(texte)
  }

  function copierRepli(texte) {
    var zone = document.createElement('textarea')
    zone.value = texte
    zone.setAttribute('readonly', '')
    zone.style.position = 'fixed'
    zone.style.opacity = '0'
    document.body.appendChild(zone)
    zone.select()
    var ok = false
    try { ok = document.execCommand('copy') } catch (e) { ok = false }
    document.body.removeChild(zone)
    dire(ok ? 'markdown copié' : 'copie refusée — utilisez « Télécharger »', ok)
  }

  function basculerApercu() {
    var visible = apercu.classList.toggle('visible')
    if (visible) apercu.querySelector('pre').textContent = construireMarkdown()
  }

  function reinitialiser() {
    if (!window.confirm('Effacer toutes les réponses de cet écran ?')) return
    form.reset()
    try { window.localStorage.removeItem(cle) } catch (e) { /* stockage déjà indisponible */ }
    dire('réponses effacées', false)
  }

  /* ---------------------------------------------------------------- câblage */

  construireFormulaire()

  form.addEventListener('input', function () {
    sauver()
    if (apercu.classList.contains('visible')) apercu.querySelector('pre').textContent = construireMarkdown()
  })
  form.addEventListener('change', sauver)
  document.getElementById('q-telecharger').addEventListener('click', telecharger)
  document.getElementById('q-copier').addEventListener('click', copier)
  document.getElementById('q-apercu-bouton').addEventListener('click', basculerApercu)
  document.getElementById('q-reinit').addEventListener('click', reinitialiser)

  charger()
})()
