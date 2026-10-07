import sys
import mysql.connector
from pathlib import Path

import queries

TEST_DB = 'bibinatorTestDB'

FIXTURE_PATH = Path(__file__).parent.parent.parent / 'data' / 'test_fixture.sql'
_SETUP_DIR = str(Path(__file__).parent.parent / 'setup')

sys.modules.pop('_config', None)
sys.path.insert(0, _SETUP_DIR)
import full_pipeline  # type: ignore
sys.path.remove(_SETUP_DIR)
del sys.modules['_config']

from _config import DB_CONFIG


def _connect(database=None):
    cfg = {**DB_CONFIG}
    if database:
        cfg['database'] = database
    else:
        cfg.pop('database', None)
    return mysql.connector.connect(**cfg)


class _TestFailure(Exception):
    pass


def _assert(condition, msg):
    if not condition:
        print(f'\n  \033[31m[FAIL]\033[0m {msg}')
        raise _TestFailure()


def _fetch(cursor, query, params=()):
    cursor.execute(query, params)
    return cursor.fetchall()


def _fetchone(cursor, query, params=()):
    cursor.execute(query, params)
    return cursor.fetchone()



##############
### TESTS ####
##############

def test_quick_stats(cursor):
    print('QUICK_STATS:'.ljust(30), end='')
    row = _fetchone(cursor, queries.QUICK_STATS)
    _assert(row is not None, 'returns a row')
    n_conf, n_mag, n_papers, n_authors, min_yr, max_yr = row

    _assert(0 <= n_conf <= 6, f'number of conferences: expected ~3 (got {n_conf})')
    _assert(0 <= n_mag <= 6, f'number of journals: expected ~3 (got {n_mag})')
    _assert(0 <= n_papers <= 20, f'number of papers: expected ~10 (got {n_papers})')
    _assert(0 <= n_authors <= 8, f'number of authors: expected ~4 (got {n_authors})')
    _assert(min_yr == 2010 and max_yr == 2012, f'year range: expected 2010-2012, got {min_yr}-{max_yr}')

    print(f'\033[32m[PASS]\033[0m')


def test_venue_stats_conf(cursor):
    print('VENUE_STATS_CONF:'.ljust(30), end='')
    rows = _fetch(cursor, queries.VENUE_STATS_CONF, ('%C1%', '%C1%', 2010, 2012))
    _assert(len(rows) == 1, 'conf1 has data for one year')
    year, num_papers, total_authors, distinct_authors = rows[0]

    _assert(year == 2010, f'year is 2010 (got {year})')
    _assert(num_papers == 2, f'number of papers: expected 2, got {num_papers}')
    _assert(total_authors == 3, f'total author slots: expected 3, got {total_authors}')
    _assert(distinct_authors == 2, f'distinct authors: expected 2, got {distinct_authors}')

    rows = _fetch(cursor, queries.VENUE_STATS_CONF, ('%Unknown%', '%Unknown%', 2010, 2012))
    _assert(len(rows) == 0, f'unknown venue returns no rows (got {len(rows)})')

    print(f'\033[32m[PASS]\033[0m')


def test_venue_stats_mag(cursor):
    print('VENUE_STATS_MAG:'.ljust(30), end='')
    rows = _fetch(cursor, queries.VENUE_STATS_MAG, ('%Journal 1%', 2010, 2012))
    _assert(len(rows) == 2, f'journal1 has data for two years (got {len(rows)})')
    year, num_papers, total_authors, distinct_authors = rows[0]

    _assert(year == 2010, f'first year is 2010 (got {year})')
    _assert(num_papers == 1, f'number of papers in 2010: expected 1, got {num_papers}')
    _assert(total_authors == 2, f'total author slots in 2010: expected 2, got {total_authors}')
    _assert(distinct_authors == 2, f'distinct authors in 2010: expected 2, got {distinct_authors}')

    year, num_papers, total_authors, distinct_authors = rows[1]
    _assert(year == 2011, f'second year is 2011 (got {year})')
    _assert(num_papers == 1, f'number of papers in 2011: expected 1, got {num_papers}')
    _assert(total_authors == 1, f'total author slots in 2011: expected 1, got {total_authors}')
    _assert(distinct_authors == 1, f'distinct authors in 2011: expected 1, got {distinct_authors}')

    rows = _fetch(cursor, queries.VENUE_STATS_MAG, ('%Unknown%', 2010, 2012))
    _assert(len(rows) == 0, f'unknown journal returns no rows (got {len(rows)})')
    
    print(f'\033[32m[PASS]\033[0m')


