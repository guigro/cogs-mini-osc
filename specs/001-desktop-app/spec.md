# Feature Specification: Mini-OSC en logiciel de bureau autonome

**Feature Branch**: `feature/desktop-app`

**Created**: 2026-10-04

**Status**: Draft

**Input**: User description: "Transformer Mini-OSC en vrai logiciel de bureau autonome, distribué en un seul fichier par système : Mini-OSC.app (dans un .dmg) pour macOS, Mini-OSC.exe pour Windows, Mini-OSC.AppImage pour Linux. Aucune installation de Python requise. Au lancement, l'application démarre ses serveurs (OSC, HTTP Flask, TCP/UDP) exactement comme aujourd'hui et ouvre une vraie fenêtre native (pywebview) affichant l'interface web actuelle, sans aucune modification de l'UI ni de la logique de routage. Fermer la fenêtre quitte le logiciel (pas d'icône en tâche de fond). Adaptations nécessaires : config.json et logs stockés dans le dossier utilisateur standard de chaque OS (config par défaut créée au premier lancement), bouton Restart géré dans l'application (plus de dépendance au code de sortie 42 et au script .command), Bulma et Font Awesome intégrés en local (fonctionne hors ligne), une seule instance à la fois. Builds produits par GitHub Actions (runners Mac, Windows, Linux) avec PyInstaller. Applications non signées (avertissements Gatekeeper/SmartScreen acceptés). Le mode lancement en script Python actuel doit continuer de fonctionner."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lancer Mini-OSC d'un double-clic dans sa propre fenêtre (Priority: P1)

L'opérateur de la salle télécharge un seul fichier pour son système (Mac, Windows ou Linux), le lance d'un double-clic, et Mini-OSC démarre dans une vraie fenêtre de logiciel, avec exactement la même interface qu'aujourd'hui (onglets Servers, Connections, Logs). Aucun terminal, aucun navigateur, aucune installation de Python. Les messages OSC, HTTP, TCP et UDP sont routés comme avec la version script.

**Why this priority**: c'est le cœur de la demande. Sans ça, rien d'autre n'a de valeur.

**Independent Test**: sur une machine sans Python, lancer le fichier livré, vérifier que la fenêtre s'ouvre avec l'interface habituelle, ajouter une connexion HTTP vers OSC et vérifier qu'un message envoyé arrive bien à destination.

**Acceptance Scenarios**:

1. **Given** une machine Mac, Windows ou Linux sans Python installé, **When** l'opérateur lance le fichier Mini-OSC, **Then** une fenêtre de logiciel s'ouvre et affiche l'interface Mini-OSC complète en moins de 10 secondes.
2. **Given** Mini-OSC lancé avec une connexion configurée, **When** un message arrive sur la source de cette connexion, **Then** il est transmis à la destination exactement comme avec la version script.
3. **Given** Mini-OSC lancé, **When** l'opérateur ferme la fenêtre, **Then** le logiciel s'arrête entièrement et libère tous ses ports réseau.
4. **Given** la machine n'a aucun accès internet, **When** l'opérateur lance Mini-OSC, **Then** l'interface s'affiche avec sa mise en forme et ses icônes complètes.

---

### User Story 2 - Configuration et logs conservés entre les lancements et les mises à jour (Priority: P1)

