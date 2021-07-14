
def ask_for_vote(term: str, commit_id: str, staged: dict):
    return dict({
        'term': term,
        'commit_id': commit_id,
        'staged': staged
    })


def update_follower_commitid(term, addr, action, payload):
    return dict({
        'term': term,
        'addr': addr,
        'action': action,
        'payload': payload
    })

def send_heartbeat(term, addr):
    return dict({
        'term': term,
        'addr': addr
    })

def handle_put(term, addr, payload, action, commit_id):
    return dict({
            "term": term,
            "addr": addr,
            "payload": payload,
            "action": action,
            "commit_id": commit_id
    })