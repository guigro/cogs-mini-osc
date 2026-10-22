# Feature Specification: Destination « Multiball » (API cloud LYMB.iO)

**Feature Branch**: `feature/multiball-api`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Nouveau type de destination « Multiball » qui pilote un mur Multiball (LYMB.iO) via son API cloud (https://multiball-admin.net/api/v1.0, authentification Basic clé API : jeton), pour que COGS puisse charger un jeu, le régler, lancer et arrêter une partie, et lire le statut du terrain avec de simples messages OSC sous un préfixe (/mb/start, /mb/switch, /mb/play, /mb/stop, /mb/status). Retour OSC optionnel vers COGS, formulaire dans l'interface web avec un bouton « Tester et lister » qui affiche les terrains et les jeux, aucun secret dans les logs ni dans le dépôt, appels réseau sans bloquer le serveur OSC, délai d'attente de 10 s par requête."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lancer une partie Multiball depuis COGS en un seul message (Priority: P1)

Le game master configure dans COGS un message OSC `/mb/start <gameId> [durée] [difficulté]`. Quand le scénario le déclenche, Mini-OSC charge le jeu sur le mur, applique le réglage s'il est fourni, attend que le jeu soit chargé, puis démarre la partie. Les joueurs n'attendent pas qu'un opérateur ouvre l'admin web Multiball.

**Why this priority**: c'est la raison d'être de la fonctionnalité. Sans elle, le lancement reste manuel.

**Independent Test**: avec une connexion Multiball configurée et un faux serveur d'API, envoyer `/mb/start <gameId>` et vérifier que les appels « charger le jeu » puis « démarrer » partent dans cet ordre, séparés du délai prévu, avec la bonne authentification.

**Acceptance Scenarios**:

1. **Given** une connexion Multiball avec le préfixe `/mb`, **When** COGS envoie `/mb/start 288b6480c62001f919d2736e`, **Then** Mini-OSC charge ce jeu sur le terrain configuré, attend le délai avant démarrage (3 s par défaut), puis démarre la partie, sans appel de réglage.
2. **Given** la même connexion, **When** COGS envoie `/mb/start 288b6480c62001f919d2736e 300 0.5`, **Then** Mini-OSC charge le jeu, envoie le réglage (durée 300 s, difficulté 0,5), attend le délai, puis démarre la partie.
3. **Given** le démarrage échoue une première fois (jeu pas encore prêt), **When** la séquence `start` est en cours, **Then** Mini-OSC retente le démarrage une seule fois après le même délai.
4. **Given** le chargement du jeu échoue (identifiants refusés, jeu inconnu), **When** la séquence `start` est en cours, **Then** la séquence s'arrête, aucun démarrage n'est tenté, et le message d'erreur renvoyé par l'API apparaît tel quel dans les logs.
5. **Given** une séquence `start` en pause avant le démarrage, **When** de nouveaux messages OSC arrivent sur Mini-OSC (y compris pour d'autres connexions), **Then** ils sont traités immédiatement, sans attendre la fin de la séquence.

---

### User Story 2 - Arrêter, charger, démarrer séparément et lire le statut (Priority: P1)

Le game master peut aussi envoyer des actions unitaires : `/mb/switch <gameId>` (charger seulement), `/mb/play [gameId]` (démarrer seulement), `/mb/stop [gameId]` (arrêter la partie), `/mb/status` (lire l'état du terrain). Sans gameId, `play` utilise le dernier jeu chargé et `stop` le dernier jeu lancé par cette connexion.

**Why this priority**: arrêter la partie en fin de session est aussi indispensable que la lancer.

**Independent Test**: envoyer `/mb/start <id>` puis `/mb/stop` sans argument et vérifier que l'arrêt vise bien le jeu lancé.

**Acceptance Scenarios**:

1. **Given** un jeu lancé par `/mb/start <id>`, **When** COGS envoie `/mb/stop`, **Then** Mini-OSC arrête la partie du jeu `<id>` sur le terrain configuré.
2. **Given** aucun jeu mémorisé (Mini-OSC vient de démarrer), **When** COGS envoie `/mb/stop`, **Then** Mini-OSC lit l'état du terrain, retrouve le jeu en cours et l'arrête ; s'il n'y en a pas, un message clair est écrit dans les logs et rien n'est arrêté.
3. **Given** un jeu chargé par `/mb/switch <id>`, **When** COGS envoie `/mb/play`, **Then** Mini-OSC démarre la partie du jeu `<id>`.
4. **Given** la connexion configurée, **When** COGS envoie `/mb/status`, **Then** Mini-OSC lit l'état du terrain et écrit dans les logs le statut et le nom du jeu en cours.
5. **Given** une action inconnue (`/mb/foo`) ou un gameId manquant (`/mb/switch` sans argument), **When** le message arrive, **Then** un message clair est écrit dans les logs et aucun appel n'est envoyé au mur.
6. **Given** une séquence `start` en pause avant le démarrage, **When** COGS envoie `/mb/stop` ou un nouveau `/mb/start`, **Then** la séquence en pause est abandonnée et ne démarre pas la partie.

---

### User Story 3 - Retour du résultat vers COGS (Priority: P2)

Après chaque action, Mini-OSC peut renvoyer à COGS un message OSC `<adresse> <action> <ok 1|0> <message>` (par exemple `/mb/result start 1 "Game started"`), à l'adresse IP, au port et à l'adresse OSC choisis dans la connexion. Pour `status`, le message contient le statut du terrain et le nom du jeu en cours. COGS peut ainsi réagir si le lancement échoue (afficher une alerte au game master, relancer, passer à un plan B).

**Why this priority**: très utile en exploitation, mais le lancement fonctionne sans.

**Independent Test**: activer le retour OSC vers un récepteur de test, envoyer `/mb/start` avec une API simulée qui refuse, et vérifier la réception de `/mb/result start 0 "<message d'erreur>"`.

**Acceptance Scenarios**:

1. **Given** le retour OSC activé, **When** une séquence `start` se termine avec succès, **Then** COGS reçoit `<adresse> start 1 <message>`.
2. **Given** le retour OSC activé, **When** une action échoue (API, réseau, argument manquant, action inconnue), **Then** COGS reçoit `<adresse> <action> 0 <message d'erreur>`.
3. **Given** le retour OSC activé, **When** COGS envoie `/mb/status`, **Then** COGS reçoit `<adresse> status 1 <statut> <nom du jeu> <gameId du jeu>`.
4. **Given** le retour OSC désactivé, **When** une action se termine, **Then** aucun message n'est renvoyé, seuls les logs sont écrits.

---

### User Story 4 - Configurer la connexion et retrouver les identifiants depuis l'interface (Priority: P2)

Dans l'onglet Connections, l'opérateur choisit la destination « Multiball (LYMB API) », saisit l'adresse de l'API, la clé API, le jeton (champ masqué), l'identifiant du terrain, le délai avant démarrage et le retour OSC optionnel. Un bouton « Test and list » interroge l'API avec la clé et le jeton saisis, affiche les terrains accessibles (un clic remplit l'identifiant du terrain) puis les jeux installés sur le terrain choisi (identifiant, nom, versions), avec un bouton pour copier chaque gameId. Un aide-mémoire sous le formulaire liste les messages OSC à créer dans COGS.

**Why this priority**: indispensable pour une configuration sans erreur, mais une configuration saisie à la main suffit pour lancer des parties.

**Independent Test**: avec une API simulée, cliquer « Test and list » et vérifier l'affichage des terrains puis des jeux, le remplissage de l'identifiant du terrain au clic, et l'affichage tel quel du message d'erreur de l'API en cas de mauvais identifiants.

**Acceptance Scenarios**:

1. **Given** une clé et un jeton valides saisis, **When** l'opérateur clique « Test and list », **Then** la liste des terrains s'affiche ; un clic sur un terrain remplit l'identifiant du terrain et affiche ses jeux installés.
2. **Given** des identifiants refusés, **When** l'opérateur clique « Test and list », **Then** le message de l'API (par exemple `Invalid api key!`) s'affiche tel quel.
3. **Given** une connexion Multiball existante en modification, **When** l'opérateur laisse le champ jeton vide, **Then** le jeton enregistré est conservé (pour l'enregistrement comme pour le test).
4. **Given** le type Multiball choisi, **When** le formulaire s'affiche, **Then** un aide-mémoire montre les messages OSC disponibles avec le préfixe saisi.

---

### User Story 5 - Les secrets ne fuient pas (Priority: P1)

Le jeton donne le contrôle du mur à quiconque le possède. Il ne doit apparaître ni dans les logs (écran et fichier), ni dans la configuration renvoyée à l'interface, ni dans le dépôt, et l'export de configuration ne l'inclut que si l'opérateur le demande explicitement.

**Why this priority**: une fuite du jeton (capture d'écran des logs, fichier de config partagé) permettrait de piloter le mur pendant que des clients jouent.

**Independent Test**: exécuter toutes les actions avec un jeton reconnaissable et vérifier qu'il n'apparaît dans aucun log, ni dans la configuration renvoyée à l'interface, ni dans l'export par défaut.

**Acceptance Scenarios**:

1. **Given** une connexion avec un jeton, **When** n'importe quelle action est exécutée (succès ou erreur), **Then** ni le jeton ni l'en-tête d'authentification n'apparaissent dans les logs.
2. **Given** une connexion avec un jeton, **When** l'interface lit la configuration, **Then** le jeton est remplacé par une indication « jeton enregistré » sans sa valeur.
3. **Given** une connexion avec un jeton, **When** l'opérateur exporte la configuration sans cocher l'option d'inclusion des secrets, **Then** le fichier exporté ne contient pas le jeton ; avec l'option cochée, un avertissement est affiché et le jeton est inclus.
4. **Given** un export sans jeton réimporté sur la même machine, **When** la configuration actuelle contient une connexion Multiball avec la même clé API, **Then** son jeton est conservé.

---

### Edge Cases

- Message sur le préfixe seul (`/mb` sans action) : message clair dans les logs, rien n'est envoyé.
- Durée à 0 ou vide : considérée comme « non fournie » (permet d'envoyer seulement une difficulté avec `/mb/start <id> 0 0.7`).
- Difficulté hors de l'intervalle 0 à 1, durée non numérique : erreur claire, aucun appel au mur.
- Réponse de l'API qui n'est pas du JSON ou délai dépassé (10 s) : erreur claire dans les logs et retour OSC `0`.
- Connexion sans clé, sans jeton ou sans identifiant de terrain : erreur claire « connexion incomplète », aucun appel.
- Deux connexions Multiball (deux murs) : chacune garde sa propre mémoire du dernier jeu.
- La connexion existante « OSC to Multiball » (`/multiball`, TCP) n'est pas concernée : le préfixe `/mb` ne capte pas `/multiball` (la correspondance se fait par segment d'adresse, pas par début de texte).
- Retour OSC activé mais IP ou port manquant : l'action s'exécute, une alerte est écrite dans les logs, aucun retour n'est envoyé.
- Mini-OSC redémarré : la mémoire du dernier jeu est perdue, `stop` se rabat sur la lecture de l'état du terrain.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Le système MUST proposer un nouveau type de destination « multiball » pour les connexions dont la source est OSC, avec les réglages : adresse de base de l'API (par défaut `https://multiball-admin.net/api/v1.0`), clé API, jeton, identifiant du terrain, délai avant démarrage (3 s par défaut) et retour OSC optionnel (IP, port, adresse).
- **FR-002**: Le préfixe de la connexion MUST fonctionner comme pour les destinations OSC : `<préfixe>/<action>` est accepté, l'action est le segment qui suit le préfixe. `<préfixe>suite` (sans `/`) ne correspond pas.
- **FR-003**: L'action `start <gameId> [durée] [difficulté]` MUST enchaîner : chargement du jeu, réglage seulement si une durée (> 0) ou une difficulté est fournie, pause du délai avant démarrage, démarrage ; en cas d'échec du démarrage, une seule nouvelle tentative après le même délai.
- **FR-004**: Les actions `switch <gameId>`, `play [gameId]`, `stop [gameId]` et `status` MUST effectuer respectivement le chargement, le démarrage, l'arrêt et la lecture de l'état du terrain.
- **FR-005**: Chaque connexion MUST mémoriser le dernier jeu chargé (par `switch` ou `start`) et le dernier jeu lancé (par `play` ou `start`) ; `play` sans gameId utilise le dernier jeu chargé, `stop` sans gameId le dernier jeu lancé ; à défaut, les deux se rabattent sur le jeu en cours lu sur le terrain.
- **FR-006**: Une action inconnue, un gameId manquant, un argument invalide ou une connexion incomplète MUST produire un message clair dans les logs et aucun appel vers le mur.
- **FR-007**: Un `stop`, `switch` ou nouveau `start` MUST annuler une séquence `start` de la même connexion qui n'a pas encore démarré la partie.
- **FR-008**: Chaque action MUST s'exécuter sans bloquer la réception des autres messages ; chaque requête vers l'API a un délai d'attente de 10 secondes.
- **FR-009**: Chaque requête MUST être journalisée avec sa méthode, son URL, son code de réponse et le début de la réponse ; les messages d'erreur de l'API (par exemple `Invalid api key!`, `authorization header missing`) MUST apparaître tels quels.
- **FR-010**: Le jeton et l'en-tête d'authentification MUST NOT apparaître dans les logs (écran et fichier).
- **FR-011**: Quand le retour OSC est activé, le système MUST envoyer après chaque action `<adresse> <action> <1|0> <message>`, et pour `status` : `<adresse> status 1 <statut> <nom du jeu> <gameId>`.
- **FR-012**: La configuration renvoyée à l'interface MUST masquer le jeton ; enregistrer une connexion avec un jeton vide MUST conserver le jeton déjà enregistré pour cette connexion.
- **FR-013**: L'export de configuration MUST exclure les jetons par défaut ; l'inclusion MUST être un choix explicite de l'opérateur accompagné d'un avertissement. L'import MUST accepter les connexions Multiball et récupérer le jeton de la configuration actuelle quand la clé API correspond et que le fichier importé n'en contient pas.
- **FR-014**: L'interface MUST proposer un bouton « Test and list » qui liste les terrains puis les jeux installés (identifiant, nom, versions), remplit l'identifiant du terrain au clic et permet de copier chaque gameId ; les messages d'erreur de l'API sont affichés tels quels. Ce bouton ne fait que des lectures.
- **FR-015**: L'interface MUST afficher un aide-mémoire des messages OSC disponibles sous le formulaire Multiball.
- **FR-016**: La validation de configuration, la migration de l'ancien format et toutes les connexions existantes (dont « OSC to Multiball » en TCP sur `/multiball`) MUST continuer de fonctionner sans changement.
- **FR-017**: La configuration par défaut livrée et les fichiers du dépôt MUST NOT contenir de clé ni de jeton.

### Key Entities

- **Connexion Multiball**: une connexion dont la source est un préfixe OSC et la destination un mur Multiball ; porte l'adresse de l'API, la clé API, le jeton, l'identifiant du terrain, le délai avant démarrage et le retour OSC optionnel.
- **Mémoire de connexion**: pour chaque connexion Multiball, le dernier jeu chargé, le dernier jeu lancé et la séquence `start` en cours éventuelle. Non persistée.
- **Terrain (court)**: un mur Multiball accessible avec la clé ; identifiant, nom, statut, jeu en cours.
- **Jeu**: un jeu installé sur un terrain ; identifiant, nom, nom affiché, versions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un seul message OSC envoyé par COGS suffit à charger et démarrer une partie, sans intervention humaine, en moins de délai avant démarrage + 10 secondes dans les conditions normales.
- **SC-002**: Pendant une séquence `start` (pause comprise), les autres messages OSC reçus sont routés sans retard perceptible (moins de 100 ms ajoutés).
- **SC-003**: Le jeton n'apparaît dans aucune ligne de log, ni dans la configuration lue par l'interface, ni dans l'export par défaut, vérifié par des tests automatiques.
- **SC-004**: Un opérateur qui dispose seulement d'une clé et d'un jeton retrouve l'identifiant de son terrain et de ses jeux en moins d'une minute depuis l'interface.
- **SC-005**: 100 % des tests existants passent toujours, et la connexion existante `/multiball` (TCP) reste routée exactement comme avant.
- **SC-006**: Chaque échec (identifiants, réseau, jeu inconnu, argument invalide) produit un message lisible dans les logs et, si le retour est activé, un `0` reçu par COGS.

## Assumptions

- Seules les sources OSC sont prises en charge pour cette destination (comme pour la destination JSON) ; c'est le seul besoin exprimé.
- `versionNumber` est toujours envoyé à `null` (version actuelle du terrain) ; choisir une version précise n'est pas demandé. L'« asset flip » n'est pas couvert.
- La clé API n'est pas considérée comme secrète à elle seule (c'est l'équivalent d'un nom d'utilisateur) : elle reste visible dans l'interface et dans l'export ; seul le jeton est masqué.
- Les tests automatiques simulent l'API ; aucun appel réel ne change l'état du mur pendant le développement. Les lectures réelles (`courts`, `games`) ne sont faites que si l'utilisateur fournit sa clé pour un test.
- En mode script (`python mini_osc.py`), la configuration est enregistrée dans `config.json` du dossier du projet, qui est suivi par git : saisir un jeton dans ce mode l'écrit dans un fichier du dépôt. L'application de bureau, elle, enregistre dans le dossier utilisateur. Ce point sera rappelé dans la documentation.
- Le délai avant démarrage accepte des valeurs décimales de 0 à 60 secondes.
