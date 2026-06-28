from random import choices
from string import ascii_uppercase, digits
from models import db, ChatRoom, Friendship, ChatRoomMember, User



def generate_room_code(length=8) -> str:
    while True:
        code = ''.join(choices(ascii_uppercase + digits, k=length))
        if not ChatRoom.query.filter_by(code=code).first():
            return code
        
def chat_info(userid) -> dict:
    info = {}
    sent = Friendship.query.filter_by(requester_id=userid, status='accepted').all()
    receieved = Friendship.query.filter_by(receiver_id=userid, status='accepted').all()
    info["friends"] = [f.receiver for f in sent] + [f.requester for f in receieved]
    info["pending"] = Friendship.query.filter_by(receiver_id=userid, status='pending').all()
    memberships = ChatRoomMember.query.filter_by(user_id=userid).all()
    info["rooms"] = [m.room for m in memberships]
    return info

def user_search(request, session) -> dict:
    results = []
    query = ''
    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if query:
            if query.isdigit():
                found = User.query.filter_by(id=int(query)).first()
                if found and found.id != session['user_id']:
                    results = [found]
            else:
                results = User.query.filter(
                    User.username.ilike(f'%{query}%'),
                    User.id != session['user_id']
                ).all()
    return {"results":results, "query":query}