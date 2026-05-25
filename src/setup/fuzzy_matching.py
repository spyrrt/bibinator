import mysql.connector
import pandas as pd
from rapidfuzz.utils import default_process
from rapidfuzz import fuzz
from rapidfuzz.process import extractOne
from pathlib import Path
from _config import DB_CONFIG

OUTPUT_DIR = Path(__file__).parent.parent.parent / 'output/fuzzy_matching'

##########################
### TEXT NORMALIZATION ###
##########################

M_REPLACE_DICT = {
    'computer': 'comp',
    'comput': 'comp',
    'compational': 'comp',
    'mathematic': 'math',
    'mathal': 'math',
    'system': 'sy',
    'syst': 'sy',
    'transaction': 't',
    'tran': 't',
    'medical': 'm',
    'intelligent': 'intell',
    'foundation': 'found',
    'science': 'sci',
    'technology': 'tech',
    'advance': 'adv',
    'informat': 'inf',
    'inform': 'inf',
    'letter': 'lett',
    'communication': 'comm',
    'knowledge': 'knowl',
    'international': 'i',
    'int': 'i',
    'software': 'softw',
    'automat': 'autom',
    'commun': 'comm',
    'research': 're',
    'application': 'appl',
    'process': 'proc',
    'engineer': 'eng',
    'china': 'ch',
    'magazine': 'mag',
    'educat': 'edu',
}

C_REPLACE_DICT = {
    'international': 'i',
}

M_REMOVE_SET = {'journal', 'j'}
C_REMOVE_SET = {
    'workshop', 'workshops', 'i', 'ii', 'iii',
    'conference', 'comference', 'confrence', 'symposium',
}
STOPWORDS = {'and', 'the', 'on', 'for', 'in', 'of', 'with'}
SUFFIXES = {'s', 'ed', 'ing', 'ion'}


def replace_with_dict(text, repl_dict):
    if not text:
        return ''
    for key, value in repl_dict.items():
        text = text.replace(key, value)
    return text


def remove_suffixes(text):
    if not text:
        return ''
    new_words = []
    for word in text.split():
        for suffix in SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix):
                word = word[:-len(suffix)]
                break
        new_words.append(word)
    return ' '.join(new_words)


def remove_words(text, remv_set):
    if not text:
        return ''
    return ' '.join(
        word for word in text.split()
        if word not in STOPWORDS and word not in remv_set
    )

#######################
### MATCHING CONFIG ###
#######################

M_SCORER = fuzz.token_sort_ratio
C_SCORER = fuzz.WRatio
M_THRESHOLD = 88.1
C_THRESHOLD = 92.2

M_BLACKLISTED_C_IDS = {
    4184, 7610, 15694, 13199, 2885, 6458, 9109, 9998, 697, 6474,
    2516, 2997, 10243, 9502, 12334, 9851, 1404, 4071, 2072, 13335,
    4542, 8289, 9764, 6103, 11192, 15104, 5523,
}

M_WHITELISTED_C_IDS = {
    1303: 'T. Affective Computing',
}

C_BLACKLISTED_C_IDS = {
    2176, 507, 2188, 576, 1892, 1815, 2186, 37, 887,
}

C_WHITELISTED_C_IDS = {
    1961: 'Artificial Intelligence in Higher Education',
    1122: 'Machine Learning and Its Applications',
    1378: 'Experimental Algorithmics',
    572:  'Drawing Graphs',
    2257: 'Mobile and Wireless Communication Networks',
    925:  'Integrated Broadband Communications',
    661:  'IEEE Conf. of Intelligent Systems',
    2061: 'International Conference on Evolutionary Computation',
    64:   'Symposium on Solid and Physical Modeling',
}


def _tuple_to_cid(matched_tuple, ranking_df):
    if matched_tuple is None:
        return None
    return ranking_df.iloc[matched_tuple[2]]['c_id']


####################
### DATA LOADING ###
####################

def _load_data(cursor):
    def query_to_df(query):
        cursor.execute(query)
        return pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])

    m_ranking = query_to_df(
        'SELECT mag_rank AS c_id, Title AS c_title FROM starting_mag_ranking'
    )
    m_articles = query_to_df(
        'SELECT id AS a_id, journal AS a_title FROM starting_mag_articles'
    )
    c_ranking = query_to_df(
        'SELECT id AS c_id, title AS c_title, acronym AS c_acronym_og FROM starting_conf_ranking'
    )
    c_articles = query_to_df(
        'SELECT id AS a_id, booktitle AS a_title FROM starting_conf_articles'
    )

    return m_ranking, m_articles, c_ranking, c_articles


