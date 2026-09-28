import click, copy
from Site.code.airspy.database import default_stats, update_organization_stats, get_global_stats_row, set_global_stats_row
from Site.code.airspy.utility import get_games_updated_after_cutoff
from Site.code.database.main import get_matching_row, get_property_value

SERIES_GROUPS = {
    "timestamps": ["playerCounts", "plays", "plays24h", "uniquePlays24h"],
    "dailyTimestamps": ["dailyPlayerCounts", "dailyPlays", "dailyPlays24h", "dailyUniquePlays24h"],
    "monthlyTimestamps": ["monthlyPlayerCounts", "monthlyPlays", "monthlyPlays24h", "monthlyUniquePlays24h"],
}

ATH_SOURCES = [
    ("athPlayerCount", "athPlayerCountAt", [("playerCounts", "timestamps")]),
    ("athPlays24h", "athPlays24hAt", [("plays24h", "timestamps"), ("dailyPlays24h", "dailyTimestamps"), ("monthlyPlays24h", "monthlyTimestamps")]),
    ("athUniquePlays24h", "athUniquePlays24hAt", [("uniquePlays24h", "timestamps"), ("dailyUniquePlays24h", "dailyTimestamps"), ("monthlyUniquePlays24h", "monthlyTimestamps")]),
]

def combine_stats(stats_list, previous=None):
    """Sum gameStats/orgStats dicts into one, aligning series from the newest end
    (a point stays -1 only if no input had data). All-time highs come from the
    combined series, or from `previous` when higher; pass None to rebuild them."""
    combined = copy.deepcopy(default_stats)
    for timestamp_key, value_keys in SERIES_GROUPS.items():
        length = max([len(s[timestamp_key]) for s in stats_list] + [len(combined[timestamp_key])])
        timestamps = [None] * length
        for s in stats_list:
            offset = length - len(s[timestamp_key])
            for idx, timestamp in enumerate(s[timestamp_key]):
                if timestamps[offset + idx] is None:
                    timestamps[offset + idx] = timestamp
        combined[timestamp_key] = timestamps

        for value_key in value_keys:
            totals = [-1] * length
            for s in stats_list:
                offset = length - len(s[value_key])
                for idx, value in enumerate(s[value_key]):
                    if value == -1:
                        continue
                    totals[offset + idx] = value if totals[offset + idx] == -1 else totals[offset + idx] + value
            combined[value_key] = totals

    for ath_key, ath_at_key, sources in ATH_SOURCES:
        best, best_at = 0, None
        if previous:
            best, best_at = previous.get(ath_key, 0), previous.get(ath_at_key)
        for values_key, timestamps_key in sources:
            for value, timestamp in zip(combined[values_key], combined[timestamps_key]):
                if value > best:
                    best, best_at = value, timestamp
        combined[ath_key] = best
        combined[ath_at_key] = best_at

    return combined

def compile_organization_stats(organization_id, keep_ath=True, cutoff=None):
    """Rebuild an organization's stats from its publicly shown games: not hidden
    from Airspy and not last updated before the admin 'updated after' cutoff."""
    organization = get_matching_row("organization", {"id": organization_id})
    if not organization:
        return
    games = get_matching_row("game", {"organizationId": organization_id, "hiddenFromAirspy": False}, multiple=True)
    stats = combine_stats(
        [game["gameStats"] for game in games if game["gameStats"] and not (cutoff and game["lastVersionUpdate"] < cutoff)],
        previous=organization["orgStats"] if keep_ath else None
    )
    update_organization_stats(organization_id, stats)

def compile_global_stats(keep_ath=True):
    """Rebuild the global stats by combining every organization that isn't hidden from Airspy."""
    organizations = get_matching_row("organization", {"hiddenFromAirspy": False}, multiple=True)
    stats = combine_stats(
        [organization["orgStats"] for organization in organizations if organization["orgStats"]],
        previous=get_global_stats_row() if keep_ath else None
    )
    set_global_stats_row(stats)
    return stats

def get_global_stats_data():
    return get_global_stats_row() or compile_global_stats()

def compile_all_stats(keep_ath=True):
    """Rebuild every organization's stats and the global stats from the raw game data."""
    organization_ids = get_property_value("organization", "id")
    cutoff = get_games_updated_after_cutoff()
    for organization_id in organization_ids:
        compile_organization_stats(organization_id, keep_ath, cutoff)
    compile_global_stats(keep_ath)
    return len(organization_ids)

def recompile_after_visibility_change(organization_id):
    """A game or organization was hidden/unhidden, so its old all-time highs may
    be wrong - rebuild them from the stored history too."""
    compile_organization_stats(organization_id, keep_ath=False, cutoff=get_games_updated_after_cutoff())
    compile_global_stats(keep_ath=False)

@click.command('recompile-airspy-stats')
def recompile_airspy_stats_command():
    count = compile_all_stats(keep_ath=False)
    click.echo(f'Recompiled stats for {count} organizations and the global stats.')
