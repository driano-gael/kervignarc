/* Atlas — rendu des pages.
 *
 * DETTE-067 — ce fichier ne passe sous aucun linter : `eslint` et `prettier` sont cadrés sur
 * `^frontend/` (hooks pre-commit) et `working-directory: frontend` (CI). Ce qui est vérifié
 * mécaniquement l'est par `backend/tests/test_atlas_site.py` ; le rendu, lui, se regarde à l'œil
 * (checklist dans `atlas/README.md`).
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
      /* Les deux origines sont comparées **explicitement**, `git` compris : un `else` implicite
       * aurait laissé un renommage côté Python passer sans bruit, et la fiche aurait cessé de
       * distinguer une note écrite d'un commit. Un test relie ces littéraux à leur source. */
      var origine = "origine inconnue";
      if (entree.origine === "incise") {
        origine = "note écrite dans la règle";
      } else if (entree.origine === "git") {
        origine = "commit " + E(entree.reference || "").slice(0, 7);
      }
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

    cible.appendChild(Atlas.element("h2", null, "Décisions liées par amendement"));
    cible.appendChild(
      Atlas.element(
        "p",
        "chapo",
        "Chaque groupe rassemble des décisions qui se sont amendées les unes les autres — " +
          "l'histoire d'une même question tranchée plusieurs fois. Les boîtes sont rangées par " +
          "date ; <strong>seules les relations réellement déclarées sont tracées</strong>, et " +
          "leur libellé apparaît au survol. Deux boîtes voisines ne sont donc pas forcément liées."
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
   * `socle` relient presque tout à presque tout et noieraient le signal.
   *
   * ⚠️ Chaque groupe transporte **ses arêtes réelles**, et pas seulement ses nœuds. Une version
   * antérieure ne rendait que la liste des nœuds, et le dessin reliait les voisins consécutifs :
   * une composante n'étant pas un chemin, cela **fabriquait des relations** — 11 arêtes
   * inexistantes sur la plus grande composante, pendant que 7 vraies n'étaient jamais montrées.
   * Le lecteur en concluait qu'ADR-0079 amende ADR-0083. C'est le « parseur qui devine et finit
   * par affirmer » que tout le reste de cet atlas s'interdit. */
  function chaines(toutes) {
    var index = {};
    var voisins = {};
    var aretes = [];
    toutes.forEach(function (decision) {
      index[decision.identifiant] = decision;
      voisins[decision.identifiant] = voisins[decision.identifiant] || {};
    });
    toutes.forEach(function (decision) {
      decision.amende_par.forEach(function (source) {
        if (!index[source]) return;
        aretes.push({ de: source, vers: decision.identifiant });
        voisins[decision.identifiant][source] = true;
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
          Object.keys(voisins[courant]).forEach(function (suivant) {
            if (!vus[suivant]) pile.push(suivant);
          });
        }
        if (groupe.length < 2) return;
        var membres = {};
        groupe.forEach(function (numero) {
          membres[numero] = true;
        });
        groupes.push({
          noeuds: groupe.sort(function (a, b) {
            return index[a].date < index[b].date ? -1 : index[a].date > index[b].date ? 1 : a < b ? -1 : 1;
          }),
          aretes: aretes.filter(function (arete) {
            return membres[arete.de] && membres[arete.vers];
          }),
        });
      });
    return groupes;
  }

  /* Les nœuds sont posés sur une rangée, dans l'ordre des dates ; **seules les arêtes réelles**
   * sont tracées, dans des couloirs sous la rangée. Chaque arête fait trois segments — vertical,
   * horizontal, vertical — donc que des angles droits, et le couloir garantit qu'aucune ne
   * traverse une boîte. Les couloirs sont attribués par coloration gloutonne d'intervalles :
   * deux arêtes qui ne se chevauchent pas partagent le même, ce qui garde le schéma bas. */
  function schemaChaine(chaine) {
    var index = {};
    ((Atlas.donnees("decisions") || {}).decisions || []).forEach(function (decision) {
      index[decision.identifiant] = decision;
    });

    var LARGEUR = 148;
    var HAUTEUR = 46;
    var ECART = 46;
    var COULOIR = 14;
    var BAS_DES_BOITES = 8 + HAUTEUR;

    var rangs = {};
    chaine.noeuds.forEach(function (numero, rang) {
      rangs[numero] = rang;
    });
    function centre(numero) {
      return 2 + rangs[numero] * (LARGEUR + ECART) + LARGEUR / 2;
    }

    var placees = [];
    chaine.aretes
      .slice()
      .sort(function (a, b) {
        return Math.abs(rangs[b.de] - rangs[b.vers]) - Math.abs(rangs[a.de] - rangs[a.vers]);
      })
      .forEach(function (arete) {
        var bas = Math.min(rangs[arete.de], rangs[arete.vers]);
        var haut = Math.max(rangs[arete.de], rangs[arete.vers]);
        var couloir = 0;
        while (
          placees.some(function (posee) {
            return posee.couloir === couloir && posee.bas < haut && bas < posee.haut;
          })
        ) {
          couloir += 1;
        }
        placees.push({ arete: arete, bas: bas, haut: haut, couloir: couloir });
      });

    var couloirs = placees.reduce(function (max, posee) {
      return Math.max(max, posee.couloir + 1);
    }, 0);
    var largeurTotale = chaine.noeuds.length * LARGEUR + (chaine.noeuds.length - 1) * ECART + 4;
    var hauteurTotale = BAS_DES_BOITES + couloirs * COULOIR + 14;

    var svg =
      "<svg class='reseau' width='" + largeurTotale + "' viewBox='0 0 " +
      largeurTotale + " " + hauteurTotale +
      "' role='img' aria-label='Amendements entre décisions liées'>";

    placees.forEach(function (posee) {
      var y = BAS_DES_BOITES + (posee.couloir + 1) * COULOIR;
      svg +=
        "<path class='arete' d='M " + centre(posee.arete.de) + " " + BAS_DES_BOITES +
        " V " + y + " H " + centre(posee.arete.vers) + " V " + BAS_DES_BOITES + "'>" +
        "<title>ADR-" + E(posee.arete.de) + " amende ADR-" + E(posee.arete.vers) +
        "</title></path>";
    });

    chaine.noeuds.forEach(function (numero, rang) {
      var x = 2 + rang * (LARGEUR + ECART);
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

    /* Le sens de l'arête décide de la colonne. Le backend distingue soigneusement les relations
     * entrantes (« Prolongé par », « Complété et partiellement révisé par ») des sortantes, avec
     * un avertissement explicite dans `normalisation.py` ; ignorer `lien.sens` ici jetait ce
     * travail et dessinait le même ADR **des deux côtés** du schéma. */
    var amont = {};
    var aval = {};
    decision.liens.forEach(function (lien) {
      if (lien.type === "us" || !index[lien.cible]) return;
      if (lien.sens === "entrant") aval[lien.cible] = lien.libelle;
      else amont[lien.cible] = lien.libelle;
    });
    decision.amende_par.forEach(function (numero) {
      if (index[numero]) aval[numero] = aval[numero] || "amende";
    });
    Object.keys(aval).forEach(function (numero) {
      delete amont[numero];
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
      "<svg class='reseau' width='" + (X_DROITE + LARGEUR + 4) + "' viewBox='0 0 " +
      (X_DROITE + LARGEUR + 4) + " " + hauteurTotale +
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

  /* Même normalisation que celle appliquée côté Python à la génération : minuscules, sans
   * diacritiques. Écrite une fois ici plutôt que recopiée à chaque usage. */
  function normaliser(texte) {
    return String(texte || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

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
      var terme = normaliser(brut);

      var trouves = documents
        .map(function (fiche) {
          var position = fiche.recherche.indexOf(terme);
          if (position < 0) return null;
          var dansTitre = normaliser(fiche.titre).indexOf(terme) >= 0;
          /* \u26a0\ufe0f `position` est un index dans `recherche` (titre + section + texte), pas dans
           * `texte`. Trancher l'extrait avec cet index-l\u00e0 d\u00e9calait **les 113 documents** \u2014 sur
           * ADR-0075 le d\u00e9calage vaut 193 caract\u00e8res, et chercher \u00ab barrage \u00bb rendait un extrait
           * vide. On relocalise donc le terme dans le texte affich\u00e9. */
          var dansTexte = normaliser(fiche.texte).indexOf(terme);
          return {
            document: fiche,
            score: (dansTitre ? 100 : 0) - position,
            position: dansTexte >= 0 ? dansTexte : 0,
          };
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
            /* Quand le terme n'est **que** dans le titre ou l'en-tête, `position` vaut 0 et
             * l'extrait est le début du document. L'encadrer de « … » des deux côtés le ferait
             * passer pour un passage relocalisé autour du terme — un extrait qui ne contient pas
             * ce qu'on cherche, présenté comme s'il le contenait. */
            var debut = Math.max(0, trouve.position - 70);
            var extrait = trouve.document.texte.slice(debut, trouve.position + 130);
            var fin = debut + extrait.length < trouve.document.texte.length ? "…" : "";
            return (
              "<li><a href='" + trouve.document.lien + "'>" + E(trouve.document.titre) + "</a>" +
              "<div class='discret'>" + (debut > 0 ? "…" : "") + E(extrait) + fin + "</div></li>"
            );
          })
          .join("") +
        "</ul>";
    }

    zone.addEventListener("input", chercher);
    chercher();
  }

  /* --- 8. L'avancement ------------------------------------------------------------------------ */

  /* Les six glyphes de la Légende de `SUIVI-US.md`. Le glyphe **fait autorité** sur l'état d'une
   * US : rien ici ne le déduit de git, et c'est délibéré — trois US ont un commit dans `main`
   * sans être livrées, une vue qui lirait le journal des commits les compterait faites. */
  var ETATS = {
    "✅": "livrée",
    "⬜": "à faire",
    "🔶": "en cours",
    "🎯": "prochaine",
    "🔒": "bloquée",
    "⛔": "absorbée",
  };

  function libelleEtat(glyphe) {
    return ETATS[glyphe] || "état inconnu";
  }

  function pastilleEtat(glyphe) {
    var classe = glyphe === "✅" ? "tenu" : glyphe === "🔒" ? "alerte" : glyphe === "🎯" ? "change" : null;
    return "<span class='pastille" + (classe ? " " + classe : "") + "'>" +
      E(glyphe) + " " + E(libelleEtat(glyphe)) + "</span>";
  }

  function avancement(cible) {
    var donnees = Atlas.donnees("avancement") || { sections: [], epics: [], dettes: [], fiches: [] };

    /* Les deux nombres viennent du générateur (`avancement.resume`), calculés par la règle de
     * comptage de la Légende — la seule. Les recalculer ici en aurait fait une **troisième**
     * écriture, sur la page dont le sujet est justement que les compteurs ne se contredisent pas. */
    var resume = donnees.resume || { livrees: 0, vivantes: 0 };
    var divergentes = donnees.sections.filter(function (section) {
      return (
        section.compteur_ecrit &&
        (section.compteur_ecrit[0] !== section.calcule[0] ||
          section.compteur_ecrit[1] !== section.calcule[1])
      );
    });

    titrePage(
      cible,
      "L'avancement",
      "Ce que les quatre livrables de suivi disent, mis côte à côte : le tracker pour l'état, " +
        "<span class='mono'>stories/</span> pour le contenu, <span class='mono'>epics/</span> pour " +
        "l'ordre, le registre pour ce qui reste dû. Les compteurs sont <strong>recalculés</strong> " +
        "depuis la règle de comptage de la Légende — jamais recopiés."
    );

    var grille = Atlas.element("div", "grille");
    grille.innerHTML =
      "<div class='carte'><span class='compteur'>" + resume.livrees + " / " + resume.vivantes +
      "</span> US livrées<p class='discret'>US distinctes, absorbées exclues. La somme des " +
      "compteurs de section vaut davantage : deux US sont listées dans deux sections.</p></div>" +
      "<div class='carte'><span class='compteur'>" + donnees.epics.length +
      "</span> epics<p class='discret'>Le graphe ci-dessous est leur <strong>réduction " +
      "transitive</strong> : une dépendance déjà impliquée par un chemin plus long n'est pas " +
      "redessinée.</p></div>" +
      "<div class='carte'><span class='compteur'>" + donnees.dettes.length +
      "</span> dettes ouvertes<p class='discret'>Telles que la table « Dette ouverte » les " +
      "porte. Une dette résorbée change de table.</p></div>" +
      "<div class='carte'><span class='compteur'>" + divergentes.length +
      "</span> compteur(s) divergent(s)<p class='discret'>Un compteur faux fait repartir la " +
      "session suivante sur une base fausse : c'est un écart <strong>bloquant</strong>.</p></div>";
    cible.appendChild(grille);

    if (donnees.entete && donnees.entete.derniere) {
      cible.appendChild(
        Atlas.element(
          "p",
          "discret",
          "Dernière US annoncée en tête du tracker : <a href='us.html?id=" +
            E(encodeURIComponent(donnees.entete.derniere)) + "'>" + E(donnees.entete.derniere) +
            "</a>."
        )
      );
    }

    cible.appendChild(Atlas.element("h2", null, "L'ordre des epics"));
    cible.appendChild(
      Atlas.element(
        "p",
        "discret",
        "Chaque colonne ne peut commencer qu'une fois la précédente disponible. " +
          "Les liaisons longues passent sous le schéma pour ne traverser aucune boîte."
      )
    );
    cible.appendChild(grapheEpics(donnees.epics));

    cible.appendChild(Atlas.element("h2", null, "Section par section"));
    donnees.sections.forEach(function (section) {
      cible.appendChild(sectionAvancement(section));
    });

    cible.appendChild(Atlas.element("h2", null, "La dette ouverte"));
    cible.appendChild(tableauDettes(donnees.dettes));
  }

  function sectionAvancement(section) {
    var bloc = Atlas.element("section", "regle");
    var ecrit = section.compteur_ecrit;
    var concorde =
      !ecrit || (ecrit[0] === section.calcule[0] && ecrit[1] === section.calcule[1]);
    var badge = !ecrit
      ? "<span class='pastille'>sans compteur écrit</span>"
      : concorde
        ? "<span class='pastille tenu'>" + section.calcule[0] + "/" + section.calcule[1] +
          " — concorde</span>"
        : "<span class='pastille alerte'>écrit " + ecrit[0] + "/" + ecrit[1] + ", recalculé " +
          section.calcule[0] + "/" + section.calcule[1] + "</span>";

    var tete = Atlas.element("div", "regle-tete");
    tete.innerHTML = "<h3>" + E(section.titre) + "</h3>" + badge;
    bloc.appendChild(tete);

    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML =
      "<table><thead><tr><th>US</th><th>Titre</th><th>État</th></tr></thead><tbody>" +
      section.lignes
        .map(function (ligne) {
          /* `E()` **par-dessus** `encodeURIComponent` : ce dernier n'encode pas l'apostrophe,
           * et tous les attributs du site sont écrits en apostrophes simples. Rien d'exploitable
           * ici (`_US` garantit `E\d{2}US\d{3}`), mais la sûreté ne doit pas reposer sur une
           * classe de caractères posée trois modules plus haut. */
          var nom = ligne.identifiant
            ? "<a href='us.html?id=" + E(encodeURIComponent(ligne.identifiant)) + "'>" +
              E(ligne.identifiant) + "</a>"
            : "<span class='discret'>hors US</span>";
          return (
            "<tr><td class='mono'>" + nom + "</td><td>" + E(ligne.titre) + "</td><td>" +
            (ligne.etat ? pastilleEtat(ligne.etat) : "") +
            (ligne.comptee ? "" : " <span class='discret'>hors décompte</span>") +
            "</td></tr>"
          );
        })
        .join("") +
      "</tbody></table>";
    bloc.appendChild(enveloppe);
    return bloc;
  }

  function tableauDettes(dettes) {
    var enveloppe = Atlas.element("div", "defilable");
    if (!dettes.length) {
      return Atlas.element("p", "discret", "Aucune dette ouverte.");
    }
    enveloppe.innerHTML =
      "<table><thead><tr><th>Dette</th><th>Sévérité</th><th>Introduite par</th>" +
      "<th>Résorption prévue</th></tr></thead><tbody>" +
      dettes
        .map(function (dette) {
          return (
            "<tr><td class='mono'>DETTE-" + E(dette.identifiant) + "</td><td>" +
            E(dette.severite) + "</td><td class='mono'>" +
            (dette.introduite_par.map(E).join(" ") || "—") + "</td><td class='mono'>" +
            (dette.resorption_us.map(E).join(" ") || "—") + "</td></tr>"
          );
        })
        .join("") +
      "</tbody></table>";
    return enveloppe;
  }

  /* Réduction transitive : une arête A→C est retirée si un chemin A→…→C existe déjà. Sur le
   * dépôt du 16/08/2026, elle fait tomber le graphe de 38 arêtes à 19, dont 18 franchissent une
   * seule colonne. Aucune information n'est perdue — la dépendance reste impliquée — et c'est ce
   * qui rend un dessin sans moteur de mise en page réellement lisible. */
  function reduire(dependances) {
    function atteignables(depart, vus) {
      (dependances[depart] || []).forEach(function (voisin) {
        if (!vus[voisin]) {
          vus[voisin] = true;
          atteignables(voisin, vus);
        }
      });
      return vus;
    }
    var reduites = {};
    Object.keys(dependances).forEach(function (noeud) {
      var indirects = {};
      (dependances[noeud] || []).forEach(function (direct) {
        atteignables(direct, indirects);
      });
      reduites[noeud] = (dependances[noeud] || []).filter(function (direct) {
        return !indirects[direct];
      });
    });
    return reduites;
  }

  function grapheEpics(epics) {
    if (!epics.length) {
      return Atlas.element("p", "discret", "Aucun epic déclaré.");
    }

    var LARGEUR = 196;
    var HAUTEUR = 46;
    var ECART_X = 74;
    var ECART_Y = 18;
    var COULOIR = 12;

    var dependances = {};
    epics.forEach(function (epic) {
      dependances[epic.identifiant] = epic.depend_de.filter(function (cible) {
        return dependances.hasOwnProperty(cible) || epics.some(function (autre) {
          return autre.identifiant === cible;
        });
      });
    });
    var reduites = reduire(dependances);

    /* Rang = longueur du plus long chemin depuis une racine. Le balayage est répété autant de fois
     * qu'il y a d'epics : c'est la borne d'un DAG, et cela **termine** même sur un cycle.
     * ⚠️ Terminer n'est pas montrer : sur un cycle, la réduction transitive efface **toutes** ses
     * arêtes, chacune étant impliquée par le chemin qui passe par les autres — le graphe faux est
     * alors la seule chose invisible. C'est pourquoi l'acyclicité est un contrôle **bloquant**
     * (`cycle-entre-epics`), et non une promesse de ce dessin. */
    var rangs = {};
    epics.forEach(function () {
      epics.forEach(function (epic) {
        var maximum = 0;
        (dependances[epic.identifiant] || []).forEach(function (cible) {
          maximum = Math.max(maximum, (rangs[cible] || 0) + 1);
        });
        rangs[epic.identifiant] = maximum;
      });
    });

    var colonnes = [];
    epics
      .slice()
      .sort(function (a, b) {
        return a.identifiant < b.identifiant ? -1 : 1;
      })
      .forEach(function (epic) {
        var rang = rangs[epic.identifiant];
        colonnes[rang] = colonnes[rang] || [];
        colonnes[rang].push(epic);
      });

    var positions = {};
    function poser() {
      colonnes.forEach(function (colonne, rang) {
        colonne.forEach(function (epic, ligne) {
          positions[epic.identifiant] = {
            x: 2 + rang * (LARGEUR + ECART_X),
            y: 10 + ligne * (HAUTEUR + ECART_Y),
            rang: rang,
          };
        });
      });
    }
    poser();

    /* Une passe de barycentre : chaque epic se replace en face de la moyenne de ses dépendances.
     * Une seule passe, pas dix — l'objectif est de décroiser l'évident, pas d'optimiser. */
    colonnes.forEach(function (colonne) {
      colonne.sort(function (a, b) {
        function moyenne(epic) {
          var cibles = reduites[epic.identifiant] || [];
          if (!cibles.length) return positions[epic.identifiant].y;
          return (
            cibles.reduce(function (somme, cible) {
              return somme + (positions[cible] ? positions[cible].y : 0);
            }, 0) / cibles.length
          );
        }
        return moyenne(a) - moyenne(b);
      });
    });
    poser();

    var hautes = colonnes.reduce(function (max, colonne) {
      return Math.max(max, colonne.length);
    }, 0);
    var basDesBoites = 10 + hautes * (HAUTEUR + ECART_Y);

    /* Deux routages, et le critère est la portée. Une liaison entre colonnes voisines tient dans
     * l'écart qui les sépare. Une liaison plus longue traverserait des boîtes : elle descend sous
     * le schéma, y circule, et remonte — même parti pris que les chaînes d'amendement. */
    var courtes = [];
    var longues = [];
    Object.keys(reduites).forEach(function (vers) {
      reduites[vers].forEach(function (de) {
        if (!positions[de] || !positions[vers]) return;
        var portee = positions[vers].rang - positions[de].rang;
        (portee === 1 ? courtes : longues).push({ de: de, vers: vers });
      });
    });

    /* Allocation de couloir par coloration d'intervalles : deux liaisons ne partagent un couloir
     * que si leurs portées ne se chevauchent pas. Même algorithme que `schemaChaine`. */
    function allouer(liaisons, borne) {
      var placees = [];
      liaisons.forEach(function (liaison) {
        var bas = Math.min(borne(liaison).a, borne(liaison).b);
        var haut = Math.max(borne(liaison).a, borne(liaison).b);
        var couloir = 0;
        while (
          placees.some(function (posee) {
            return posee.couloir === couloir && posee.bas < haut && bas < posee.haut;
          })
        ) {
          couloir += 1;
        }
        placees.push({ liaison: liaison, bas: bas, haut: haut, couloir: couloir });
      });
      return placees;
    }

    var placeesLongues = allouer(longues, function (liaison) {
      return { a: positions[liaison.de].x, b: positions[liaison.vers].x };
    });
    var couloirs = placeesLongues.reduce(function (max, posee) {
      return Math.max(max, posee.couloir + 1);
    }, 0);

    var largeurTotale = colonnes.length * (LARGEUR + ECART_X) + 4;
    var hauteurTotale = basDesBoites + couloirs * COULOIR + 14;

    var svg =
      "<svg class='reseau' width='" + largeurTotale + "' viewBox='0 0 " + largeurTotale + " " +
      hauteurTotale + "' role='img' aria-label='Dépendances entre epics'>";

    courtes.forEach(function (liaison) {
      var depart = positions[liaison.de];
      var arrivee = positions[liaison.vers];
      var milieu = depart.x + LARGEUR + ECART_X / 2;
      svg +=
        "<path class='arete' d='M " + (depart.x + LARGEUR) + " " + (depart.y + HAUTEUR / 2) +
        " H " + milieu + " V " + (arrivee.y + HAUTEUR / 2) + " H " + arrivee.x + "'>" +
        "<title>EPIC-" + E(liaison.vers) + " dépend d'EPIC-" + E(liaison.de) + "</title></path>";
    });

    placeesLongues.forEach(function (posee) {
      var depart = positions[posee.liaison.de];
      var arrivee = positions[posee.liaison.vers];
      var y = basDesBoites + (posee.couloir + 1) * COULOIR;
      svg +=
        "<path class='arete' d='M " + (depart.x + LARGEUR / 2) + " " + (depart.y + HAUTEUR) +
        " V " + y + " H " + (arrivee.x + LARGEUR / 2) + " V " + (arrivee.y + HAUTEUR) + "'>" +
        "<title>EPIC-" + E(posee.liaison.vers) + " dépend d'EPIC-" + E(posee.liaison.de) +
        "</title></path>";
    });

    epics.forEach(function (epic) {
      var position = positions[epic.identifiant];
      svg +=
        "<rect class='boite' x='" + position.x + "' y='" + position.y + "' width='" + LARGEUR +
        "' height='" + HAUTEUR + "' rx='4'></rect>" +
        "<text x='" + (position.x + 10) + "' y='" + (position.y + 19) + "'>EPIC-" +
        E(epic.identifiant) + "</text>" +
        "<text class='etiquette' x='" + (position.x + 10) + "' y='" + (position.y + 36) + "'>" +
        E(couper(epic.titre, 30)) + "</text>";
    });

    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML = svg + "</svg>";
    return enveloppe;
  }

  /* --- 9. La fiche d'une US ------------------------------------------------------------------- */

  function ficheUs(cible) {
    var donnees = Atlas.donnees("avancement") || { fiches: [], dettes: [] };
    var identifiant = Atlas.parametre("id");
    var fiche = donnees.fiches.filter(function (candidate) {
      return candidate.identifiant === identifiant;
    })[0];

    if (!fiche) {
      titrePage(cible, "US introuvable", "Le tracker ne porte aucune ligne « " + E(identifiant) + " ».");
      cible.appendChild(Atlas.element("p", null, "<a href='avancement.html'>Retour à l'avancement</a>"));
      return;
    }

    titrePage(cible, fiche.identifiant + " — " + fiche.titre, "");

    var tete = Atlas.element("p", null);
    tete.innerHTML =
      pastilleEtat(fiche.etat) +
      " <span class='pastille'>EPIC-" + E(fiche.epic) +
      (fiche.epic_titre ? " · " + E(fiche.epic_titre) : "") + "</span>";
    cible.appendChild(tete);

    var lignes = [
      ["Sections du tracker", fiche.sections.map(E).join(" · ") || "—"],
      [
        "Spécifiée dans",
        fiche.story
          ? "<span class='mono'>" + E(fiche.story) + "</span>" +
            (fiche.titre_story && fiche.titre_story !== fiche.titre
              ? " — « " + E(fiche.titre_story) + " »"
              : "")
          : "<strong>aucune fiche dans stories/</strong>",
      ],
      [
        "Décisions qui la citent",
        fiche.adr
          .map(function (numero) {
            return "<a href='adr.html?id=" + E(numero) + "'>ADR-" + E(numero) + "</a>";
          })
          .join(" · ") || "—",
      ],
      ["Dette introduite", fiche.dettes_introduites.map(function (d) { return "DETTE-" + E(d); }).join(" · ") || "—"],
      ["Dette résorbée", fiche.dettes_resorbees.map(function (d) { return "DETTE-" + E(d); }).join(" · ") || "—"],
    ];

    var liste = Atlas.element("ul", "liste-nue");
    liste.innerHTML = lignes
      .map(function (couple) {
        return "<li><div class='discret'>" + couple[0] + "</div><div>" + couple[1] + "</div></li>";
      })
      .join("");
    cible.appendChild(liste);

    cible.appendChild(
      Atlas.element(
        "p",
        "discret",
        "L'atlas ne dit pas si cette US est <em>faite</em> : il rapporte le glyphe écrit dans le " +
          "tracker, qui fait autorité. Trois US ont un commit dans <span class='mono'>main</span> " +
          "sans être livrées — un état déduit de git serait faux."
      )
    );
    cible.appendChild(Atlas.element("p", null, "<a href='avancement.html'>Retour à l'avancement</a>"));
  }

  /* --- 8. La carte du code -------------------------------------------------------------------- */

  /* Le schéma du sens des dépendances. Les cinq couches sont posées **dans l'ordre du sens
   * autorisé** — le domaine à gauche, la racine de composition à droite —, et chaque import
   * traversant est tiré sous la rangée. La propriété visuelle est alors immédiate : quand
   * l'architecture est tenue, **toutes les flèches pointent vers la gauche**. Une seule qui pointe
   * à droite, et elle est rouge.
   *
   * Tracé orthogonal (V/H), comme les deux autres schémas du site : aucune courbe, aucun
   * chevauchement — le rendu Mermaid avait été écarté pour cette raison exacte (ADR-0086). */
  function schemaCouches(donnees) {
    var LARGEUR = 148;
    var HAUTEUR = 44;
    var ECART = 30;
    var COULOIR = 17;
    var BAS = 8 + HAUTEUR;

    var couches = donnees.couches || [];
    var rang = {};
    couches.forEach(function (couche, index) {
      rang[couche] = index;
    });
    var centre = function (couche) {
      return 2 + rang[couche] * (LARGEUR + ECART) + LARGEUR / 2;
    };

    var traversantes = (donnees.matrice || []).filter(function (cellule) {
      return cellule.occurrences > 0;
    });

    /* Placement en couloirs : une liaison descend jusqu'au premier couloir libre sur son
     * intervalle, donc deux liaisons qui se chevauchent ne partagent jamais un couloir.
     *
     * ⚠️ Le nommage suit **exactement** celui des deux autres schémas du site (`schemaChaine`,
     * `grapheEpics`) : `bas` = borne inférieure, `haut` = borne supérieure, test de recouvrement
     * `posee.bas < haut && bas < posee.haut`. La première version inversait les deux noms et le
     * sens des comparaisons — correct isolément, mais c'est le piège : copier une ligne d'un
     * schéma à l'autre y introduisait un bug muet, sur du JS que ni linter ni typage ne regardent
     * (DETTE-067). Le tri diffère en revanche volontairement (courtes d'abord ici, longues
     * d'abord dans `schemaChaine`) : ce schéma n'a que cinq boîtes, les courtes au plus près.
     *
     * 3ᵉ occurrence de cette coloration d'intervalles dans le fichier : le seuil du § Dette est
     * atteint, le remède (hisser `allouer` au niveau du module) est renvoyé à E00US026, qui
     * touche déjà ces fichiers — pas en douce ici. */
    var placees = [];
    traversantes
      .slice()
      .sort(function (a, b) {
        return (
          Math.abs(rang[a.source] - rang[a.cible]) - Math.abs(rang[b.source] - rang[b.cible])
        );
      })
      .forEach(function (cellule) {
        var bas = Math.min(centre(cellule.source), centre(cellule.cible));
        var haut = Math.max(centre(cellule.source), centre(cellule.cible));
        var couloir = 0;
        while (
          placees.some(function (posee) {
            return posee.couloir === couloir && posee.bas < haut && bas < posee.haut;
          })
        ) {
          couloir += 1;
        }
        placees.push({ cellule: cellule, bas: bas, haut: haut, couloir: couloir });
      });

    var couloirs = placees.reduce(function (max, posee) {
      return Math.max(max, posee.couloir + 1);
    }, 0);
    var largeurTotale = couches.length * LARGEUR + (couches.length - 1) * ECART + 4;
    var hauteurTotale = BAS + couloirs * COULOIR + 18;

    var svg =
      "<svg class='reseau' width='" + largeurTotale + "' viewBox='0 0 " + largeurTotale + " " +
      hauteurTotale + "' role='img' aria-label='Sens des dépendances entre les cinq couches'>";

    placees.forEach(function (posee) {
      var cellule = posee.cellule;
      var y = BAS + (posee.couloir + 1) * COULOIR;
      var xDepart = centre(cellule.source);
      var xArrivee = centre(cellule.cible);
      var classe = cellule.autorise ? "arete" : "arete interdite";
      var sens = cellule.autorise ? "dépend de" : "REMONTE vers";
      svg +=
        "<path class='" + classe + "' d='M " + xDepart + " " + BAS + " V " + y + " H " + xArrivee +
        " V " + (BAS + 7) + "'><title>" + E(cellule.source) + " " + sens + " " + E(cellule.cible) +
        " — " + cellule.occurrences + " imports</title></path>" +
        /* La pointe marque **l'arrivée** : sans elle, un tracé orthogonal ne dit pas qui dépend
         * de qui, et le schéma se lit à l'envers une fois sur deux. */
        "<path class='fleche" + (cellule.autorise ? "" : " interdite") + "' d='M " +
        (xArrivee - 4) + " " + (BAS + 8) + " L " + (xArrivee + 4) + " " + (BAS + 8) + " L " +
        xArrivee + " " + BAS + " Z'></path>" +
        "<text class='etiquette' x='" + ((xDepart + xArrivee) / 2) + "' y='" + (y - 4) +
        "' text-anchor='middle'>" + cellule.occurrences + "</text>";
    });

    couches.forEach(function (couche, index) {
      var x = 2 + index * (LARGEUR + ECART);
      var permis = (donnees.sens_autorise || {})[couche] || [];
      svg +=
        "<rect class='boite" + (couche === "domain" ? " pivot" : "") + "' x='" + x +
        "' y='8' width='" + LARGEUR + "' height='" + HAUTEUR + "' rx='4'><title>" + E(couche) +
        " peut importer : " + E(permis.join(", ") || "aucune couche") + "</title></rect>" +
        "<text x='" + (x + 10) + "' y='27'>" + E(couche) + "</text>" +
        "<text class='etiquette' x='" + (x + 10) + "' y='44'>" +
        E(permis.length ? "→ " + permis.length + " couche(s)" : "n'importe rien") + "</text>";
    });

    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML = svg + "</svg>";
    return enveloppe;
  }

  function matriceCouches(donnees) {
    var couches = donnees.couches || [];
    var par = {};
    (donnees.matrice || []).forEach(function (cellule) {
      par[cellule.source + ">" + cellule.cible] = cellule;
    });

    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML =
      "<table><thead><tr><th>importe →</th>" +
      couches
        .map(function (couche) {
          return "<th>" + E(couche) + "</th>";
        })
        .join("") +
      "</tr></thead><tbody>" +
      couches
        .map(function (source) {
          return (
            "<tr><th scope='row'>" + E(source) + "</th>" +
            couches
              .map(function (cible) {
                if (source === cible) {
                  return "<td class='discret'>—</td>";
                }
                var cellule = par[source + ">" + cible];
                if (!cellule || !cellule.occurrences) {
                  /* Une case vide **autorisée** et une case vide **interdite** ne disent pas la
                   * même chose : la première est une dépendance qui n'existe pas encore, la
                   * seconde une dépendance qui ne doit jamais exister. */
                  return (
                    "<td class='discret'>" +
                    (cellule && cellule.autorise ? "0" : "<span title='interdit par la règle 2'>✕</span>") +
                    "</td>"
                  );
                }
                return cellule.autorise
                  ? "<td class='mono'>" + cellule.occurrences + "</td>"
                  : "<td class='mono'><span class='pastille alerte'>" + cellule.occurrences +
                      " — interdit</span></td>";
              })
              .join("") +
            "</tr>"
          );
        })
        .join("") +
      "</tbody></table>";
    return enveloppe;
  }

  function tableauPaquets(paquets) {
    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML =
      "<table><thead><tr><th>Paquet</th><th>importe</th><th>Imports</th><th>Depuis</th></tr>" +
      "</thead><tbody>" +
      paquets
        .map(function (arete) {
          var fichiers = arete.origines
            .map(function (chemin) {
              return "<li class='mono'>" + E(chemin) + "</li>";
            })
            .join("");
          return (
            "<tr><td class='mono'>" + E(arete.source) + "</td><td class='mono'>" +
            E(arete.cible) + "</td><td>" +
            (arete.autorise
              ? arete.occurrences
              : "<span class='pastille alerte'>" + arete.occurrences + " — interdit</span>") +
            "</td><td><details><summary>" +
            Atlas.pluriel(arete.origines.length, "fichier") +
            "</summary><ul class='liste-nue'>" + fichiers + "</ul></details></td></tr>"
          );
        })
        .join("") +
      "</tbody></table>";
    return enveloppe;
  }

  function tableauPorts(ports) {
    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML =
      "<table><thead><tr><th>Port</th><th>Déclaré dans</th><th>Méthodes</th><th>Adapters</th>" +
      "</tr></thead><tbody>" +
      ports
        .map(function (port) {
          /* Un port à un seul membre apparie tout ce qui porte une méthode du même nom, sémantique
           * comprise : 26 des 60 ports sont dans ce cas et produisent plus de la moitié des
           * appariements affichés. Le dire sur la ligne, plutôt que de laisser « 24 candidats »
           * passer pour un inventaire. */
          var peuDiscriminant = port.methodes.length < 2 && port.adapters.length > 2;
          var adapters = port.adapters.length
            ? "<details><summary>" + Atlas.pluriel(port.adapters.length, "candidat") +
              (peuDiscriminant ? " <span class='discret'>— apparié sur un seul membre, peu discriminant</span>" : "") +
              "</summary><ul class='liste-nue'>" +
              port.adapters
                .map(function (adapter) {
                  return (
                    "<li><strong>" + E(adapter.nom) + "</strong> <span class='discret mono'>" +
                    E(adapter.fichier) + "</span></li>"
                  );
                })
                .join("") +
              "</ul></details>"
            : "<span class='pastille alerte'>aucun</span>";
          return (
            "<tr><td><strong>" + E(port.nom) + "</strong></td><td class='mono'>" +
            E(port.fichier) +
            (port.hors_domaine ? " <span class='pastille change'>hors domaine</span>" : "") +
            "</td><td class='discret'>" + E(port.methodes.join(", ") || "aucune") + "</td><td>" +
            adapters + "</td></tr>"
          );
        })
        .join("") +
      "</tbody></table>";
    return enveloppe;
  }

  function tableauFront(front) {
    var enveloppe = Atlas.element("div", "defilable");
    enveloppe.innerHTML =
      "<table><thead><tr><th>Feature</th><th>Importée par</th></tr></thead><tbody>" +
      front.fan_in
        .map(function (ligne) {
          /* Le seuil est **indicatif** et assumé comme tel : rien dans les règles ne fixe le
           * nombre de clientes à partir duquel une feature cesse d'en être une. Il attire l'œil,
           * il ne prononce pas de verdict — le verdict, ce sont les nœuds ci-dessus. */
          var brique = ligne.clientes >= 8;
          return (
            "<tr><td class='mono'>" + E(ligne.feature) + "</td><td>" + ligne.clientes +
            (brique
              ? " <span class='pastille change'>brique commune de fait</span>"
              : "") +
            "</td></tr>"
          );
        })
        .join("") +
      "</tbody></table>";
    return enveloppe;
  }

  function carte(cible) {
    var donnees =
      Atlas.donnees("carte") ||
      { couches: [], matrice: [], paquets: [], ports: [], front: { fan_in: [], enchevetrements: [] }, resume: {} };
    var resume = donnees.resume || {};
    var front = donnees.front || { fan_in: [], enchevetrements: [], aretes: [] };

    titrePage(
      cible,
      "La carte du code",
      "Ce que les imports font <strong>réellement</strong> des règles d'architecture. Le backend " +
        "est lu à l'<strong>AST</strong> — exact, imports relatifs résolus : c'est ce qui autorise " +
        "un contrôle bloquant. Le front est lu à l'<strong>expression régulière</strong>, faute de " +
        "savoir lire du TypeScript sans dépendance : ses constats sont des <strong>signaux</strong>, " +
        "jamais des blocages."
    );

    var grille = Atlas.element("div", "grille");
    grille.innerHTML =
      /* Les deux nombres, et pas seulement le premier : la matrice ci-dessous ne somme que les
       * imports **franchissant une couche**, l'écart étant celui des arêtes intra-couche entre
       * paquets. Une page dont l'argument est « un nombre qu'on ne peut pas aller vérifier ne se
       * corrige jamais » ne peut pas se permettre une addition qui ne tombe pas juste. */
      "<div class='carte'><span class='compteur'>" + (resume.imports || 0) +
      "</span> imports entre paquets<p class='discret'>Dont <strong>" +
      (resume.imports_entre_couches || 0) + "</strong> franchissent une couche — c'est ce que " +
      "somme la matrice — et <strong>" + (resume.violations || 0) + "</strong> à contresens. Un " +
      "seul suffit à faire rougir <span class='mono'>--verifier</span> : la règle 2 n'était " +
      "vérifiée que pour le domaine.</p></div>" +
      "<div class='carte'><span class='compteur'>" + (resume.ports || 0) +
      "</span> ports<p class='discret'>Dont <strong>" + (resume.ports_hors_domaine || 0) +
      "</strong> hors du domaine et <strong>" + (resume.ports_sans_adapter || 0) +
      "</strong> sans adapter. Appariement structurel : signalé, jamais bloqué.</p></div>" +
      "<div class='carte'><span class='compteur'>" + (resume.features || 0) +
      "</span> features au front<p class='discret'>Reliées par <strong>" +
      (resume.aretes_front || 0) + "</strong> imports croisés. La règle 10 veut des features " +
      "autonomes ; rien ne le vérifiait.</p></div>" +
      "<div class='carte'><span class='compteur'>" + (resume.enchevetrements || 0) +
      "</span> nœuds enchevêtrés<p class='discret'>Le plus gros tient <strong>" +
      (resume.plus_gros_noeud || 0) + "</strong> features : aucune ne peut plus être lue, testée " +
      "ni retirée seule.</p></div>";
    cible.appendChild(grille);

    cible.appendChild(Atlas.element("h2", null, "Le sens des dépendances"));
    cible.appendChild(
      Atlas.element(
        "p",
        "discret",
        "Les couches sont posées dans l'ordre du sens autorisé — le domaine à gauche, la racine " +
          "de composition à droite. Quand l'architecture est tenue, <strong>toutes les flèches " +
          "pointent vers la gauche</strong> ; une flèche rouge remonte le courant. " +
          "<strong>Limite assumée</strong> : la lecture couvre les imports statiques et les " +
          "<span class='mono'>import_module(\"…\")</span> à cible littérale ; un module dont le " +
          "nom est <em>calculé</em> à l'exécution reste hors de portée."
      )
    );
    cible.appendChild(schemaCouches(donnees));

    cible.appendChild(Atlas.element("h2", null, "Couche par couche"));
    cible.appendChild(
      Atlas.element(
        "p",
        "discret",
        "Une case <span class='mono'>✕</span> est une dépendance que la règle 2 interdit : elle " +
          "doit rester vide. Une case <span class='mono'>0</span> est simplement une dépendance " +
          "qui n'existe pas encore."
      )
    );
    cible.appendChild(matriceCouches(donnees));

    cible.appendChild(Atlas.element("h2", null, "Paquet par paquet"));
    cible.appendChild(
      Atlas.element(
        "p",
        "discret",
        "Le grain fin, fichiers d'origine compris — un nombre qu'on ne peut pas aller vérifier " +
          "ne se corrige jamais."
      )
    );
    cible.appendChild(tableauPaquets(donnees.paquets || []));

    cible.appendChild(Atlas.element("h2", null, "Les ports et leurs adapters"));
    cible.appendChild(
      Atlas.element(
        "p",
        "discret",
        "Un <span class='mono'>Protocol</span> s'implémente <strong>sans héritage</strong> : " +
          "l'appariement est donc structurel — une classe qui porte toutes les méthodes publiques " +
          "du port. Un port à une seule méthode courante sur-apparie ; seul le <strong>zéro</strong> " +
          "est signalé, le reste est laissé au jugement."
      )
    );
    cible.appendChild(tableauPorts(donnees.ports || []));

    cible.appendChild(Atlas.element("h2", null, "Le front, mesuré à l'expression régulière"));
    var noeuds = front.enchevetrements || [];
    cible.appendChild(
      Atlas.element(
        "p",
        null,
        noeuds.length
          ? "<strong>" + Atlas.pluriel(noeuds.length, "groupe") + "</strong> de features " +
            "s'importent mutuellement, directement ou non : " +
            noeuds
              .map(function (noeud) {
                return "<span class='mono'>" + E(noeud.join(" ↔ ")) + "</span>";
              })
              .join(" · ") +
            "."
          : "Aucune feature n'en importe une autre en cercle."
      )
    );
    cible.appendChild(
      Atlas.element(
        "p",
        "discret",
        "Ce sont des <strong>composantes fortement connexes</strong>, pas un compte de cycles : " +
          "ce dernier dépend de l'ordre de parcours, donc deux exécutions pourraient en annoncer " +
          "des nombres différents — inacceptable sur une sortie comparée à l'octet en CI. Les " +
          "fichiers de <strong>test</strong> sont exclus du graphe : reprocher à une feature de " +
          "ne plus pouvoir être <em>testée</em> seule n'a pas de sens si c'est le test qui crée " +
          "le lien."
      )
    );
    cible.appendChild(tableauFront(front));
  }

  return {
    avancement: avancement,
    carte: carte,
    controles: controles,
    decisions: decisions,
    errata: errata,
    ficheDecision: ficheDecision,
    ficheRegle: ficheRegle,
    ficheUs: ficheUs,
    recherche: recherche,
    reglement: reglement,
  };
})();
