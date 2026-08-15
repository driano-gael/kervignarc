/* Atlas — rendu des pages.
 *
 * Un seul fichier pour toutes les vues : chaque page HTML ne charge que les données dont elle a
 * besoin et appelle `Pages.<nom>()`. Les schémas sont du SVG construit ici, à partir de
 * géométries triviales (colonnes fixes, rangs par date) — aucun moteur de mise en page, donc
 * aucune dépendance, et des liaisons en segments droits comme demandé.
 */

/* global window, document, Atlas */
var Pages = (function () {
  "use strict";

  var E = Atlas.echapper;

  /* --- Petits communs ----------------------------------------------------------------------- */

  /* Sans moteur de fonte, la largeur d'un libellé n'est pas mesurable : on l'estime en chasse
   * fixe (~6 px par caractère à 10 px) et on coupe. C'est ce qui empêche « Complété et
   * partiellement révisé par » de déborder de sa boîte de 150 px. */
  function couper(texte, caracteres) {
    var brut = String(texte || "");
    return brut.length <= caracteres ? brut : brut.slice(0, caracteres - 1) + "…";
  }

  function titrePage(cible, titre, chapo) {
    cible.appendChild(Atlas.element("h1", null, E(titre)));
    if (chapo) cible.appendChild(Atlas.element("p", "chapo", chapo));
  }

  function amendementsDeLaRegle(regle) {
    var git = (Atlas.donnees("historique") || {})[regle.identifiant] || [];
    return regle.amendements
      .concat(git)
      .slice()
      .sort(function (a, b) {
        return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
      });
  }

  function references(entree) {
    var morceaux = [];
    (entree.us || []).forEach(function (us) {
      morceaux.push("<span class='pastille'>" + E(us) + "</span>");
    });
    (entree.adr || []).forEach(function (numero) {
      morceaux.push("<a class='pastille' href='adr.html?id=" + E(numero) + "'>ADR-" + E(numero) + "</a>");
    });
    return morceaux.join(" ");
  }

  /* --- 1. Le règlement en vigueur ----------------------------------------------------------- */

  function reglement(cible) {
    var donnees = Atlas.donnees("reglement");
    if (!donnees) throw new Error("Les données du règlement sont absentes.");

    titrePage(
      cible,
      "Le règlement du projet",
      "Ce qui fait règle <strong>aujourd'hui</strong>, dans l'ordre où c'est écrit. " +
        "Chaque règle mène à son histoire : quand elle est née, ce qui l'a fait changer, et pourquoi."
    );

    donnees.sections.forEach(function (section) {
      var regles = donnees.regles.filter(function (regle) {
        return regle.section === section;
      });
      if (!regles.length) return;

      cible.appendChild(Atlas.element("h2", null, E(section)));
      regles.forEach(function (regle) {
        cible.appendChild(carteRegle(regle));
      });
    });
  }

  function carteRegle(regle) {
    var bloc = Atlas.element("article", "regle");
    var changements = amendementsDeLaRegle(regle).length;
    var lien = "regle.html?id=" + encodeURIComponent(regle.identifiant);

    bloc.innerHTML =
      "<div class='regle-tete'>" +
      "<span class='rang'>" +
      regle.rang +
      "</span>" +
      "<h3><a href='" +
      lien +
      "'>" +
      E(regle.titre) +
      "</a></h3>" +
      (changements
        ? "<a class='pastille change' href='" +
          lien +
          "'>↻ " +
          Atlas.pluriel(changements, "changement") +
          "</a>"
        : "<a class='pastille' href='" + lien + "'>historique</a>") +
      "</div>" +
      "<div class='corps'>" +
      Atlas.markdown(regle.corps) +
      "</div>";
    return bloc;
  }

  /* --- 2. La fiche d'une règle -------------------------------------------------------------- */

  function ficheRegle(cible) {
    var donnees = Atlas.donnees("reglement");
    var identifiant = Atlas.parametre("id");
    var regle = (donnees ? donnees.regles : []).filter(function (candidate) {
      return candidate.identifiant === identifiant;
    })[0];

    if (!regle) {
      titrePage(cible, "Règle introuvable", "Aucune règle ne porte l'ancre « " + E(identifiant) + " ».");
      cible.appendChild(Atlas.element("p", null, "<a href='index.html'>Retour au règlement</a>"));
      return;
    }

    titrePage(cible, regle.titre, E(regle.section) + " · règle " + regle.rang);

    cible.appendChild(Atlas.element("h2", null, "Ce qu'elle dit aujourd'hui"));
    cible.appendChild(Atlas.element("div", "corps", Atlas.markdown(regle.corps)));

    var changements = amendementsDeLaRegle(regle);
    cible.appendChild(
      Atlas.element("h2", null, "Son histoire — " + Atlas.pluriel(changements.length, "entrée"))
    );
    if (!changements.length) {
      cible.appendChild(
        Atlas.element("p", "discret", "Aucun changement retrouvé depuis l'écriture de la règle.")
      );
    } else {
      cible.appendChild(friseAmendements(changements));
    }

    if (regle.adr.length) {
      cible.appendChild(Atlas.element("h2", null, "Décisions liées"));
      cible.appendChild(
        Atlas.element(
          "p",
          null,
          regle.adr
            .map(function (numero) {
              return "<a class='pastille' href='adr.html?id=" + E(numero) + "'>ADR-" + E(numero) + "</a>";
            })
            .join(" ")
        )
      );
    }

    cible.appendChild(
      Atlas.element(
        "p",
        "discret",
        "Source : <code>" + E(regle.fichier) + "</code>, lignes " + regle.ligne + "–" + regle.ligne_fin +
          ". L'atlas ne fait que la lire — c'est le fichier qui fait foi."
      )
    );
  }

  function friseAmendements(entrees) {
    var liste = Atlas.element("ul", "frise");
    entrees.forEach(function (entree) {
      var element = Atlas.element("li", entree.origine === "incise" ? "change" : null);
      var origine =
        entree.origine === "incise"
          ? "note écrite dans la règle"
          : "commit " + E(entree.reference || "").slice(0, 7);
      element.innerHTML =
        "<div class='quand'>" +
        Atlas.jour(entree.date) +
        " · " +
        E(entree.nature) +
        " · " +
        origine +
        "</div>" +
        "<div>" +
        Atlas.enligne(entree.motif) +
        "</div>" +
        (references(entree) ? "<div>" + references(entree) + "</div>" : "");
      liste.appendChild(element);
    });
    return liste;
  }

  /* --- 3. Les décisions --------------------------------------------------------------------- */

  function decisions(cible) {
    var toutes = (Atlas.donnees("decisions") || {}).decisions || [];
    if (!toutes.length) throw new Error("Les données des décisions sont absentes.");

    var amendees = toutes.filter(function (decision) {
      return decision.amende_par.length;
    });

    titrePage(
      cible,
      Atlas.pluriel(toutes.length, "décision") + " d'architecture",
      "Le statut ne dit presque rien : <strong>" +
        toutes.filter(function (d) {
          return d.statut === "accepte";
        }).length +
        " sur " +
        toutes.length +
        "</strong> sont « Accepté ». Ce qui répond vraiment à « est-ce encore valable ? », " +
        "c'est de savoir <strong>ce qui les a amendées depuis</strong> — et cela n'est écrit sur " +
        "aucune des deux fiches concernées. L'atlas le calcule : <strong>" +
        amendees.length +
        "</strong> décisions sont partiellement dépassées."
    );

    cible.appendChild(filtresDecisions(toutes));
    cible.appendChild(Atlas.element("div", null, "")).id = "resultats";
    appliquerFiltres(toutes);

    cible.appendChild(Atlas.element("h2", null, "Chaînes d'amendement"));
    cible.appendChild(
      Atlas.element(
        "p",
        "chapo",
        "Une chaîne, c'est l'histoire d'une même question tranchée plusieurs fois. " +
          "Lecture de gauche à droite, dans l'ordre des dates."
      )
    );
    chaines(toutes).forEach(function (chaine) {
      cible.appendChild(schemaChaine(chaine));
    });
  }

  function filtresDecisions(toutes) {
    var zone = Atlas.element("div", "filtres");
    var annees = {};
    toutes.forEach(function (decision) {
      annees[decision.date.slice(0, 4)] = true;
    });

    zone.innerHTML =
      "<input type='search' id='f-texte' placeholder='Filtrer par titre ou numéro…' " +
      "aria-label='Filtrer les décisions'>" +
      "<select id='f-etat' aria-label='État'>" +
      "<option value=''>Tous les états</option>" +
      "<option value='amendee'>Partiellement dépassées</option>" +
      "<option value='intacte'>Jamais amendées</option>" +
      "<option value='remplace'>Remplacées</option>" +
      "</select>" +
      "<select id='f-annee' aria-label='Année'><option value=''>Toutes les années</option>" +
      Object.keys(annees)
        .sort()
        .map(function (annee) {
          return "<option value='" + annee + "'>" + annee + "</option>";
        })
        .join("") +
      "</select>";

    zone.addEventListener("input", function () {
      appliquerFiltres(toutes);
    });
    return zone;
  }

  function appliquerFiltres(toutes) {
    var zone = document.getElementById("resultats");
    if (!zone) return;
    var texte = (document.getElementById("f-texte") || {}).value || "";
    var etat = (document.getElementById("f-etat") || {}).value || "";
    var annee = (document.getElementById("f-annee") || {}).value || "";
    var recherche = texte.toLowerCase();

    var visibles = toutes.filter(function (decision) {
      if (annee && decision.date.slice(0, 4) !== annee) return false;
      if (etat === "amendee" && !decision.amende_par.length) return false;
      if (etat === "intacte" && decision.amende_par.length) return false;
      if (etat === "remplace" && decision.statut !== "remplace") return false;
      if (
        recherche &&
        (decision.titre + " ADR-" + decision.identifiant).toLowerCase().indexOf(recherche) < 0
      )
        return false;
      return true;
    });

    zone.innerHTML =
      "<p class='discret'>" +
      Atlas.pluriel(visibles.length, "décision") +
      " affichée" +
      (visibles.length > 1 ? "s" : "") +
      "</p><ul class='liste-nue'>" +
      visibles
        .slice()
        .sort(function (a, b) {
          return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
        })
        .map(ligneDecision)
        .join("") +
      "</ul>";
  }

  function ligneDecision(decision) {
    var etats = [];
    if (decision.statut === "remplace") {
      etats.push("<span class='pastille alerte'>remplacée</span>");
    }
    if (decision.amende_par.length) {
      etats.push(
        "<span class='pastille change'>amendée par " +
          decision.amende_par
            .map(function (numero) {
              return "ADR-" + E(numero);
            })
            .join(", ") +
          "</span>"
      );
    }
    if (!etats.length) etats.push("<span class='pastille tenu'>intacte</span>");

    return (
      "<li><a href='adr.html?id=" +
      E(decision.identifiant) +
      "'>ADR-" +
      E(decision.identifiant) +
      " — " +
      E(decision.titre) +
      "</a> " +
      etats.join(" ") +
      "<div class='discret'>" +
      Atlas.jour(decision.date) +
      "</div></li>"
    );
  }

  /* Composantes connexes sur les seules arêtes d'amendement et de remplacement : `voisin` et
   * `socle` relient presque tout à presque tout et noieraient le signal. */
  function chaines(toutes) {
    var index = {};
    var voisins = {};
    toutes.forEach(function (decision) {
      index[decision.identifiant] = decision;
      voisins[decision.identifiant] = voisins[decision.identifiant] || {};
      decision.amende_par.forEach(function (source) {
        voisins[decision.identifiant][source] = true;
        voisins[source] = voisins[source] || {};
        voisins[source][decision.identifiant] = true;
      });
    });

    var vus = {};
    var groupes = [];
    Object.keys(voisins)
      .sort()
      .forEach(function (depart) {
        if (vus[depart] || !Object.keys(voisins[depart]).length) return;
        var pile = [depart];
        var groupe = [];
        while (pile.length) {
          var courant = pile.pop();
          if (vus[courant]) continue;
          vus[courant] = true;
          groupe.push(courant);
          Object.keys(voisins[courant] || {}).forEach(function (suivant) {
            if (!vus[suivant]) pile.push(suivant);
          });
        }
        if (groupe.length > 1) {
          groupes.push(
            groupe
              .filter(function (numero) {
                return index[numero];
              })
              .sort(function (a, b) {
                return index[a].date < index[b].date ? -1 : 1;
              })
          );
        }
      });
    return groupes;
  }

  /* Un maillon = une boîte ; les liaisons sont des segments strictement horizontaux. */
  function schemaChaine(chaine) {
    var index = {};
    ((Atlas.donnees("decisions") || {}).decisions || []).forEach(function (decision) {
      index[decision.identifiant] = decision;
    });

    var LARGEUR = 148;
    var HAUTEUR = 46;
    var ECART = 46;
    var total = chaine.length * LARGEUR + (chaine.length - 1) * ECART;
    var svg =
      "<svg class='reseau' viewBox='0 0 " +
      (total + 4) +
      " 76' role='img' aria-label='Chaîne d’amendement'>";

    chaine.forEach(function (numero, rang) {
      var x = 2 + rang * (LARGEUR + ECART);
      if (rang > 0) {
        var depart = x - ECART;
        svg +=
          "<path class='arete' d='M " + depart + " " + (HAUTEUR / 2 + 8) +
          " H " + x + "'></path>" +
          "<text class='etiquette' x='" + (depart + 4) + "' y='" + (HAUTEUR / 2 + 2) + "'>amende</text>";
      }
      svg +=
        "<rect class='boite' x='" + x + "' y='8' width='" + LARGEUR + "' height='" + HAUTEUR +
        "' rx='4'></rect>" +
        "<a href='adr.html?id=" + E(numero) + "'>" +
        "<text x='" + (x + 10) + "' y='27'>ADR-" + E(numero) + "</text>" +
        "<text class='etiquette' x='" + (x + 10) + "' y='44'>" +
        E(Atlas.jour((index[numero] || {}).date || "")) + "</text></a>";
    });

    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML = svg + "</svg>";
    return enveloppe;
  }

  /* --- 4. La fiche d'une décision ------------------------------------------------------------ */

  function ficheDecision(cible) {
    var toutes = (Atlas.donnees("decisions") || {}).decisions || [];
    var identifiant = Atlas.parametre("id");
    var decision = toutes.filter(function (candidate) {
      return candidate.identifiant === identifiant;
    })[0];

    if (!decision) {
      titrePage(cible, "Décision introuvable", "Aucun ADR ne porte le numéro « " + E(identifiant) + " ».");
      cible.appendChild(Atlas.element("p", null, "<a href='decisions.html'>Retour aux décisions</a>"));
      return;
    }

    titrePage(
      cible,
      "ADR-" + decision.identifiant + " — " + decision.titre,
      "Décidé le " + Atlas.jour(decision.date) + " · statut déclaré : " + E(decision.statut_brut)
    );

    if (decision.amende_par.length) {
      cible.appendChild(
        Atlas.element(
          "p",
          null,
          "<span class='pastille change'>partiellement dépassée</span> " +
            "Cette décision reste marquée « Accepté », mais " +
            decision.amende_par
              .map(function (numero) {
                return "<a href='adr.html?id=" + E(numero) + "'>ADR-" + E(numero) + "</a>";
              })
              .join(", ") +
            " l'a amendée depuis. Rien ne le dit sur sa propre page."
        )
      );
    }

    if (decision.extrait) {
      cible.appendChild(Atlas.element("h2", null, "Ce qu'elle décide"));
      cible.appendChild(Atlas.element("div", "corps", "<p>" + Atlas.enligne(decision.extrait) + "</p>"));
    }

    cible.appendChild(Atlas.element("h2", null, "Son voisinage"));
    cible.appendChild(schemaEgo(decision, toutes));

    cible.appendChild(Atlas.element("h2", null, "Ce qui la porte dans le code"));
    cible.appendChild(tableauPortage(decision));

    if (decision.us.length) {
      cible.appendChild(Atlas.element("h2", null, "US concernées"));
      cible.appendChild(
        Atlas.element(
          "p",
          null,
          decision.us
            .map(function (us) {
              return "<span class='pastille'>" + E(us) + "</span>";
            })
            .join(" ")
        )
      );
    }

    cible.appendChild(
      Atlas.element("p", "discret", "Source : <code>" + E(decision.fichier) + "</code>")
    );
  }

  /* Trois colonnes fixes — ce qui la fonde à gauche, elle au centre, ce qui l'amende à droite.
   * Aucun algorithme : la géométrie est connue d'avance, les liaisons sont des coudes à angle
   * droit. C'est aussi ce qui garantit qu'aucune arête ne traverse une boîte. */
  function schemaEgo(decision, toutes) {
    var index = {};
    toutes.forEach(function (autre) {
      index[autre.identifiant] = autre;
    });

    var amont = {};
    decision.liens.forEach(function (lien) {
      if (lien.type !== "us" && index[lien.cible]) amont[lien.cible] = lien.libelle;
    });
    var aval = {};
    decision.amende_par.forEach(function (numero) {
      if (index[numero]) aval[numero] = "amende";
    });

    var gauche = Object.keys(amont).sort();
    var droite = Object.keys(aval).sort();
    if (!gauche.length && !droite.length) {
      return Atlas.element(
        "p",
        "discret",
        "Cette décision ne déclare aucune relation et aucune autre ne l'amende."
      );
    }

    /* Géométrie posée à la main, en trois colonnes qui ne se recouvrent pas :
     *   gauche  [  0 .. 150]      pivot [210 .. 360]      droite [420 .. 570]
     * Les gouttières de 60 px entre colonnes servent de couloirs de routage : une arête y fait
     * son coude vertical, donc elle ne traverse jamais une boîte. */
    var LARGEUR = 150;
    var HAUTEUR = 34;
    var GOUTTIERE = 14;
    var X_GAUCHE = 0;
    var X_PIVOT = 210;
    var X_DROITE = 420;
    var rangees = Math.max(gauche.length, droite.length, 1);
    var hauteurTotale = rangees * (HAUTEUR + GOUTTIERE) + GOUTTIERE;
    var milieu = hauteurTotale / 2;

    function colonne(numeros, x, etiquettes, versLaDroite) {
      var bordBoite = versLaDroite ? x + LARGEUR : x;
      var bordPivot = versLaDroite ? X_PIVOT : X_PIVOT + LARGEUR;
      var coude = (bordBoite + bordPivot) / 2;
      var html = "";
      numeros.forEach(function (numero, rang) {
        var y = GOUTTIERE + rang * (HAUTEUR + GOUTTIERE);
        var centreY = y + HAUTEUR / 2;
        html +=
          "<path class='arete' d='M " + bordBoite + " " + centreY +
          " H " + coude + " V " + milieu + " H " + bordPivot + "'></path>" +
          "<rect class='boite' x='" + x + "' y='" + y + "' width='" + LARGEUR +
          "' height='" + HAUTEUR + "' rx='4'></rect>" +
          "<a href='adr.html?id=" + E(numero) + "'>" +
          "<text x='" + (x + 9) + "' y='" + (y + 15) + "'>ADR-" + E(numero) + "</text>" +
          "<text class='etiquette' x='" + (x + 9) + "' y='" + (y + 28) + "'>" +
          E(couper(etiquettes[numero], 22)) + "</text>" +
          "<title>" + E(etiquettes[numero]) + "</title></a>";
      });
      return html;
    }

    var svg =
      "<svg class='reseau' viewBox='0 0 " + (X_DROITE + LARGEUR + 4) + " " + hauteurTotale +
      "' role='img' aria-label='Voisinage de la décision'>" +
      colonne(gauche, X_GAUCHE, amont, true) +
      colonne(droite, X_DROITE, aval, false) +
      "<rect class='boite pivot' x='" + X_PIVOT + "' y='" + (milieu - HAUTEUR / 2) +
      "' width='" + LARGEUR + "' height='" + HAUTEUR + "' rx='4'></rect>" +
      "<text x='" + (X_PIVOT + 9) + "' y='" + (milieu + 5) + "'>ADR-" + E(decision.identifiant) +
      "</text></svg>";

    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML = svg;
    return enveloppe;
  }

  function tableauPortage(decision) {
    if (!decision.portage.length) {
      return Atlas.element(
        "p",
        "discret",
        "Cette décision ne nomme aucun module. Un ADR sans lien vérifiable vers le code est une " +
          "intention, pas une décision — mais la règle n'a pas été appliquée rétroactivement à " +
          "tout le registre, donc ce n'est pas nécessairement un défaut ici."
      );
    }

    var lignes = decision.portage
      .map(function (portage) {
        var etat = !portage.existe
          ? "<span class='pastille alerte'>chemin disparu</span>"
          : portage.symboles_absents.length
            ? "<span class='pastille change'>introuvable : " +
              portage.symboles_absents.map(E).join(", ") +
              "</span>"
            : "<span class='pastille tenu'>tenu</span>";
        return (
          "<tr><td><code>" +
          E(portage.chemin) +
          "</code></td><td>" +
          (portage.symboles.length ? portage.symboles.map(E).join(", ") : "—") +
          "</td><td>" +
          etat +
          "</td></tr>"
        );
      })
      .join("");

    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML =
      "<table><thead><tr><th>Module</th><th>Symboles annoncés</th><th>État</th></tr></thead>" +
      "<tbody>" + lignes + "</tbody></table>";
    return enveloppe;
  }

  /* --- 5. Errata ----------------------------------------------------------------------------- */

  function errata(cible) {
    var reglementDonnees = Atlas.donnees("reglement") || { regles: [] };
    var decisionsDonnees = (Atlas.donnees("decisions") || {}).decisions || [];

    var entrees = [];
    reglementDonnees.regles.forEach(function (regle) {
      amendementsDeLaRegle(regle).forEach(function (amendement) {
        entrees.push({
          date: amendement.date,
          quoi: "règle « " + regle.titre + " »",
          lien: "regle.html?id=" + encodeURIComponent(regle.identifiant),
          detail: amendement.motif,
          nature: amendement.nature,
        });
      });
    });
    decisionsDonnees.forEach(function (decision) {
      entrees.push({
        date: decision.date,
        quoi: "ADR-" + decision.identifiant + " — " + decision.titre,
        lien: "adr.html?id=" + decision.identifiant,
        detail: "Décision prise.",
        nature: "décision",
      });
    });
    entrees.sort(function (a, b) {
      return a.date < b.date ? 1 : a.date > b.date ? -1 : 0;
    });

    titrePage(
      cible,
      "Ce qui a changé",
      "Tout ce qui a bougé dans le règlement et dans les décisions, du plus récent au plus ancien — " +
        Atlas.pluriel(entrees.length, "entrée") + "."
    );

    var liste = Atlas.element("ul", "frise");
    entrees.forEach(function (entree) {
      var element = Atlas.element("li", entree.nature === "décision" ? null : "change");
      element.innerHTML =
        "<div class='quand'>" + Atlas.jour(entree.date) + " · " + E(entree.nature) + "</div>" +
        "<div><a href='" + entree.lien + "'>" + E(entree.quoi) + "</a></div>" +
        "<div class='discret'>" + Atlas.enligne(entree.detail) + "</div>";
      liste.appendChild(element);
    });
    cible.appendChild(liste);
  }

  /* --- 6. Les écarts constatés --------------------------------------------------------------- */

  function controles(cible) {
    var donnees = Atlas.donnees("controles") || { controles: [], resume: {} };

    titrePage(
      cible,
      "Écarts constatés",
      "Ce que l'écrit promet, confronté à ce que le dépôt contient. " +
        "L'atlas <strong>pose les questions, il ne les tranche pas</strong> : « cette règle est-elle " +
        "encore d'actualité ? » est indécidable mécaniquement, et rien ici ne prétend le contraire."
    );

    var grille = Atlas.element("div", "grille");
    grille.innerHTML =
      "<div class='carte'><span class='compteur'>" + (donnees.resume.bloquants || 0) +
      "</span> écart(s) bloquant(s)<p class='discret'>Constats sans ambiguïté : un chemin qui " +
      "n'existe pas, un ADR cité absent. La CI rougit dessus.</p></div>" +
      "<div class='carte'><span class='compteur'>" + (donnees.resume.signaux || 0) +
      "</span> signal(aux)<p class='discret'>Heuristique ou choix de forme. Affichés, jamais " +
      "bloquants — une porte qui rougit sur de l'heuristique finit désactivée.</p></div>";
    cible.appendChild(grille);

    [
      ["bloquant", "Bloquants"],
      ["signal", "Signaux"],
    ].forEach(function (couple) {
      var lot = donnees.controles.filter(function (controle) {
        return controle.severite === couple[0];
      });
      cible.appendChild(Atlas.element("h2", null, couple[1] + " — " + lot.length));
      if (!lot.length) {
        cible.appendChild(Atlas.element("p", "discret", "Rien à signaler."));
        return;
      }
      var liste = Atlas.element("ul", "liste-nue");
      liste.innerHTML = lot
        .map(function (controle) {
          return (
            "<li><strong>" + E(controle.sujet) + "</strong> " + Atlas.enligne(controle.message) +
            "<div class='discret mono'>" + E(controle.code) + "</div></li>"
          );
        })
        .join("");
      cible.appendChild(liste);
    });
  }

  /* --- 7. Recherche -------------------------------------------------------------------------- */

  function recherche(cible) {
    var documents = (Atlas.donnees("corpus") || {}).documents || [];

    titrePage(
      cible,
      "Rechercher",
      "Sur les " + documents.length + " fiches du corpus — règles et décisions. " +
        "Balayage direct, sans index : la recherche par expression exacte reste donc possible."
    );

    var zone = Atlas.element("div", "filtres");
    zone.innerHTML =
      "<input type='search' id='q' autofocus placeholder='portée sportive, ADR-0075, E05US028…' " +
      "aria-label='Rechercher dans le corpus'>";
    cible.appendChild(zone);

    var resultats = Atlas.element("div");
    cible.appendChild(resultats);

    function chercher() {
      var brut = document.getElementById("q").value.trim();
      if (brut.length < 2) {
        resultats.innerHTML = "<p class='discret'>Saisis au moins deux caractères.</p>";
        return;
      }
      var terme = brut
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");

      var trouves = documents
        .map(function (document_) {
          var position = document_.recherche.indexOf(terme);
          if (position < 0) return null;
          var dansTitre = document_.titre.toLowerCase().normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "").indexOf(terme) >= 0;
          return { document: document_, score: (dansTitre ? 100 : 0) - position, position: position };
        })
        .filter(Boolean)
        .sort(function (a, b) {
          return b.score - a.score;
        });

      resultats.innerHTML =
        "<p class='discret'>" + Atlas.pluriel(trouves.length, "résultat") + "</p>" +
        "<ul class='liste-nue'>" +
        trouves
          .slice(0, 60)
          .map(function (trouve) {
            var extrait = trouve.document.texte.slice(
              Math.max(0, trouve.position - 70),
              trouve.position + 130
            );
            return (
              "<li><a href='" + trouve.document.lien + "'>" + E(trouve.document.titre) + "</a>" +
              "<div class='discret'>…" + E(extrait) + "…</div></li>"
            );
          })
          .join("") +
        "</ul>";
    }

    zone.addEventListener("input", chercher);
    chercher();
  }

  return {
    controles: controles,
    decisions: decisions,
    errata: errata,
    ficheDecision: ficheDecision,
    ficheRegle: ficheRegle,
    recherche: recherche,
    reglement: reglement,
  };
})();