def test_venue_papers_conf(cursor):
    print('VENUE_PAPERS_CONF:'.ljust(30), end='')
    rows = _fetch(cursor, queries.VENUE_PAPERS_CONF, ('%C1%', '%C1%', 2010, 2012))
    _assert(len(rows) == 2, f'conf1 has 2 papers (got {len(rows)})')

    ids = {row[0] for row in rows}
    _assert(ids == {1, 2}, f'article IDs: expected {{1, 2}}, got {ids}')
    _assert(all(row[3] == 2010 for row in rows), 'all papers are from 2010')

    rows = _fetch(cursor, queries.VENUE_PAPERS_CONF, ('%Unknown%', '%Unknown%', 2010, 2012))
    _assert(len(rows) == 0, f'unknown venue returns no rows (got {len(rows)})')

    print(f'\033[32m[PASS]\033[0m')


def test_venue_papers_mag(cursor):
    print('VENUE_PAPERS_MAG:'.ljust(30), end='')
    rows = _fetch(cursor, queries.VENUE_PAPERS_MAG, ('%Journal 1%', 2010, 2012))
    _assert(len(rows) == 2, f'journal1 has 2 papers (got {len(rows)})')

    ids = {row[0] for row in rows}
    _assert(ids == {6, 7}, f'article IDs: expected {{6, 7}}, got {ids}')
    years = {row[3] for row in rows}
    _assert(years == {2010, 2011}, f'years: expected {{2010, 2011}}, got {years}')

    rows = _fetch(cursor, queries.VENUE_PAPERS_MAG, ('%Unknown%', 2010, 2012))
    _assert(len(rows) == 0, f'unknown journal returns no rows (got {len(rows)})')

    print(f'\033[32m[PASS]\033[0m')


def test_author_activity(cursor):
    print('AUTHOR_ACTIVITY:'.ljust(30), end='')
    rows = _fetch(cursor, queries.AUTHOR_ACTIVITY, ('author1', 'author1'))
    _assert(len(rows) == 2, f'author1 has activity in two years (got {len(rows)})')

    year, conf_papers, journal_papers = rows[0]
    _assert(year == 2010, f'first year is 2010 (got {year})')
    _assert(conf_papers == 2, f'conference papers in 2010: expected 2, got {conf_papers}')
    _assert(journal_papers == 1, f'journal papers in 2010: expected 1, got {journal_papers}')

    year, conf_papers, journal_papers = rows[1]
    _assert(year == 2011, f'second year is 2011 (got {year})')
    _assert(conf_papers == 0, f'conference papers in 2011: expected 0, got {conf_papers}')
    _assert(journal_papers == 1, f'journal papers in 2011: expected 1, got {journal_papers}')

    rows = _fetch(cursor, queries.AUTHOR_ACTIVITY, ('unknown_author', 'unknown_author'))
    _assert(len(rows) == 0, f'unknown author returns no rows (got {len(rows)})')

    print(f'\033[32m[PASS]\033[0m')


def test_year_stats(cursor):
    print('YEAR_STATS:'.ljust(30), end='')
    row = _fetchone(cursor, queries.YEAR_STATS, (2010, 2010, 2010, 2010))
    _assert(row is not None, 'returns a row for year 2010')

    num_papers, num_conf, num_journals, num_authors, num_distinct_authors = row
    _assert(num_papers == 5, f'total papers in 2010: expected 5, got {num_papers}')
    _assert(num_conf == 2, f'active conferences in 2010: expected 2, got {num_conf}')
    _assert(num_journals == 2, f'active journals in 2010: expected 2, got {num_journals}')
    _assert(num_authors == 7, f'total author slots in 2010: expected 7, got {num_authors}')
    _assert(num_distinct_authors == 4, f'distinct authors in 2010: expected 4, got {num_distinct_authors}')

    row = _fetchone(cursor, queries.YEAR_STATS, (9999, 9999, 9999, 9999))
    num_papers, num_conf, num_journals, num_authors, num_distinct_authors = row
    _assert(num_papers == 0, f'year with no data has 0 papers (got {num_papers})')
    _assert(num_distinct_authors == 0, f'year with no data has 0 distinct authors (got {num_distinct_authors})')

    print(f'\033[32m[PASS]\033[0m')


