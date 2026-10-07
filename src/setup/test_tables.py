import sys
import mysql.connector
from _config import DB_CONFIG


class _TestFailure(Exception):
    pass


def _assert(condition, msg):
    if not condition:
        print(f'  \033[31m[FAIL]\033[0m {msg}')
        raise _TestFailure()
    print(f'  \033[32m[PASS]\033[0m {msg}')


def _count(cursor, query):
    cursor.execute(query)
    return cursor.fetchone()[0]


def _assert_count(actual, expected):
    if actual == expected:
        print(f'  \033[32m[PASS]\033[0m row count: {actual}')
    else:
        print(f'  \033[31m[FAIL]\033[0m row count: expected {expected}, got {actual}')
        raise _TestFailure()


##################
### FOR_LOOKUP ###
##################

def test_for_lookup(cursor):
    print('FOR_LOOKUP:')
    cursor.execute("SHOW TABLES LIKE 'FOR_LOOKUP'")
    _assert(cursor.fetchone() is not None, 'table exists')

    n = _count(cursor, 'SELECT COUNT(*) FROM FOR_LOOKUP')
    _assert_count(n, 11)

    _assert(_count(cursor, 'SELECT COUNT(*) FROM FOR_LOOKUP WHERE for_name IS NULL') == 0, 'no NULL for_name')
    _assert(_count(cursor, "SELECT COUNT(*) FROM FOR_LOOKUP WHERE TRIM(for_name) = ''") == 0, 'no empty for_name')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM FOR_LOOKUP WHERE for_code <= 0') == 0, 'all codes positive')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM FOR_LOOKUP WHERE for_code >= 10000') == 0, 'all codes top-level (< 10000)')
    _assert(
        _count(cursor, 'SELECT COUNT(*) FROM FOR_LOOKUP') ==
        _count(cursor, 'SELECT COUNT(DISTINCT for_name) FROM FOR_LOOKUP'),
        'no duplicate for_name'
    )
    

################################
### BEST_SUBJECT_AREA_LOOKUP ###
################################

def test_best_subject_area_lookup(cursor):
    print('\nBEST_SUBJECT_AREA_LOOKUP:')
    cursor.execute("SHOW TABLES LIKE 'BEST_SUBJECT_AREA_LOOKUP'")
    _assert(cursor.fetchone() is not None, 'table exists')

    n = _count(cursor, 'SELECT COUNT(*) FROM BEST_SUBJECT_AREA_LOOKUP')
    _assert_count(n, 27)

    _assert(_count(cursor, 'SELECT COUNT(*) FROM BEST_SUBJECT_AREA_LOOKUP WHERE best_subject_area_name IS NULL') == 0, 'no NULL best_subject_area_name')
    _assert(_count(cursor, "SELECT COUNT(*) FROM BEST_SUBJECT_AREA_LOOKUP WHERE TRIM(best_subject_area_name) = ''") == 0, 'no empty best_subject_area_name')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM BEST_SUBJECT_AREA_LOOKUP WHERE best_subject_area_id <= 0') == 0, 'all IDs positive')
    _assert(
        _count(cursor, 'SELECT COUNT(*) FROM BEST_SUBJECT_AREA_LOOKUP') ==
        _count(cursor, 'SELECT COUNT(DISTINCT best_subject_area_name) FROM BEST_SUBJECT_AREA_LOOKUP'),
        'no duplicate best_subject_area_name'
    )
    max_id = _count(cursor, 'SELECT MAX(best_subject_area_id) FROM BEST_SUBJECT_AREA_LOOKUP')
    _assert(max_id == n, f'IDs are sequential from 1 (max={max_id}, count={n})')


#####################
### AUTHOR_LOOKUP ###
#####################