def run(cursor):
    # OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print('\n\033[34m~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\033[0m')
    print('Loading data from database...')
    m_ranking, m_articles, c_ranking, c_articles = _load_data(cursor)

    print('\nMatching magazines...')
    m_articles_out, m_ranking_out, m_matches = match_magazines(m_ranking, m_articles)
    # m_matches.to_csv(OUTPUT_DIR / 'm_matches.csv', index=False)
    # m_articles_out.to_csv(OUTPUT_DIR / 'm_articles.csv', index=False)
    # m_ranking_out.to_csv(OUTPUT_DIR / 'm_ranking.csv', index=False)

    print('\nMatching conferences...')
    c_articles_out, c_ranking_out, c_matches = match_conferences(c_ranking, c_articles)
    # c_matches.to_csv(OUTPUT_DIR / 'c_matches.csv', index=False)
    # c_articles_out.to_csv(OUTPUT_DIR / 'c_articles.csv', index=False)
    # c_ranking_out.to_csv(OUTPUT_DIR / 'c_unique_ranking.csv', index=False)

    print('Fuzzy matching complete !')
    print('\033[34m~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\033[0m\n')

    return m_articles_out, m_ranking_out, c_articles_out, c_ranking_out


####################
### MAG MATCHING ###
####################

def match_magazines(m_ranking, m_articles):
    m_unique_titles = m_articles[
        m_articles['a_title'].notna() &
        (m_articles['a_title'].str.strip() != '"') &
        (m_articles['a_title'].str.strip() != '') &
        ~m_articles['a_title'].str.contains('…', na=False)
    ][['a_title']].drop_duplicates().reset_index(drop=True)

    m_ranking['c_title'] = m_ranking.apply(
        lambda row: M_WHITELISTED_C_IDS.get(row['c_id'], row['c_title']), axis=1
    )

    m_unique_titles['a_title_processed'] = (
        m_unique_titles['a_title']
        .apply(default_process)
        .apply(lambda x: remove_words(x, M_REMOVE_SET))
        .apply(remove_suffixes)
        .apply(lambda x: replace_with_dict(x, M_REPLACE_DICT))
    )
    m_ranking['c_title_processed'] = (
        m_ranking['c_title']
        .apply(default_process)
        .apply(lambda x: remove_words(x, M_REMOVE_SET))
        .apply(remove_suffixes)
        .apply(lambda x: replace_with_dict(x, M_REPLACE_DICT))
    )

    print(f'  Unique magazines: {m_unique_titles.shape[0]}')
    print(f'  Magazine rankings: {m_ranking.shape[0]}')

    m_unique_titles['matched_tuple'] = m_unique_titles['a_title_processed'].apply(
        lambda x: extractOne(
            query=x,
            choices=m_ranking['c_title_processed'],
            scorer=M_SCORER,
            score_cutoff=M_THRESHOLD,
        )
    )
    m_unique_titles['c_id'] = m_unique_titles['matched_tuple'].apply(
        lambda t: _tuple_to_cid(t, m_ranking)
    )
    m_unique_titles['score'] = m_unique_titles['matched_tuple'].apply(
        lambda x: x[1] if x is not None else None
    )

    blacklist_mask = (
        m_unique_titles['c_id'].isin(M_BLACKLISTED_C_IDS) &
        (m_unique_titles['score'] != 100)
    )
    m_unique_titles.loc[blacklist_mask, ['matched_tuple', 'c_id', 'score']] = None

    m_unique_titles = m_unique_titles.merge(
        m_ranking[['c_id', 'c_title', 'c_title_processed']], on='c_id', how='left'
    )

    m_matches = m_unique_titles[[
        'a_title', 'c_title', 'c_id', 'score', 'a_title_processed', 'c_title_processed'
    ]].copy().sort_values('score', ascending=False).reset_index(drop=True)

    m_unmatched = m_unique_titles[m_unique_titles['c_id'].isna()]
    print(f'  Unmatched magazines: {m_unmatched.shape[0]}')

    m_new_ranking = m_unmatched[['a_title']].rename(columns={'a_title': 'c_title'})
    m_new_ranking['is_ranked'] = False
    start_id = int(m_ranking['c_id'].max()) + 1
    m_new_ranking['c_id'] = range(start_id, start_id + len(m_new_ranking))

    m_ranking['is_ranked'] = True
    m_ranking = pd.concat([m_ranking, m_new_ranking], ignore_index=True)
    m_ranking = m_ranking.drop(columns=['c_title_processed'])

    title_to_new_cid = m_new_ranking.set_index('c_title')['c_id']
    unmatched_mask = m_unique_titles['c_id'].isna()
    m_unique_titles.loc[unmatched_mask, 'c_id'] = m_unique_titles.loc[unmatched_mask, 'a_title'].map(title_to_new_cid)

    m_articles = m_articles.merge(m_unique_titles[['a_title', 'c_id']], on='a_title', how='left')
    m_articles = m_articles.drop(columns=['a_title'])

    ranked = m_articles.merge(
        m_ranking[['c_id', 'is_ranked']], on='c_id', how='left'
    )['is_ranked'].sum()
    print(f'  Ranked articles in magazines: {ranked}')

    return m_articles, m_ranking, m_matches

#####################
### CONF MATCHING ###
#####################