def test_year_papers(cursor):
    print('YEAR_PAPERS:'.ljust(30), end='')
    no_filter = (2010, None, None, None, None, None, 2010, None, None, None, None, None, None)
    rows = _fetch(cursor, queries.YEAR_PAPERS, no_filter)
    _assert(len(rows) == 5, f'2010 has 5 papers with no filters (got {len(rows)})')

    conf_filter = (2010, None, None, None, None, None, 2010, None, None, None, None, 'conference', 'conference')
    rows = _fetch(cursor, queries.YEAR_PAPERS, conf_filter)
    _assert(len(rows) == 3, f'2010 has 3 conference papers (got {len(rows)})')

    journal_filter = (2010, None, None, None, None, None, 2010, None, None, None, None, 'journal', 'journal')
    rows = _fetch(cursor, queries.YEAR_PAPERS, journal_filter)
    _assert(len(rows) == 2, f'2010 has 2 journal papers (got {len(rows)})')

    print(f'\033[32m[PASS]\033[0m')



def test_venue_rank_conf(cursor):
    print('VENUE_RANK_CONF:'.ljust(30), end='')
    row = _fetchone(cursor, queries.VENUE_RANK_CONF, ('%C1%', '%C1%'))
    _assert(row is not None, 'conf1 returns a row')
    _assert(row[0] == 'A*', f'conf1 rank is A* (got {row[0]})')

    row = _fetchone(cursor, queries.VENUE_RANK_CONF, ('%C3%', '%C3%'))
    _assert(row is not None, 'conf3 returns a row')
    _assert(row[0] == 'unranked', f'conf3 rank is unranked (got {row[0]})')

    row = _fetchone(cursor, queries.VENUE_RANK_CONF, ('%Unknown%', '%Unknown%'))
    _assert(row is None, f'unknown venue returns no row (got {row})')

    print(f'\033[32m[PASS]\033[0m')


def test_venue_rank_mag(cursor):
    print('VENUE_RANK_MAG:'.ljust(30), end='')
    row = _fetchone(cursor, queries.VENUE_RANK_MAG, ('%Journal 1%',))
    _assert(row is not None, 'journal1 returns a row')
    _assert(row[0] == 'Q1', f'journal1 rank is Q1 (got {row[0]})')

    row = _fetchone(cursor, queries.VENUE_RANK_MAG, ('%Journal 3%',))
    _assert(row is not None, 'journal3 returns a row')
    _assert(row[0] is None, f'journal3 has NULL quartile (got {row[0]})')

    row = _fetchone(cursor, queries.VENUE_RANK_MAG, ('%Unknown%',))
    _assert(row is None, f'unknown journal returns no row (got {row})')

    print(f'\033[32m[PASS]\033[0m')


def test_venue_distinct_authors_conf(cursor):
    print('VENUE_DISTINCT_AUTHORS_CONF:'.ljust(30), end='')
    row = _fetchone(cursor, queries.VENUE_DISTINCT_AUTHORS_CONF, ('%C1%', '%C1%', 2010, 2012))
    _assert(row[0] == 2, f'conf1 has 2 distinct authors over 2010-2012 (got {row[0]})')

    row = _fetchone(cursor, queries.VENUE_DISTINCT_AUTHORS_CONF, ('%Unknown%', '%Unknown%', 2010, 2012))
    _assert(row[0] == 0, f'unknown venue has 0 distinct authors (got {row[0]})')

    print(f'\033[32m[PASS]\033[0m')


def test_venue_distinct_authors_mag(cursor):
    print('VENUE_DISTINCT_AUTHORS_MAG:'.ljust(30), end='')
    row = _fetchone(cursor, queries.VENUE_DISTINCT_AUTHORS_MAG, ('%Journal 1%', 2010, 2012))
    _assert(row[0] == 3, f'journal1 has 3 distinct authors over 2010-2012 (got {row[0]})')

    row = _fetchone(cursor, queries.VENUE_DISTINCT_AUTHORS_MAG, ('%Unknown%', 2010, 2012))
    _assert(row[0] == 0, f'unknown journal has 0 distinct authors (got {row[0]})')

    print(f'\033[32m[PASS]\033[0m')



def test_venue_year_range_conf(cursor):
    print('VENUE_YEAR_RANGE_CONF:'.ljust(30), end='')
    row = _fetchone(cursor, queries.VENUE_YEAR_RANGE_CONF, ('%C1%', '%C1%'))
    _assert(row[0] == 2010 and row[1] == 2010, f'conf1 year range: expected 2010-2010, got {row[0]}-{row[1]}')

    row = _fetchone(cursor, queries.VENUE_YEAR_RANGE_CONF, ('%C2%', '%C2%'))
    _assert(row[0] == 2011 and row[1] == 2012, f'conf2 year range: expected 2011-2012, got {row[0]}-{row[1]}')

    row = _fetchone(cursor, queries.VENUE_YEAR_RANGE_CONF, ('%Unknown%', '%Unknown%'))
    _assert(row[0] is None and row[1] is None, f'unknown venue returns NULL year range (got {row})')

    print(f'\033[32m[PASS]\033[0m')


