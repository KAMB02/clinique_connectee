// ══════════════════════════════════════════════════════
//  MongoDB Init — Clinique Connectée
//  Initialise la base clinique_db avec collections,
//  indexes, et données de démo
// ══════════════════════════════════════════════════════

db = db.getSiblingDB("clinique_db");

// ── Création utilisateur applicatif ──────────────────
db.createUser({
  user: "clinique_app",
  pwd: "tp-iot26@",
  roles: [{ role: "readWrite", db: "clinique_db" }]
});

// ══════════════════════════════════════════════════════
//  COLLECTION : chambres
// ══════════════════════════════════════════════════════
db.createCollection("chambres");
db.chambres.createIndex({ chambre_id: 1 }, { unique: true });

db.chambres.insertMany([
  { chambre_id: "CH-001", type: "hospitalisation", etage: 1, batiment: "A", capacite: 1, equipements: ["bracelet", "tensiometre", "co2", "perfuseur", "bouton_appel"] },
  { chambre_id: "CH-002", type: "hospitalisation", etage: 1, batiment: "A", capacite: 1, equipements: ["bracelet", "tensiometre", "co2", "perfuseur", "bouton_appel"] },
  { chambre_id: "CH-003", type: "hospitalisation", etage: 1, batiment: "A", capacite: 1, equipements: ["bracelet", "tensiometre", "co2", "perfuseur", "bouton_appel"] },
  { chambre_id: "CH-004", type: "hospitalisation", etage: 2, batiment: "A", capacite: 1, equipements: ["bracelet", "tensiometre", "co2", "perfuseur", "bouton_appel"] },
  { chambre_id: "CH-005", type: "hospitalisation", etage: 2, batiment: "A", capacite: 1, equipements: ["bracelet", "tensiometre", "co2", "perfuseur", "bouton_appel"] },
  { chambre_id: "SI-001", type: "soins_intensifs",  etage: 3, batiment: "B", capacite: 1, equipements: ["bracelet", "tensiometre", "co2", "perfuseur", "bouton_appel", "ecg", "respirateur"] },
  { chambre_id: "SI-002", type: "soins_intensifs",  etage: 3, batiment: "B", capacite: 1, equipements: ["bracelet", "tensiometre", "co2", "perfuseur", "bouton_appel", "ecg", "respirateur"] }
]);

// ══════════════════════════════════════════════════════
//  COLLECTION : patients
// ══════════════════════════════════════════════════════
db.createCollection("patients");
db.patients.createIndex({ patient_id: 1 }, { unique: true });
db.patients.createIndex({ chambre_id: 1 });
db.patients.createIndex({ statut: 1 });

db.patients.insertMany([
  {
    patient_id: "PAT-001", nom: "Koné", prenom: "Aminata", age: 45,
    chambre_id: "CH-001", date_admission: new Date("2026-06-20"),
    groupe_sanguin: "O+", allergies: ["pénicilline"],
    antecedents: ["hypertension"], statut: "hospitalise",
    medecin_referent: "Dr. Kouassi"
  },
  {
    patient_id: "PAT-002", nom: "Traoré", prenom: "Ibrahim", age: 62,
    chambre_id: "CH-002", date_admission: new Date("2026-06-22"),
    groupe_sanguin: "A+", allergies: [],
    antecedents: ["diabète type 2"], statut: "hospitalise",
    medecin_referent: "Dr. Kouassi"
  },
  {
    patient_id: "PAT-003", nom: "Bamba", prenom: "Fatoumata", age: 33,
    chambre_id: "CH-003", date_admission: new Date("2026-06-25"),
    groupe_sanguin: "B-", allergies: ["aspirine"],
    antecedents: [], statut: "hospitalise",
    medecin_referent: "Dr. N'Guessan"
  },
  {
    patient_id: "PAT-004", nom: "Ouattara", prenom: "Seydou", age: 78,
    chambre_id: "SI-001", date_admission: new Date("2026-06-18"),
    groupe_sanguin: "AB+", allergies: [],
    antecedents: ["insuffisance cardiaque", "diabète"], statut: "critique",
    medecin_referent: "Dr. N'Guessan"
  },
  {
    patient_id: "PAT-005", nom: "Diabaté", prenom: "Marie-Claire", age: 55,
    chambre_id: "SI-002", date_admission: new Date("2026-06-28"),
    groupe_sanguin: "O-", allergies: ["iode"],
    antecedents: ["AVC"], statut: "critique",
    medecin_referent: "Dr. Kouassi"
  }
]);

// ══════════════════════════════════════════════════════
//  COLLECTION : alertes
// ══════════════════════════════════════════════════════
db.createCollection("alertes");
db.alertes.createIndex({ alerte_id: 1 }, { unique: true });
db.alertes.createIndex({ chambre_id: 1 });
db.alertes.createIndex({ niveau: 1 });
db.alertes.createIndex({ statut: 1 });
db.alertes.createIndex({ timestamp: -1 });

// ══════════════════════════════════════════════════════
//  COLLECTION : utilisateurs (auth)
// ══════════════════════════════════════════════════════
db.createCollection("utilisateurs");
db.utilisateurs.createIndex({ username: 1 }, { unique: true });

// Passwords hashés avec bcrypt (valeur réelle : "clinique2026")
// Hash généré : $2b$12$... (à régénérer en prod)
db.utilisateurs.insertMany([
  {
    username: "medecin1", role: "medecin",
    nom: "Dr. Kouassi", email: "kouassi@clinique-cocody.ci",
    actif: true, created_at: new Date()
  },
  {
    username: "medecin2", role: "medecin",
    nom: "Dr. N'Guessan", email: "nguessan@clinique-cocody.ci",
    actif: true, created_at: new Date()
  },
  {
    username: "infirmier1", role: "medecin",
    nom: "Inf. Coulibaly", email: "coulibaly@clinique-cocody.ci",
    actif: true, created_at: new Date()
  },
  {
    username: "controleur1", role: "controleur",
    nom: "Sgt. Konaté", email: "konate@clinique-cocody.ci",
    actif: true, created_at: new Date()
  },
  {
    username: "technicien1", role: "technicien",
    nom: "Tech. Yao", email: "yao@clinique-cocody.ci",
    actif: true, created_at: new Date()
  },
  {
    username: "admin", role: "admin",
    nom: "Administrateur Système", email: "admin@clinique-cocody.ci",
    actif: true, created_at: new Date()
  }
]);

// ══════════════════════════════════════════════════════
//  COLLECTION : dossiers_soins (DPI)
// ══════════════════════════════════════════════════════
db.createCollection("dossiers_soins");
db.dossiers_soins.createIndex({ patient_id: 1 });
db.dossiers_soins.createIndex({ timestamp: -1 });

// ══════════════════════════════════════════════════════
//  COLLECTION : incidents_securite
// ══════════════════════════════════════════════════════
db.createCollection("incidents_securite");
db.incidents_securite.createIndex({ zone: 1 });
db.incidents_securite.createIndex({ timestamp: -1 });
db.incidents_securite.createIndex({ traite: 1 });

print("✅ clinique_db initialisée avec succès");
print("   - 7 chambres créées");
print("   - 5 patients de démo insérés");
print("   - 6 utilisateurs créés");
print("   - Collections : chambres, patients, alertes, utilisateurs, dossiers_soins, incidents_securite");