def match_conferences(c_ranking, c_articles):
    c_unique_titles = c_articles[
        c_articles['a_title'].notna() &
        (c_articles['a_title'].str.strip() != '"') &
        (c_articles['a_title'].str.strip() != '') &
        ~c_articles['a_title'].str.contains('…', na=False)
    ][['a_title']].drop_duplicates().reset_index(drop=True)
    c_unique_ranking = c_ranking.drop_duplicates(subset='c_id').reset_index(drop=True)

    c_unique_ranking['c_title'] = c_unique_ranking.apply(
        lambda row: C_WHITELISTED_C_IDS.get(row['c_id'], row['c_title']), axis=1
    )

    c_unique_titles['a_title_processed'] = (
        c_unique_titles['a_title']
        .apply(default_process)
        .str.replace(r'\d+$', '', regex=True)
        .apply(lambda x: remove_words(x, C_REMOVE_SET))
        .apply(lambda x: replace_with_dict(x, C_REPLACE_DICT))
    )
    c_unique_ranking['c_title_processed'] = (
        c_unique_ranking['c_title']
        .apply(default_process)
        .apply(lambda x: remove_words(x, C_REMOVE_SET))
        .apply(lambda x: replace_with_dict(x, C_REPLACE_DICT))
    )
    c_unique_ranking['c_acronym'] = (
        c_unique_ranking['c_acronym_og']
        .apply(default_process)
        .apply(lambda x: remove_words(x, C_REMOVE_SET))
        .apply(lambda x: replace_with_dict(x, C_REPLACE_DICT))
    )

    print(f'  Unique conferences: {c_unique_titles.shape[0]}')
    print(f'  Conference ranking: {c_unique_ranking.shape[0]}')

    c_unique_titles['matched_tuple'] = c_unique_titles['a_title_processed'].apply(
        lambda x: extractOne(
            query=x,
            choices=c_unique_ranking['c_title_processed'],
            scorer=C_SCORER,
            score_cutoff=C_THRESHOLD,
        )
    )

    acronym_lookup = {
        acr: (acr, 100, idx)
        for idx, acr in enumerate(c_unique_ranking['c_acronym'])
        if acr
    }

    exact = c_unique_titles['a_title_processed'].map(acronym_lookup)
    
    current_score = c_unique_titles['matched_tuple'].apply(lambda t: t[1] if t is not None else -1)

    update_mask = exact.notna() & (current_score < 100)
    c_unique_titles.loc[update_mask, 'matched_tuple'] = exact[update_mask]

    c_unique_titles['c_id'] = c_unique_titles['matched_tuple'].apply(
        lambda t: _tuple_to_cid(t, c_unique_ranking)
    )
    c_unique_titles['score'] = c_unique_titles['matched_tuple'].apply(
        lambda x: x[1] if x is not None else None
    )

    blacklist_mask = (
        c_unique_titles['c_id'].isin(C_BLACKLISTED_C_IDS) &
        (c_unique_titles['score'] != 100)
    )
    c_unique_titles.loc[blacklist_mask, ['matched_tuple', 'c_id', 'score']] = None

    c_unique_titles = c_unique_titles.merge(
        c_unique_ranking[['c_id', 'c_title', 'c_title_processed', 'c_acronym_og']],
        on='c_id', how='left',
    )

    c_matches = c_unique_titles[[
        'a_title', 'c_title', 'c_acronym_og', 'c_id', 'score',
        'a_title_processed', 'c_title_processed',
    ]].copy().sort_values('score', ascending=False).reset_index(drop=True)

    c_unmatched = c_unique_titles[c_unique_titles['c_id'].isna()]
    print(f'  Unmatched conferences: {c_unmatched.shape[0]}')

    c_new_ranking = c_unmatched[['a_title']].rename(columns={'a_title': 'c_title'})
    c_new_ranking['is_ranked'] = False
    start_id = int(c_unique_ranking['c_id'].max()) + 1
    c_new_ranking['c_id'] = range(start_id, start_id + len(c_new_ranking))

    c_unique_ranking['is_ranked'] = True
    c_unique_ranking = pd.concat([c_unique_ranking, c_new_ranking], ignore_index=True)
    c_unique_ranking = c_unique_ranking.drop(columns=['c_title_processed', 'c_acronym'])

    title_to_new_cid = c_new_ranking.set_index('c_title')['c_id']
    unmatched_mask = c_unique_titles['c_id'].isna()
    c_unique_titles.loc[unmatched_mask, 'c_id'] = c_unique_titles.loc[unmatched_mask, 'a_title'].map(title_to_new_cid)

    c_articles = c_articles.merge(c_unique_titles[['a_title', 'c_id']], on='a_title', how='left')
    c_articles = c_articles.drop(columns=['a_title'])

    ranked = c_articles.merge(
        c_unique_ranking[['c_id', 'is_ranked']], on='c_id', how='left'
    )['is_ranked'].sum()
    print(f'  Ranked articles in conferences: {ranked}')

    return c_articles, c_unique_ranking, c_matches

############
### MAIN ###
############

if __name__ == '__main__':
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        run(cursor)
    finally:
        cursor.close()
        conn.close()