def test_venue_year_range_mag(cursor):
    print('VENUE_YEAR_RANGE_MAG:'.ljust(30), end='')
    row = _fetchone(cursor, queries.VENUE_YEAR_RANGE_MAG, ('%Journal 1%',))
    _assert(row[0] == 2010 and row[1] == 2011, f'journal1 year range: expected 2010-2011, got {row[0]}-{row[1]}')

    row = _fetchone(cursor, queries.VENUE_YEAR_RANGE_MAG, ('%Unknown%',))
    _assert(row[0] is None and row[1] is None, f'unknown journal returns NULL year range (got {row})')

    print(f'\033[32m[PASS]\033[0m')


def test_venue_trend(cursor):
    print('VENUE_TREND:'.ljust(30), end='')
    sql = queries.venue_trend('num_papers', 'conference')
    rows = _fetch(cursor, sql, ('%C1%', '%C1%', 2010, 2012))
    _assert(len(rows) == 1, f'conference trend for conf1 returns 1 row (got {len(rows)})')
    year, num_papers, _, _ = rows[0]
    _assert(year == 2010 and num_papers == 2, f'conf1 2010: expected 2 papers (got year={year}, papers={num_papers})')

    sql = queries.venue_trend('num_papers', 'journal')
    rows = _fetch(cursor, sql, ('%Journal 1%', 2010, 2012))
    _assert(len(rows) == 2, f'journal trend for journal1 returns 2 rows (got {len(rows)})')

    print(f'\033[32m[PASS]\033[0m')


def test_venue_aggregate(cursor):
    print('VENUE_AGGREGATE:'.ljust(30), end='')
    sql = queries.venue_aggregate('conference')
    row = _fetchone(cursor, sql, ('%C1%', '%C1%'))
    total_papers, avg_papers, avg_authors = row
    _assert(total_papers == 2, f'conf1 total papers: expected 2, got {total_papers}')
    _assert(float(avg_papers) == 2.0, f'conf1 avg papers per year: expected 2.0, got {avg_papers}')
    _assert(float(avg_authors) == 3.0, f'conf1 avg authors per year: expected 3.0, got {avg_authors}')

    sql = queries.venue_aggregate('journal')
    row = _fetchone(cursor, sql, ('%Journal 1%',))
    total_papers, avg_papers, avg_authors = row
    _assert(total_papers == 2, f'journal1 total papers: expected 2, got {total_papers}')
    _assert(float(avg_papers) == 1.0, f'journal1 avg papers per year: expected 1.0, got {avg_papers}')
    _assert(float(avg_authors) == 1.5, f'journal1 avg authors per year: expected 1.5, got {avg_authors}')

    print(f'\033[32m[PASS]\033[0m')


def test_quartile_dist(cursor):
    print('QUARTILE_DIST:'.ljust(30), end='')
    rows = _fetch(cursor, queries.QUARTILE_DIST)
    _assert(len(rows) == 2, f'returns 2 quartile groups (got {len(rows)})')
    _assert(rows[0] == ('Q1', 1), f'Q1 has 1 journal (got {rows[0]})')
    _assert(rows[1] == ('Q2', 1), f'Q2 has 1 journal (got {rows[1]})')

    print(f'\033[32m[PASS]\033[0m')


def test_publisher_quartile(cursor):
    print('PUBLISHER_QUARTILE:'.ljust(30), end='')
    rows = _fetch(cursor, queries.PUBLISHER_QUARTILE, (None, None))
    _assert(len(rows) == 2, f'returns 2 publisher-quartile groups with no filter (got {len(rows)})')
    _assert(rows[0] == ('publisher1', 'Q1', 1), f'publisher1 Q1: expected 1 journal (got {rows[0]})')
    _assert(rows[1] == ('publisher2', 'Q2', 1), f'publisher2 Q2: expected 1 journal (got {rows[1]})')

    rows = _fetch(cursor, queries.PUBLISHER_QUARTILE, ('%publisher1%', '%publisher1%'))
    _assert(len(rows) == 1, f'publisher1 filter returns 1 row (got {len(rows)})')

    print(f'\033[32m[PASS]\033[0m')


