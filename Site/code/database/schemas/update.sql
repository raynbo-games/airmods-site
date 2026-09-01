UPDATE "game"
SET "gameStats" = "gameStats" || jsonb_build_object(
	'timestamps', to_jsonb(array_fill(NULL::text, ARRAY[jsonb_array_length("gameStats"->'playerCounts')])),
	'dailyTimestamps', to_jsonb(array_fill(NULL::text, ARRAY[jsonb_array_length("gameStats"->'dailyPlayerCounts')])),
	'monthlyTimestamps', to_jsonb(array_fill(NULL::text, ARRAY[jsonb_array_length("gameStats"->'monthlyPlayerCounts')])),
	'athPlayerCountAt', 'null'::jsonb,
	'athPlays24hAt', 'null'::jsonb,
	'athUniquePlays24hAt', 'null'::jsonb
)
WHERE NOT ("gameStats" ? 'timestamps');

UPDATE "organization"
SET "orgStats" = "orgStats" || jsonb_build_object(
	'timestamps', to_jsonb(array_fill(NULL::text, ARRAY[jsonb_array_length("orgStats"->'playerCounts')])),
	'dailyTimestamps', to_jsonb(array_fill(NULL::text, ARRAY[jsonb_array_length("orgStats"->'dailyPlayerCounts')])),
	'monthlyTimestamps', to_jsonb(array_fill(NULL::text, ARRAY[jsonb_array_length("orgStats"->'monthlyPlayerCounts')])),
	'athPlayerCountAt', 'null'::jsonb,
	'athPlays24hAt', 'null'::jsonb,
	'athUniquePlays24hAt', 'null'::jsonb
)
WHERE NOT ("orgStats" ? 'timestamps');

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "notes" TEXT;

ALTER TABLE "roadmap_box_comment" ADD COLUMN IF NOT EXISTS "parentCommentId" INTEGER;
ALTER TABLE "roadmap_box_comment" ADD COLUMN IF NOT EXISTS "deleted" BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE "comment" ADD COLUMN IF NOT EXISTS "parentCommentId" INTEGER;