def test_author_lookup(cursor):
    print('\nAUTHOR_LOOKUP:')
    cursor.execute("SHOW TABLES LIKE 'AUTHOR_LOOKUP'")
    _assert(cursor.fetchone() is not None, 'table exists')

    n = _count(cursor, 'SELECT COUNT(*) FROM AUTHOR_LOOKUP')
    _assert_count(n, 1394256)

    _assert(_count(cursor, 'SELECT COUNT(*) FROM AUTHOR_LOOKUP WHERE author_name IS NULL') == 0, 'no NULL author_name')
    _assert(_count(cursor, "SELECT COUNT(*) FROM AUTHOR_LOOKUP WHERE TRIM(author_name) = ''") == 0, 'no empty author_name')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM AUTHOR_LOOKUP WHERE author_id <= 0') == 0, 'all IDs positive')
    _assert(
        _count(cursor, 'SELECT COUNT(*) FROM AUTHOR_LOOKUP') ==
        _count(cursor, 'SELECT COUNT(DISTINCT author_name) FROM AUTHOR_LOOKUP'),
        'no duplicate author_name'
    )
    max_id = _count(cursor, 'SELECT MAX(author_id) FROM AUTHOR_LOOKUP')
    _assert(max_id == n, f'IDs are sequential from 1 (max={max_id}, count={n})')
    _assert(_count(cursor, "SELECT COUNT(*) FROM AUTHOR_LOOKUP WHERE author_name = 'no_author'") == 1, 'no_author placeholder exists exactly once')


################
### ARTICLES ###
################

def test_articles(cursor):
    print('\nARTICLES:')
    cursor.execute("SHOW TABLES LIKE 'ARTICLES'")
    _assert(cursor.fetchone() is not None, 'table exists')

    n = _count(cursor, 'SELECT COUNT(*) FROM ARTICLES')
    _assert_count(n, 2528067)

    _assert(_count(cursor, 'SELECT COUNT(*) FROM ARTICLES WHERE title IS NULL') == 0, 'no NULL title')
    _assert(_count(cursor, "SELECT COUNT(*) FROM ARTICLES WHERE TRIM(title) = ''") == 0, 'no empty title')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM ARTICLES WHERE article_id <= 0') == 0, 'all article_ids positive')
    _assert(_count(cursor, "SELECT COUNT(*) FROM ARTICLES WHERE title = 'no_title'") > 0, 'no_title placeholder exists')


####################
### CONF_RANKING ###
####################

def test_conf_ranking(cursor):
    print('\nCONF_RANKING:')
    cursor.execute("SHOW TABLES LIKE 'CONF_RANKING'")
    _assert(cursor.fetchone() is not None, 'table exists')

    n = _count(cursor, 'SELECT COUNT(*) FROM CONF_RANKING')
    _assert_count(n, 6358)

    _assert(_count(cursor, 'SELECT COUNT(*) FROM CONF_RANKING WHERE conf_rank IS NULL') == 0, 'no NULL conf_rank')
    _assert(_count(cursor, "SELECT COUNT(*) FROM CONF_RANKING WHERE TRIM(conf_rank) = ''") == 0, 'no empty conf_rank')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM CONF_RANKING WHERE conf_id <= 0') == 0, 'all conf_ids positive')
    _assert(_count(cursor, "SELECT COUNT(*) FROM CONF_RANKING WHERE conf_rank = 'unranked'") > 0, 'unranked placeholder exists')
    _assert(_count(cursor, "SELECT COUNT(*) FROM CONF_RANKING WHERE conf_rank != 'unranked'") > 0, 'ranked conferences exist')


###################
### MAG_RANKING ###
###################

def test_mag_ranking(cursor):
    print('\nMAG_RANKING:')
    cursor.execute("SHOW TABLES LIKE 'MAG_RANKING'")
    _assert(cursor.fetchone() is not None, 'table exists')

    n = _count(cursor, 'SELECT COUNT(*) FROM MAG_RANKING')
    _assert_count(n, 18792)

    _assert(_count(cursor, 'SELECT COUNT(*) FROM MAG_RANKING WHERE mag_id <= 0') == 0, 'all mag_ids positive')
    _assert(_count(cursor, "SELECT COUNT(*) FROM MAG_RANKING WHERE best_quartile NOT IN ('Q1','Q2','Q3','Q4') AND best_quartile IS NOT NULL") == 0, 'best_quartile values are valid')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM MAG_RANKING WHERE mag_rank IS NOT NULL AND mag_rank <= 0') == 0, 'all non-NULL mag_rank values are positive')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM MAG_RANKING WHERE mag_rank IS NOT NULL') > 0, 'ranked magazines exist')


########################
### CONF_ARTICLE_INFO ##
########################