def test_journal_metrics(cursor):
    print('JOURNAL_METRICS:'.ljust(30), end='')
    rows = _fetch(cursor, queries.JOURNAL_METRICS)
    _assert(len(rows) == 3, f'returns 3 journals (got {len(rows)})')

    j1 = next((r for r in rows if r[0] == 'Journal 1'), None)
    _assert(j1 is not None, 'journal1 is in results')
    _assert(j1[1] == 200, f'TotalDocs: expected 200, got {j1[1]}')
    _assert(j1[8] == 'Q1', f'BestQuartile: expected Q1, got {j1[8]}')

    j3 = next((r for r in rows if r[0] == 'Journal 3'), None)
    _assert(j3 is not None, 'journal3 is in results')
    _assert(j3[8] is None, f'journal3 BestQuartile: expected NULL (got {j3[8]})')

    print(f'\033[32m[PASS]\033[0m')


def test_for_options_conf(cursor):
    print('FOR_OPTIONS_CONF:'.ljust(30), end='')
    rows = _fetch(cursor, queries.FOR_OPTIONS_CONF)
    _assert(len(rows) == 2, f'returns 2 FoR options (got {len(rows)})')
    _assert(rows[0] == (4601, 'for_name_1'), f'first FoR: expected (4601, for_name_1), got {rows[0]}')
    _assert(rows[1] == (4613, 'for_name_2'), f'second FoR: expected (4613, for_name_2), got {rows[1]}')

    print(f'\033[32m[PASS]\033[0m')


def test_for_options_mag(cursor):
    print('FOR_OPTIONS_MAG:'.ljust(30), end='')
    rows = _fetch(cursor, queries.FOR_OPTIONS_MAG)
    _assert(len(rows) == 2, f'returns 2 subject area options (got {len(rows)})')
    names = [r[0] for r in rows]
    _assert('subject_area_1' in names, 'subject_area_1 is an option')
    _assert('subject_area_2' in names, 'subject_area_2 is an option')

    print(f'\033[32m[PASS]\033[0m')


def test_category_trend_conf(cursor):
    print('CATEGORY_TREND_CONF:'.ljust(30), end='')
    rows = _fetch(cursor, queries.CATEGORY_TREND_CONF, (None, None, 2010, 2012))
    _assert(len(rows) == 4, f'no filter returns 4 rows (got {len(rows)})')

    rows = _fetch(cursor, queries.CATEGORY_TREND_CONF, (4601, 4601, 2010, 2012))
    _assert(len(rows) == 1, f'filter for FoR 4601 returns 1 row (got {len(rows)})')
    _assert(rows[0][0] == 2010 and rows[0][2] == 1, f'FoR 4601 in 2010: expected 1 venue (got {rows[0]})')

    print(f'\033[32m[PASS]\033[0m')


def test_category_trend_mag(cursor):
    print('CATEGORY_TREND_MAG:'.ljust(30), end='')
    rows = _fetch(cursor, queries.CATEGORY_TREND_MAG, (None, None, 2010, 2012))
    _assert(len(rows) == 4, f'no filter returns 4 rows (got {len(rows)})')

    rows = _fetch(cursor, queries.CATEGORY_TREND_MAG, ('subject_area_2', 'subject_area_2', 2010, 2012))
    _assert(len(rows) == 2, f'subject_area_2 filter returns 2 rows (got {len(rows)})')
    years = {r[0] for r in rows}
    _assert(years == {2011, 2012}, f'subject_area_2 years: expected {{2011, 2012}}, got {years}')

    print(f'\033[32m[PASS]\033[0m')


def test_scatter_trend_conf(cursor):
    print('SCATTER_TREND_CONF:'.ljust(30), end='')
    rows = _fetch(cursor, queries.SCATTER_TREND_CONF)
    _assert(len(rows) == 3, f'returns 3 years of data (got {len(rows)})')
    years = {r[0] for r in rows}
    _assert(years == {2010, 2011, 2012}, f'years: expected {{2010, 2011, 2012}}, got {years}')

    conf_2010 = next(r for r in rows if r[0] == 2010)
    conf_2011 = next(r for r in rows if r[0] == 2011)
    conf_2012 = next(r for r in rows if r[0] == 2012)
    _assert(conf_2010[2] == 3, f'conference papers in 2010: expected 3, got {conf_2010[2]}')
    _assert(conf_2011[2] == 1, f'conference papers in 2011: expected 1, got {conf_2011[2]}')
    _assert(conf_2012[2] == 1, f'conference papers in 2012: expected 1, got {conf_2012[2]}')
    _assert(float(conf_2011[1]) == 1.0, f'avg authors per paper in 2011: expected 1.0, got {conf_2011[1]}')
    _assert(float(conf_2012[1]) == 2.0, f'avg authors per paper in 2012: expected 2.0, got {conf_2012[1]}')

    print(f'\033[32m[PASS]\033[0m')


