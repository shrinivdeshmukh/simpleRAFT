
def ask_for_vote(term: str, commit_id: str, staged: dict):
    return dict({
        'term': term,
        'commit_id': commit_id,
        'staged': staged
    })