La configuration (serveurs, connexions, règles d'ignore, journalisation) et les fichiers de logs sont rangés dans le dossier utilisateur standard du système. Au tout premier lancement, une configuration par défaut est créée. Remplacer le fichier de l'application par une version plus récente ne fait rien perdre.

**Why this priority**: un logiciel empaqueté ne peut pas écrire à côté de lui-même. Sans emplacement persistant, la configuration serait perdue ou l'application planterait au premier enregistrement.

**Independent Test**: lancer l'application, ajouter une connexion, quitter, relancer et vérifier que la connexion est toujours là. Remplacer le fichier de l'application par une nouvelle copie et relancer : la connexion est toujours là.

**Acceptance Scenarios**:

1. **Given** un premier lancement sur une machine, **When** l'application démarre, **Then** une configuration par défaut valide est créée dans le dossier utilisateur et l'application fonctionne avec.
2. **Given** une configuration modifiée depuis l'interface, **When** l'application est quittée puis relancée, **Then** toutes les modifications sont conservées.
3. **Given** une ancienne configuration au format `targets` + `routes` déposée dans le dossier utilisateur, **When** l'application démarre, **Then** elle est convertie automatiquement au format `connections` comme le fait déjà la version script.
4. **Given** la journalisation fichier activée, **When** l'application tourne, **Then** les logs sont écrits dans le dossier utilisateur avec la rotation quotidienne existante.
5. **Given** l'opérateur veut retrouver ou sauvegarder sa configuration, **When** il consulte l'interface ou la documentation, **Then** l'emplacement exact du fichier de configuration lui est indiqué.

---

### User Story 3 - Redémarrer depuis l'interface (Priority: P2)

Le bouton Restart de l'interface relance Mini-OSC (pour appliquer des changements de ports serveur, par exemple) sans script de lancement externe, et la fenêtre revient avec l'interface rechargée.

**Why this priority**: fonction existante utilisée en exploitation. Elle repose aujourd'hui sur le script `.command`, absent de la version empaquetée.

**Independent Test**: changer le port du serveur OSC depuis l'interface, cliquer sur Restart, vérifier que Mini-OSC écoute sur le nouveau port et que l'interface est de nouveau utilisable.

**Acceptance Scenarios**:

1. **Given** l'application lancée, **When** l'opérateur clique sur Restart, **Then** Mini-OSC redémarre avec la configuration enregistrée et l'interface est de nouveau utilisable en moins de 10 secondes.
2. **Given** un redémarrage en cours, **When** il se termine, **Then** une seule fenêtre et une seule instance de Mini-OSC existent.

---

### User Story 4 - Une seule instance à la fois (Priority: P2)

Si l'opérateur relance Mini-OSC alors qu'il tourne déjà, aucune seconde instance ne démarre pour se disputer les ports. La fenêtre existante revient au premier plan, ou à défaut l'opérateur est clairement prévenu que Mini-OSC tourne déjà.

**Why this priority**: évite les conflits de ports et les comportements incompréhensibles pendant une session de jeu.

**Independent Test**: lancer Mini-OSC deux fois de suite et vérifier qu'une seule instance tourne et que le routage fonctionne toujours.

**Acceptance Scenarios**:

1. **Given** Mini-OSC déjà lancé, **When** l'opérateur le lance une deuxième fois, **Then** aucune seconde instance ne reste active et l'instance existante continue de router normalement.

---

### User Story 5 - Produire les trois versions automatiquement (Priority: P2)

Le mainteneur publie une nouvelle version et obtient automatiquement les quatre fichiers (macOS Apple Silicon, macOS Intel, Windows, Linux x86_64), prêts à télécharger, sans avoir besoin de posséder les trois systèmes.

**Why this priority**: sans production automatique, il faudrait trois machines différentes à chaque mise à jour.

**Independent Test**: créer une version sur le dépôt et vérifier que les trois fichiers sont produits et téléchargeables.

**Acceptance Scenarios**:

1. **Given** une nouvelle version marquée sur le dépôt, **When** la production automatique se termine, **Then** les quatre fichiers (macOS Apple Silicon, macOS Intel, Windows, Linux x86_64) sont disponibles au téléchargement.
2. **Given** une modification qui casse la production d'une des versions, **When** la production tourne, **Then** l'échec est visible et aucun fichier incomplet n'est publié pour ce système.

---

### User Story 6 - La version script continue de fonctionner (Priority: P3)

Les installations actuelles lancées en script Python (`python mini_osc.py`, `Start_OSC_Webapp.command`) continuent de fonctionner comme avant, avec leur `config.json` au même endroit.

**Why this priority**: des machines tournent déjà ainsi en production. La transition doit pouvoir se faire à son rythme.

**Independent Test**: sur une installation script existante, mettre à jour le code, lancer comme d'habitude et vérifier que la configuration existante est chargée et que le routage fonctionne.

**Acceptance Scenarios**:

1. **Given** une installation script existante avec son `config.json`, **When** elle est lancée après la mise à jour du code, **Then** elle utilise toujours ce `config.json` et fonctionne à l'identique, bouton Restart compris.

---

### Edge Cases

- Un port configuré (serveur HTTP, OSC, TCP ou UDP) est déjà utilisé par un autre programme : l'application ne doit pas rester bloquée sur une fenêtre vide. L'erreur est visible pour l'opérateur.
- Le fichier de configuration est corrompu ou illisible : l'application le signale clairement, sans écraser silencieusement les réglages de l'opérateur.
- Le serveur HTTP est configuré sur une adresse réseau précise (IP de la machine sur le LAN) ou sur toutes les interfaces : la fenêtre doit quand même afficher l'interface.
- Le dossier utilisateur n'existe pas encore : il est créé au premier lancement.
- Premier lancement sur Mac ou Windows avec les avertissements de sécurité (application non signée) et la demande d'autorisation du pare-feu : la marche à suivre est documentée.
- Linux sans le composant d'affichage web nécessaire : un message explique quoi installer.
- La fenêtre est fermée pendant qu'un message est en cours de transmission : l'arrêt reste propre et ne laisse aucun processus orphelin.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le logiciel MUST être livré sous la forme d'un seul fichier téléchargeable par plateforme, pour quatre plateformes : macOS Apple Silicon, macOS Intel, Windows et Linux x86_64.
- **FR-002**: Le logiciel MUST fonctionner sur une machine où Python et les dépendances de Mini-OSC ne sont pas installés.
- **FR-003**: Au lancement, le logiciel MUST démarrer tous les serveurs prévus par la configuration (OSC, HTTP, TCP, UDP), avec le même comportement que la version script.
- **FR-004**: Le logiciel MUST afficher l'interface Mini-OSC actuelle dans une fenêtre native du système, sans passer par le navigateur de l'utilisateur.
- **FR-005**: L'interface et la logique de routage MUST rester fonctionnellement identiques à la version actuelle : mêmes onglets, mêmes écrans, mêmes protocoles, même format de configuration.
- **FR-006**: Fermer la fenêtre MUST arrêter complètement le logiciel et libérer ses ports. Il n'y a pas de fonctionnement en tâche de fond.
- **FR-007**: L'interface MUST s'afficher complètement (styles et icônes) sans aucune connexion internet.
- **FR-008**: En version empaquetée, la configuration et les logs MUST être stockés dans le dossier de données utilisateur standard du système.
- **FR-009**: Au premier lancement, si aucune configuration n'existe, le logiciel MUST créer une configuration par défaut valide.
- **FR-010**: Le logiciel MUST conserver la migration automatique existante des anciennes configurations (`targets` + `routes` vers `connections`).
- **FR-011**: Le bouton Restart MUST redémarrer Mini-OSC sans script externe, en version empaquetée comme en version script.
- **FR-012**: Le logiciel MUST empêcher deux instances de tourner en même temps sur la même machine.
- **FR-013**: Un problème au démarrage (port occupé, configuration illisible) MUST être signalé à l'opérateur par un message compréhensible, et non par une fenêtre vide ou une fermeture silencieuse.
- **FR-014**: Le dépôt MUST produire automatiquement les quatre fichiers à chaque nouvelle version marquée, sans machine personnelle de chaque système.
- **FR-015**: Le lancement en script Python MUST continuer de fonctionner avec un `config.json` situé à côté du script, comme aujourd'hui.
- **FR-016**: La documentation MUST indiquer pour chaque système comment télécharger, ouvrir la première fois (avertissements de sécurité et pare-feu), et où se trouvent la configuration et les logs.
- **FR-017**: L'opérateur MUST pouvoir connaître l'emplacement du fichier de configuration utilisé (dans la documentation et dans les logs au démarrage).
- **FR-018** *(ajout du 2026-10-05)*: L'interface MUST afficher le chemin complet du fichier de configuration (onglet Servers) et du dossier des logs (onglet Logs), avec un bouton « Open folder » qui ouvre ce dossier dans le gestionnaire de fichiers. Ce bouton n'est proposé que sur la machine qui fait tourner Mini-OSC.
- **FR-019** *(ajout du 2026-10-05)*: L'opérateur MUST pouvoir exporter la configuration courante dans un fichier JSON de son choix.
- **FR-020** *(ajout du 2026-10-05)*: L'opérateur MUST pouvoir importer un fichier de configuration (nouveau ou ancien format). Le fichier est validé avant d'être appliqué, un fichier invalide est refusé sans rien modifier, la configuration précédente est sauvegardée dans `backups/`, puis Mini-OSC redémarre.
- **FR-021** *(ajout du 2026-10-05)*: L'icône macOS MUST s'afficher proprement sur macOS 26 (pas de cadre gris).

### Key Entities

- **Configuration**: le fichier `config.json` existant (serveurs, connexions, règles d'ignore, journalisation). Format inchangé. Seul son emplacement dépend du mode de lancement : dossier utilisateur en version empaquetée, dossier du script en version script.
- **Logs fichiers**: fichiers de journalisation avec rotation quotidienne existante. Même emplacement que la configuration selon le mode.
- **Version livrée**: un fichier par système (macOS, Windows, Linux) produit pour chaque version marquée du dépôt.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Sur une machine neuve sans Python, un opérateur passe du téléchargement à un Mini-OSC fonctionnel en moins de 2 minutes, avertissements de premier lancement compris.
- **SC-002**: Entre le double-clic et l'interface utilisable, il s'écoule moins de 10 secondes.
- **SC-003**: 100 % des types de connexions existants (OSC, HTTP, TCP, UDP, JSON, OSC vers OSC, réponse HTTP vers OSC) fonctionnent à l'identique dans la version empaquetée.
- **SC-004**: L'interface s'affiche complètement sur une machine sans internet, sur les quatre plateformes.
- **SC-005**: Aucune configuration n'est perdue après 10 cycles quitter/relancer et après le remplacement du fichier de l'application par une nouvelle version.
- **SC-006**: Une nouvelle version produit ses quatre fichiers sans intervention manuelle au-delà du marquage de la version.
- **SC-007**: Une installation script existante fonctionne sans changement de procédure après la mise à jour du code.

## Assumptions

- Les applications ne sont pas signées : les avertissements Gatekeeper (Mac) et SmartScreen (Windows) au premier lancement sont acceptés et documentés.
- La production automatique utilise le dépôt GitHub existant (`guigro/cogs-mini-osc`) et ses machines de build hébergées.
- Mac : deux fichiers séparés (Apple Silicon et Intel), chacun un `.app` distribué dans un `.dmg`, plutôt qu'un seul binaire universel plus fragile à produire.
- Linux : un fichier pour les PC x86_64 avec bureau.
- Raspberry Pi (Linux ARM) : hors périmètre pour cette version. Pourra être ajouté plus tard si besoin (build Linux arm64 sur Ubuntu 22.04, Pi OS 64 bits Bookworm ou plus).
- Le dépôt est public : les machines de build hébergées, Mac Intel compris, sont disponibles gratuitement.
- Le composant d'affichage web du système est présent : WebKit sur macOS, WebView2 sur Windows 10/11 (installé par défaut), WebKitGTK sur Linux.
- Le pare-feu du système demandera une autorisation au premier lancement, puisque le logiciel écoute sur le réseau. C'est attendu.
- Aucune mise à jour automatique n'est prévue : l'opérateur télécharge la nouvelle version et remplace l'ancienne.
- La conversion de la configuration de production de l'opérateur vers le nouveau format est un travail séparé, fait après cette fonctionnalité.