def test_scatter_trend_mag(cursor):
    print('SCATTER_TREND_MAG:'.ljust(30), end='')
    rows = _fetch(cursor, queries.SCATTER_TREND_MAG)
    _assert(len(rows) == 3, f'returns 3 years of data (got {len(rows)})')
    years = {r[0] for r in rows}
    _assert(years == {2010, 2011, 2012}, f'years: expected {{2010, 2011, 2012}}, got {years}')

    mag_2010 = next(r for r in rows if r[0] == 2010)
    mag_2011 = next(r for r in rows if r[0] == 2011)
    mag_2012 = next(r for r in rows if r[0] == 2012)
    _assert(mag_2010[2] == 2, f'journal papers in 2010: expected 2, got {mag_2010[2]}')
    _assert(mag_2011[2] == 2, f'journal papers in 2011: expected 2, got {mag_2011[2]}')
    _assert(mag_2012[2] == 1, f'journal papers in 2012: expected 1, got {mag_2012[2]}')
    _assert(float(mag_2010[1]) == 1.5, f'avg authors per paper in 2010: expected 1.5, got {mag_2010[1]}')
    _assert(float(mag_2011[1]) == 1.0, f'avg authors per paper in 2011: expected 1.0, got {mag_2011[1]}')
    _assert(float(mag_2012[1]) == 1.0, f'avg authors per paper in 2012: expected 1.0, got {mag_2012[1]}')

    print(f'\033[32m[PASS]\033[0m')


############
### MAIN ###
############

def _run_tests(cursor):
    failed = []

    def _run(fn):
        try:
            fn(cursor)
        except _TestFailure:
            failed.append(fn.__name__)
        except Exception as e:
            print(f'\n  \033[31m[ERROR]\033[0m {e}')
            failed.append(fn.__name__)

    print('\n\033[34m~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\033[0m')
    _run(test_quick_stats)

    print()
    _run(test_venue_stats_conf)
    _run(test_venue_stats_mag)
    _run(test_venue_papers_conf)
    _run(test_venue_papers_mag)

    print()
    _run(test_author_activity)
    _run(test_year_stats)
    _run(test_year_papers)

    print()
    _run(test_venue_rank_conf)
    _run(test_venue_rank_mag)
    _run(test_venue_distinct_authors_conf)
    _run(test_venue_distinct_authors_mag)
    _run(test_venue_year_range_conf)
    _run(test_venue_year_range_mag)
    _run(test_venue_trend)
    _run(test_venue_aggregate)

    print()
    _run(test_quartile_dist)
    _run(test_publisher_quartile)
    _run(test_journal_metrics)

    print()
    _run(test_for_options_conf)
    _run(test_for_options_mag)
    _run(test_category_trend_conf)
    _run(test_category_trend_mag)
    _run(test_scatter_trend_conf)
    _run(test_scatter_trend_mag)

    if failed:
        print(f'\n\033[31m{len(failed)} test(s) failed: {", ".join(failed)}\033[0m')
    else:
        print('\nAll tests passed !')
    print('\033[34m~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\033[0m\n')
    if failed:
        sys.exit(1)


def setup():
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(f'DROP DATABASE IF EXISTS {TEST_DB}')
    cursor.execute(f'CREATE DATABASE {TEST_DB}')
    cursor.execute(f'USE {TEST_DB}')
    full_pipeline.create_final_tables_schema(cursor)
    sql = FIXTURE_PATH.read_text(encoding='utf-8')
    for statement in sql.strip().split('\n\n'):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
    conn.commit()
    cursor.close()
    conn.close()


def teardown():
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(f'DROP DATABASE IF EXISTS {TEST_DB}')
    cursor.close()
    conn.close()


def run():
    setup()
    try:
        conn = _connect(database=TEST_DB)
        cursor = conn.cursor()
        try:
            _run_tests(cursor)
        finally:
            cursor.close()
            conn.close()
    finally:
        teardown()


if __name__ == '__main__':
    run()
