DROP TABLE IF EXISTS game;
DROP TABLE IF EXISTS organization;

CREATE TABLE game (
	id TEXT PRIMARY KEY UNIQUE,
	slug TEXT,
	slugProperCase TEXT,
	name TEXT NOT NULL,
	description TEXT NOT NULL,
	iconImageId TEXT,
	organizationId TEXT NOT NULL,
	createdAt TIMESTAMP NOT NULL,
	visibility TEXT NOT NULL,
	lastVersionUpdate TIMESTAMP NOT NULL,
	archivedAt TIMESTAMP,
	loadingScreenImageId TEXT,
	logoImageId TEXT,
	videoId TEXT,
	links JSON NOT NULL,
	plays INT NOT NULL,
	favorites INT NOT NULL,
	plays24h INT NOT NULL,
	uniquePlays24h INT NOT NULL,
	platforms JSON NOT NULL,
	liveStats JSON NOT NULL,
	gameStats JSON NOT NULL
);

CREATE TABLE organization (
	id TEXT PRIMARY KEY UNIQUE,
	slug TEXT NOT NULL,
	slugProperCase TEXT NOT NULL,
	name TEXT NOT NULL,
	description TEXT NOT NULL,
	iconImageId TEXT NOT NULL,
	createdAt TIMESTAMP NOT NULL,
	adminBanned BOOLEAN NOT NULL,
	orgStats JSON NOT NULL
);