from fastapi import APIRouter, HTTPException
from enum import Enum
import sqlalchemy
from src import database as db
from sqlalchemy import extract
import urllib.parse

router = APIRouter()


class team_options(str, Enum):
    toronto_raptors = "Toronto Raptors"
    memphis_grizzlies = "Memphis Grizzlies"
    miami_heat = "Miami Heat"
    utah_jazz = "Utah Jazz"
    milwaukee_bucks = "Milwaukee Bucks"
    cleveland_cavaliers = "Cleveland Cavaliers"
    new_orleans_pelicans = "New Orleans Pelicans"
    minnesota_timberwolves = "Minnesota Timberwolves"
    orlando_magic = "Orlando Magic"
    new_york_knicks = "New York Knicks"
    washington_wizards = "Washington Wizards"
    phoenix_suns = "Phoenix Suns"
    detroit_pistons = "Detroit Pistons"
    golden_state_warriors = "Golden State Warriors"
    charlotte_hornets = "Charlotte Hornets"
    san_antonio_spurs = "San Antonio Spurs"
    sacramento_kings = "Sacramento Kings"
    los_angeles_clippers = "Los Angeles Clippers"
    oklahoma_city_thunder = "Oklahoma City Thunder"
    dallas_mavericks = "Dallas Mavericks"
    los_angeles_lakers = "Los Angeles Lakers"
    indiana_pacers = "Indiana Pacers"
    atlanta_hawks = "Atlanta Hawks"
    chicago_bulls = "Chicago Bulls"
    denver_nuggets = "Denver Nuggets"
    boston_celtics = "Boston Celtics"
    portland_trail_blazers = "Portland Trail Blazers"
    philadelphia_76ers = "Philadelphia 76ers"
    houston_rockets = "Houston Rockets"
    brooklyn_nets = "Brooklyn Nets"


def get_team_helper(conn, team_id, year):
    games = sqlalchemy.select(db.games.c.home,
                              db.games.c.away,
                              db.games.c.pts_home,
                              db.games.c.pts_away).where((
                                                                 (db.games.c.home == team_id) |
                                                                 (db.games.c.away == team_id)) & (
                                                                     ((extract("year", db.games.c.date) == year) &
                                                                      (extract("month", db.games.c.date) < 10)) |
                                                                     ((extract("year", db.games.c.date) == year - 1) &
                                                                      (extract("month", db.games.c.date) >= 10))))

    games_table = conn.execute(games).fetchall()

    wins = points_for = points_allowed = losses = 0

    for row in games_table:
        winner = row.home if row.pts_home > row.pts_away else row.away
        if winner == team_id:
            wins += 1
        else:
            losses += 1
        if team_id == row.home:
            points_for += row.pts_home
            points_allowed += row.pts_away
        elif team_id == row.away:
            points_for += row.pts_away
            points_allowed += row.pts_home

    games_played = wins + losses
    stats = {"season": year, "wins": wins, "losses": losses,
             "average points for": round((points_for / games_played), 2),
             "average points allowed": round((points_allowed / games_played), 2)}

    return stats


@router.get("/teams/{team_id}", tags=["teams"])
def get_team(team_id: int,
             year: int = None
             ):
    """
    This endpoint returns a single team by its identifier. For each team it returns:
    *`team_id`: The internal id of the team
    *`team_name`: The name of the team
    *`Wins`: Number of games the team won
    *`Losses`: Number of games the team lost
    *`Average Points for`: Average number of points the team scored
    *`Average Points allowed`: Average number of points team allowed
    """

    if year and not (2019 <= year <= 2023):
        raise HTTPException(status_code=400, detail="please enter a year within 2019 to 2023 (inclusive)")

    team = sqlalchemy.select(db.teams.c.team_id, db.teams.c.team_name, db.teams.c.team_abbrev).where(
        db.teams.c.team_id == team_id)

    with db.engine.begin() as conn:
        result = conn.execute(team).fetchone()
        team_name = result.team_name

        if not result:
            raise HTTPException(status_code=404, detail="team not found.")

        if year:
            stats = [get_team_helper(conn, team_id, year)]
        else:
            stats1 = get_team_helper(conn, team_id, 2019)
            stats2 = get_team_helper(conn, team_id, 2020)
            stats3 = get_team_helper(conn, team_id, 2021)
            stats4 = get_team_helper(conn, team_id, 2022)
            stats5 = get_team_helper(conn, team_id, 2023)
            stats = [stats1, stats2, stats3, stats4, stats5]

        json = {"team_id": team_id, "team_name": team_name, "team_stats": stats}

        return json


class stat_options(str, Enum):
    points = "points"
    rebounds = "rebounds"
    assists = "assists"
    steals = "steals"
    blocks = "blocks"


@router.get("/teams/", tags=["teams"])
def compare_team(team_1: int,
                 team_2: int,
                 team_3: int = None,
                 team_4: int = None,
                 team_5: int = None,
                 compare_by: stat_options = stat_options.points):
    """
    This endpoint compares between up to 5 teams by a single metric
    * `team_i`: the id of a team to be compared
    * `Compare_by` must be one of the following values
        * `points`: The average points per game
        * `rebounds`: The average rebounds per game
        * `assists`: The average assists per game
        * `steals`: The average steals per game
        * `blocks`: The average blocks per game
    """
    num_ssn_games = 82

    teams_to_compare = (
        sqlalchemy.select(db.teams.c.team_id, db.teams.c.team_name)
        .where(sqlalchemy.column('team_id').in_([team_1, team_2, team_3, team_4, team_5]))
    )

    games_query = (
        sqlalchemy.select(
            db.teams.c.team_id,
            db.teams.c.team_name,
            sqlalchemy.func.sum(sqlalchemy.case((db.games.c.home == db.teams.c.team_id, db.games.c.pts_home),
                                                else_=db.games.c.pts_away)).label('points'),

            sqlalchemy.func.sum(sqlalchemy.case((db.games.c.home == db.teams.c.team_id, db.games.c.reb_home),
                                                else_=db.games.c.reb_away)).label('rebounds'),

            sqlalchemy.func.sum(sqlalchemy.case((db.games.c.home == db.teams.c.team_id, db.games.c.ast_home),
                                                else_=db.games.c.ast_away)).label('assists'),

            sqlalchemy.func.sum(sqlalchemy.case((db.games.c.home == db.teams.c.team_id, db.games.c.stl_home),
                                                else_=db.games.c.stl_away)).label('steals'),

            sqlalchemy.func.sum(sqlalchemy.case((db.games.c.home == db.teams.c.team_id, db.games.c.blk_home),
                                                else_=db.games.c.blk_away)).label('blocks'),
            sqlalchemy.func.count().label('games_played')
        )
        .select_from(db.teams.join(db.games, sqlalchemy.or_(db.teams.c.team_id == db.games.c.home, db.teams.c.team_id == db.games.c.away)))
        .where(sqlalchemy.column('team_id').in_([team_1, team_2, team_3, team_4, team_5]))
        .group_by(db.teams.c.team_id, db.teams.c.team_name)
    )

    with db.engine.begin() as conn:
        result = conn.execute(teams_to_compare).fetchall()
        teams_data = {row.team_id: {'team_name': row.team_name} for row in result}

        games_result = conn.execute(games_query).fetchall()
        for row in games_result:
            team_id = row.team_id
            teams_data[team_id][str(compare_by.value)] = round(
                getattr(row, compare_by.value) / (num_ssn_games * row.games_played), 3)

        sorted_teams = sorted(teams_data.values(), key=lambda x: -x[compare_by.value])
        return sorted_teams