def test_conf_article_info(cursor):
    print('\nCONF_ARTICLE_INFO:')
    cursor.execute("SHOW TABLES LIKE 'CONF_ARTICLE_INFO'")
    _assert(cursor.fetchone() is not None, 'table exists')

    n = _count(cursor, 'SELECT COUNT(*) FROM CONF_ARTICLE_INFO')
    _assert_count(n, 1413794)

    _assert(_count(cursor, 'SELECT COUNT(*) FROM CONF_ARTICLE_INFO WHERE conf_id IS NULL') == 0, 'no NULL conf_id')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM CONF_ARTICLE_INFO WHERE article_id <= 0') == 0, 'all article_ids positive')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM CONF_ARTICLE_INFO WHERE conf_id <= 0') == 0, 'all conf_ids positive')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM CONF_ARTICLE_INFO WHERE year IS NOT NULL AND (year < 1900 OR year > 2015)') == 0, 'all years in valid range (1900-2015)')


########################
### MAG_ARTICLE_INFO ###
########################

def test_mag_article_info(cursor):
    print('\nMAG_ARTICLE_INFO:')
    cursor.execute("SHOW TABLES LIKE 'MAG_ARTICLE_INFO'")
    _assert(cursor.fetchone() is not None, 'table exists')

    n = _count(cursor, 'SELECT COUNT(*) FROM MAG_ARTICLE_INFO')
    _assert_count(n, 1114045)

    _assert(_count(cursor, 'SELECT COUNT(*) FROM MAG_ARTICLE_INFO WHERE mag_id IS NULL') == 0, 'no NULL mag_id')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM MAG_ARTICLE_INFO WHERE article_id <= 0') == 0, 'all article_ids positive')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM MAG_ARTICLE_INFO WHERE mag_id <= 0') == 0, 'all mag_ids positive')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM MAG_ARTICLE_INFO WHERE year IS NOT NULL AND (year < 1900 OR year > 2015)') == 0, 'all years in valid range (1900-2015)')


#######################
### ARTICLE_AUTHORS ###
#######################

def test_article_authors(cursor):
    print('\nARTICLE_AUTHORS:')
    cursor.execute("SHOW TABLES LIKE 'ARTICLE_AUTHORS'")
    _assert(cursor.fetchone() is not None, 'table exists')

    n = _count(cursor, 'SELECT COUNT(*) FROM ARTICLE_AUTHORS')
    _assert_count(n, 7054321)

    _assert(_count(cursor, 'SELECT COUNT(*) FROM ARTICLE_AUTHORS WHERE article_id <= 0') == 0, 'all article_ids positive')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM ARTICLE_AUTHORS WHERE author_id <= 0') == 0, 'all author_ids positive')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM ARTICLES WHERE article_id NOT IN (SELECT DISTINCT article_id FROM ARTICLE_AUTHORS)') == 0, 'every article has at least one author entry')



###################
### CROSS-TABLE ###
###################

def test_cross_table(cursor):
    print('\nCROSS-TABLE:')
    _assert(_count(cursor, 'SELECT COUNT(*) FROM CONF_ARTICLE_INFO WHERE article_id IN (SELECT article_id FROM MAG_ARTICLE_INFO)') == 0, 'no article overlap in CONF_ARTICLE_INFO and MAG_ARTICLE_INFO')


############
### MAIN ###
############

def run(cursor):
    print('\n\033[34m~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\033[0m')
    tests = [
        test_for_lookup, test_best_subject_area_lookup, test_author_lookup,
        test_articles, test_conf_ranking, test_mag_ranking,
        test_conf_article_info, test_mag_article_info,
        test_article_authors, test_cross_table,
    ]
    failed = []
    for test in tests:
        try:
            test(cursor)
        except _TestFailure:
            failed.append(test.__name__)
        except Exception as e:
            print(f'  \033[31m[ERROR]\033[0m {e}')
            failed.append(test.__name__)

    if failed:
        print(f'\n\033[31m{len(failed)} test(s) failed: {", ".join(failed)}\033[0m')
    else:
        print('\nAll tests passed !')
    print('\033[34m~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\033[0m\n')
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        run(cursor)
    finally:
        cursor.close()
        conn.close()