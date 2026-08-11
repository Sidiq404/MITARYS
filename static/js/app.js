
/* =======================================================
   ÉTAT
   ======================================================= */
let conversations    = [];
let messagesCourants = [];
let idCourant        = null;
let occupe           = false;

/* ---------- EXTENSIONS ---------- */
const EXTENSIONS = [
  { id:"web",     nom:"Recherche web", on:true,
    icone:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18"/>' },
  { id:"memoire", nom:"Mémoire", on:true,
    icone:'<path d="M12 3a4 4 0 0 0-4 4v1a3 3 0 0 0 0 6v2a4 4 0 0 0 8 0v-2a3 3 0 0 0 0-6V7a4 4 0 0 0-4-4z"/>' },
  { id:"prix",    nom:"Suivi des prix", on:false,
    icone:'<path d="M3 17l6-6 4 4 8-8"/><polyline points="21 3 21 9 15 9"/>' }
];

/* ---------- MODÈLES ---------- */
const MODELES = [
  { id:"RIX 1.9",    nom:"RIX 1.9",    desc:"Modèle standard. Recherche web, mémoire et comparatifs chiffrés.", badge:"DÉFAUT" },
  { id:"RIX Search", nom:"RIX Search", desc:"Recherche approfondie. Plus de sources croisées, contexte étendu." }
];
let modeleActif = MODELES[0].id;

const nomModele = () => MODELES.find(m => m.id === modeleActif).nom;

/* ---------- SÉQUENCE DES AGENTS ---------- */
const REQUETES = [
  { q:"whey protein price comparison Canada 2026",  n:8 },
  { q:"Gold Standard vs Impact Whey cost per gram", n:6 },
  { q:"Informed Sport certified whey Canada",       n:7 }
];
const ECARTES = ["reddit.com","linkedin.com","medium.com"];
const RETENUS = ["optimumnutrition.com","myprotein.ca","informed-sport.com","examine.com","sportsdietitians.ca"];


/*Pour les propositions de nos services, a aenlever apres MVP (a voir ) ! */
const QUESTIONS_ACCUEIL = [
  { texte: "Comment puis-je vous aider ?", action: "envoyer" },
  { texte: "J'ai déjà une idée précise de ce que je cherche", action: "envoyer" },
  { texte: "Audit gratuit homelab / entreprise", action: "contact" },
  { texte: "Comparer des ventilateurs ou pâtes thermiques", action: "envoyer" },
  { texte: "Je débute, je pars de zéro", action: "envoyer" }
];

function dessinerQuali(){
  const zone = document.getElementById("videQuali");
  if(!zone) return;
  zone.innerHTML = "";

  QUESTIONS_ACCUEIL.forEach(q => {
    const b = document.createElement("button");
    b.className = "quali-btn-accueil";
    b.textContent = q.texte;

    if(q.action === "contact"){
      b.onclick = () => {
        window.location.href = "mailto:support@mitarys.com?subject=Demande d'audit gratuit MITARYS";
      };
    } else {
      b.onclick = () => {
        document.getElementById("saisie").value = q.texte;
        envoyer();
      };
    }
    zone.appendChild(b);
  });
}

dessinerQuali();

/* =======================================================
   CONSTRUCTION DE L'INTERFACE
   ======================================================= */
function dessinerExtensions(){
  const zone = document.getElementById("extensions");
  zone.innerHTML = "";

  EXTENSIONS.forEach(x => {
    const b = document.createElement("button");
    b.className = "ext" + (x.on ? " on" : "");
    b.innerHTML = `
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${x.icone}</svg>
      <span class="libelle">${x.nom}</span>`;
    b.onclick = () => { x.on = !x.on; dessinerExtensions(); };
    zone.appendChild(b);
  });

  const choix = document.createElement("div");
  choix.className = "choix-modele";
  choix.id = "choixModele";
  choix.innerHTML = `
    <button class="btn-modele" onclick="basculerMenu(event)">
      <span class="nom" id="modeleActif">${nomModele()}</span>
      <svg class="fleche" width="11" height="11" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>
    <div class="menu-modele" id="menuModele"></div>`;
  zone.appendChild(choix);

  dessinerMenuModele();
}

function dessinerMenuModele(){
  const menu = document.getElementById("menuModele");
  if(!menu) return;
  menu.innerHTML = "";
  MODELES.forEach(m => {
    const b = document.createElement("button");
    b.className = "option" + (m.id === modeleActif ? " actif" : "");
    b.innerHTML = `
      <svg class="coche" width="14" height="14" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      <span>
        <span class="option-nom">${m.nom}${m.badge ? `<span class="badge">${m.badge}</span>` : ""}</span>
        <span class="option-desc">${m.desc}</span>
      </span>`;
    b.onclick = e => { e.stopPropagation(); choisirModele(m.id); };
    menu.appendChild(b);
  });
}

function basculerMenu(e){
  e.stopPropagation();
  document.getElementById("choixModele").classList.toggle("ouvert");
}

function choisirModele(id){
  modeleActif = id;
  document.getElementById("modeleActif").textContent = nomModele();
  document.getElementById("choixModele").classList.remove("ouvert");
  dessinerMenuModele();
}

document.addEventListener("click", () => {
  const c = document.getElementById("choixModele");
  if(c) c.classList.remove("ouvert");
});
document.addEventListener("keydown", e => {
  if(e.key === "Escape"){
    const c = document.getElementById("choixModele");
    if(c) c.classList.remove("ouvert");
  }
});

/* =======================================================
   NAVIGATION
   ======================================================= */
function basculerRail(){
  document.getElementById("rail").classList.toggle("replie");
}

function ajusterHauteur(t){
  t.style.height = "auto";
  t.style.height = Math.min(t.scrollHeight, 180) + "px";
  document.getElementById("btnEnvoyer").disabled = !t.value.trim() || occupe;
}

function toucheEntree(e){
  if(e.key === "Enter" && !e.shiftKey){ e.preventDefault(); envoyer(); }
}

function nouvelleConversation(){
  idCourant = null;
  messagesCourants = [];
  document.getElementById("piste").innerHTML = "";
  document.getElementById("vide").style.display = "flex";
  document.getElementById("barreTitre").textContent = "Nouvelle conversation";
  dessinerHistorique();
  if(window.innerWidth <= 860) document.getElementById("rail").classList.add("replie");
}

function heure(ts){
  const d = new Date(ts);
  return d.getHours().toString().padStart(2,"0") + ":" +
         d.getMinutes().toString().padStart(2,"0");
}

async function chargerHistorique(){
  try{
    const r = await fetch("/api/conversations");
    conversations = await r.json();
  }catch(e){
    conversations = [];
  }
  dessinerHistorique();
}

function dessinerHistorique(){
  const nav = document.getElementById("historique");
  nav.innerHTML = "";
  conversations.forEach(c => {
    const b = document.createElement("button");
    b.className = "carte-fil" + (c.id === idCourant ? " actif" : "");
    const nb = Math.ceil((c.nb_messages || 0) / 2) || 1;
    b.innerHTML = `
      <div class="carte-titre">${echapper(c.titre)}</div>
      <div class="carte-meta">
        <span class="carte-modele">${c.modele}</span>
        <span class="sep"></span>
        <span>${nb} échange${nb > 1 ? "s" : ""}</span>
        <span class="sep"></span>
        <span>${heure(c.creee_le * 1000)}</span>
        <span class="jeter" title="Supprimer">&#215;</span>
      </div>`;
    b.onclick = () => ouvrirConversation(c.id);
    b.querySelector(".jeter").onclick = e => {
      e.stopPropagation();
      supprimerConversation(c.id);
    };
    nav.appendChild(b);
  });
}

async function supprimerConversation(id){
  try{ await fetch("/api/conversations/" + id, { method:"DELETE" }); }catch(e){}
  if(id === idCourant) nouvelleConversation();
  else await chargerHistorique();
}

async function ouvrirConversation(id){
  const c = conversations.find(x => x.id === id);
  if(!c) return;
  idCourant = id;
  document.getElementById("vide").style.display = "none";
  document.getElementById("barreTitre").textContent = c.titre;

  const piste = document.getElementById("piste");
  piste.innerHTML = "";

  try{
    const r  = await fetch("/api/conversations/" + id);
    const ms = await r.json();
    messagesCourants = ms;
    ms.forEach(m => {
      const html = m.role === "user" ? echapper(m.contenu) : fmt(m.contenu);
      piste.appendChild(construireMessage(m.role, html));
    });
  }catch(e){}

  dessinerHistorique();
  versLeBas();
  if(window.innerWidth <= 860) document.getElementById("rail").classList.add("replie");
}

/* =======================================================
   MESSAGES
   ======================================================= */
function construireMessage(role, html){
  const el = document.createElement("div");
  el.className = "msg " + (role === "user" ? "msg-toi" : "msg-ia");
  if(role === "user"){
    el.innerHTML = `<div class="msg-corps">${html}</div>`;
  }else{
    el.innerHTML = `
      <div class="msg-etiq">
        <div class="logo-boite"><img class="logo-img" src="/static/img/logo.png" alt="MITARYS AI"></div>
      </div>
      <div class="msg-corps">${html}</div>`;
  }
  return el;
}

/* =======================================================
   FLOW DES AGENTS
   ======================================================= */
const BLOCS = [
  { cle:"memoire",  nom:"Consultation de la mémoire" },
  { cle:"recherche",nom:"Recherche sur le web" },
  { cle:"filtrage", nom:"Filtrage des sources" },
  { cle:"synthese", nom:"Synthèse et rédaction" }
];

function construireFlow(){
  const el = document.createElement("div");
  el.className = "msg msg-ia";
  el.innerHTML = `
    <div class="flow" id="flow">
      <div class="flow-tete">
        <span>Chaîne d'agents · ${nomModele()}</span>
        <span class="compteur" id="chrono">0.0 s</span>
      </div>
      <div class="flow-corps" id="flowCorps">
        ${BLOCS.map(b => `
          <div class="bloc" id="bl-${b.cle}">
            <span class="puce"></span>
            <span class="bloc-txt">
              <span class="bloc-nom">${b.nom}<span class="verdict" id="vd-${b.cle}"></span></span>
              <span id="zn-${b.cle}"></span>
            </span>
          </div>`).join("")}
      </div>
      <div class="flow-pied">
        <div class="logo-boite tourne"><img class="logo-img" src="/static/img/logo.png" alt=""></div>
        <span class="mot">${nomModele()} réfléchit</span>
      </div>
    </div>`;
  return el;
}

function activerBloc(cle, termine){
  const el = document.getElementById("bl-" + cle);
  if(!el) return;
  el.classList.add("vu");
  el.classList.remove("encours");
  el.classList.add(termine ? "faite" : "encours");

  const zone = document.getElementById("flowCorps");
  if(zone){
    const haut  = zone.getBoundingClientRect().top + 24;
    const cible = el.getBoundingClientRect().top + 9;
    zone.style.setProperty("--rail-h", Math.max(0, cible - haut) + "px");
  }
}

function verdict(cle, texte){
  const el = document.getElementById("vd-" + cle);
  if(el) el.textContent = texte;
}

function ajouterRequete(texte, nb){
  const zone = document.getElementById("zn-recherche");
  if(!zone) return;
  zone.classList.add("requetes");
  const el = document.createElement("span");
  el.className = "requete";
  el.innerHTML = `
    <svg class="loupe" width="11" height="11" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="2.6" stroke-linecap="round">
      <circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/>
    </svg>
    <span class="q">${echapper(texte)}</span>
    <span class="n">${nb}</span>`;
  zone.appendChild(el);
  versLeBas();
}

function ajouterPuces(cle, liste, classe){
  const zone = document.getElementById("zn-" + cle);
  if(!zone) return;
  zone.className = classe === "domaine" ? "domaines" : "sources";
  liste.forEach((d, i) => {
    setTimeout(() => {
      const el = document.createElement("span");
      el.className = classe;
      el.innerHTML = classe === "domaine" ? `<s>${d}</s>` : d;
      zone.appendChild(el);
      versLeBas();
    }, i * 130);
  });
}

function versLeBas(){
  const f = document.getElementById("flux");
  f.scrollTop = f.scrollHeight;
}

function etatAgents(actif){
  const p = document.getElementById("pastille");
  if(p) p.classList.toggle("actif", actif);
  const e = document.getElementById("etatAgents");
  if(e) e.textContent = actif ? "agents au travail…" : "4 agents en ligne";
}

/* =======================================================
   ENVOI
   ======================================================= */
async function envoyer(){
  const saisie = document.getElementById("saisie");
  const texte  = saisie.value.trim();
  if(!texte || occupe) return;

  occupe = true;
  document.getElementById("vide").style.display = "none";
  saisie.value = "";
  ajusterHauteur(saisie);

  const piste = document.getElementById("piste");
  piste.appendChild(construireMessage("user", echapper(texte)));
  versLeBas();

  if(!idCourant){
    idCourant = Date.now();
    document.getElementById("barreTitre").textContent = texte;
  }
  messagesCourants.push({ role:"user", contenu: texte });

  const flow = construireFlow();
  piste.appendChild(flow);
  versLeBas();

  etatAgents(true);
  const arreterChrono = lancerChrono();

  let reponse;
  try{
    reponse = await derouler(texte);
  }catch(err){
    reponse = `<p>Le serveur n'a pas repondu. Verifie que <code>app.py</code>
               tourne, puis relance la question.</p>
               <p class="horo">${echapper(String(err.message || err))}</p>`;
  }

  arreterChrono();
  etatAgents(false);
  flow.remove();
  piste.appendChild(construireMessage("ia", reponse));
  messagesCourants.push({ role:"ia", contenu: reponse });
  await chargerHistorique();

  occupe = false;
  versLeBas();
  saisie.focus();
}

function lancerChrono(){
  const debut = Date.now();
  const t = setInterval(() => {
    const el = document.getElementById("chrono");
    if(el) el.textContent = ((Date.now() - debut)/1000).toFixed(1) + " s";
  }, 100);
  return () => clearInterval(t);
}

/* =======================================================
   APPEL DU SERVEUR — flux d'evenements en direct
   ======================================================= */
async function derouler(question){
  // historique envoye au serveur (hors message courant, deja empile)
  const hist = messagesCourants.slice(0, -1).map(m => ({
    role   : m.role === "user" ? "user" : "assistant",
    content: m.contenu
  })).slice(-10);

  const reponse = await fetch("/api/chat", {
    method : "POST",
    headers: { "Content-Type": "application/json" },
    body   : JSON.stringify({
      message        : question,
      modele         : modeleActif,
      historique     : hist,
      conversation_id: idCourant
    })
  });

  if(!reponse.ok) throw new Error("HTTP " + reponse.status);

  const lecteur = reponse.body.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  let texteFinal = "";

  while(true){
    const { done, value } = await lecteur.read();
    if(done) break;

    tampon += decodeur.decode(value, { stream: true });
    const lignes = tampon.split("\n");
    tampon = lignes.pop();

    for(const ligne of lignes){
      if(!ligne.trim()) continue;
      let e;
      try { e = JSON.parse(ligne); } catch { continue; }

      if(e.erreur && !e.etape){ throw new Error(e.erreur); }
      if(e.reponse !== undefined){ texteFinal = e.reponse; continue; }

      traiterEvenement(e);
    }
  }

  console.log("TEXTE BRUT REÇU:", JSON.stringify(texteFinal));



  if(texteFinal.includes('[QUALIFICATION]')) {
  texteFinal = texteFinal.replace('[QUALIFICATION]', '').trim();
  if(!texteFinal){
    texteFinal = "Comment puis-je vous aider aujourd'hui ?";
  }
  afficherQualification();
}


  return fmt(texteFinal);
}

/**La function qui dessine les buttuns */
function afficherQualification(){
  const piste = document.getElementById('piste');
  const div = document.createElement('div');
  div.className = 'msg msg-ia';
  div.innerHTML = `
    <div class="quali-options">
      <button class="quali-btn" onclick="repondreQuali('J\\'ai déjà des serveurs et je cherche des ventilateurs précis.')">
        J'ai déjà des serveurs
      </button>
      <button class="quali-btn" onclick="repondreQuali('Je suis encore à l\\'étape 0, je pars de zéro.')">
        Je pars de zéro
      </button>
    </div>`;
  piste.appendChild(div);
  bas();
}

function repondreQuali(texte){
  document.querySelectorAll('.quali-btn').forEach(b => b.disabled = true);
  document.getElementById('saisie').value = texte;
  envoyer();
}

/* Applique un evenement du serveur au panneau des agents */
function traiterEvenement(e){
  const etape = e.etape;
  if(!etape) return;

  if(e.statut === "debut") activerBloc(etape, false);
  if(e.requete)            ajouterRequete(e.requete, e.n || 0);
  if(e.domaines && e.domaines.length) ajouterPuces("filtrage", e.domaines, "domaine");
  if(e.sources  && e.sources.length)  ajouterPuces("synthese", e.sources,  "source");
  if(e.verdict){
    verdict(etape, e.verdict);
    if(e.statut === "fin") activerBloc(etape, true);
  }
  versLeBas();
}

/* Markdown minimal : **gras**, URLs, [dates], paragraphes */
function fmt(t){
  if(!t)return'<p>Aucune réponse.</p>';

  let texte = t
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/\((https?:\/\/[^\s)]+)\)/g,'(<a href="$1" target="_blank" rel="noopener">$1</a>)')
    .replace(/\[([^\]]+)\]/g,'<span class="horo">[$1]</span>');

  const blocs = texte.split(/\n{2,}/);

  return blocs.map(bloc => {
    const lignes = bloc.trim().split('\n');

    const estTableau = lignes.length >= 2 &&
      lignes[0].includes('|') &&
      /^[\s|:-]+$/.test(lignes[1]);

    if(estTableau){
      const nettoyerLigne = (l) => {
        let cells = l.split('|').map(c => c.trim());
        if(cells[0] === '') cells.shift();
        if(cells[cells.length - 1] === '') cells.pop();
        return cells;
      };

      const entetes = nettoyerLigne(lignes[0]);
      const corps = lignes.slice(2).map(nettoyerLigne);

      let html = '<table class="tbl"><thead><tr>';
      entetes.forEach(e => html += `<th>${e}</th>`);
      html += '</tr></thead><tbody>';
      corps.forEach(row => {
        html += '<tr>';
        row.forEach(c => html += `<td>${c}</td>`);
        html += '</tr>';
      });
      html += '</tbody></table>';
      return html;
    }

    return '<p>' + bloc.replace(/\n/g,'<br>') + '</p>';
  }).join('');
}


function echapper(t){
  const d = document.createElement("div");
  d.textContent = t;
  return d.innerHTML;
}

/*pour le scroll vers le bas */
function bas(){
  const f = document.getElementById("flux");
  if(f) f.scrollTop = f.scrollHeight;
}

/* ---------- démarrage ---------- */
dessinerExtensions();
chargerHistorique();
