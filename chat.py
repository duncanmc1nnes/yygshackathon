from random import choices
from string import ascii_uppercase, digits
from models import db, ChatRoom, Friendship, ChatRoomMember, User, DirectMessage, ChatRoomMessage


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

def add_friend(session, target_id) -> str:
    user_id = session['user_id']
    if target_id == user_id:
        return "self"
    existing = Friendship.query.filter(
        ((Friendship.requester_id == user_id) & (Friendship.receiver_id == target_id)) |
        ((Friendship.requester_id == target_id) & (Friendship.receiver_id == user_id))
    ).first()
    if existing:
        return "previous"
    else:
        friendship = Friendship(requester_id=user_id, receiver_id=target_id, status='pending')
        db.session.add(friendship)
        db.session.commit()
    return ""

def accept_friend(friendship_id, session) -> str:
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.receiver_id != session['user_id']:
        return "fail"
    friendship.status = 'accepted'
    db.session.commit()
    return ""

def decline_friend(friendship_id, session) -> str:
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.receiver_id != session['user_id']:
        return "fail"
    db.session.delete(friendship)
    db.session.commit()
    return ""

def send_dm(session, friend_id, request):
    user_id = session['user_id']
    friend = User.query.get_or_404(friend_id)
    friendship = Friendship.query.filter(
        ((Friendship.requester_id == user_id) & (Friendship.receiver_id == friend_id)) |
        ((Friendship.requester_id == friend_id) & (Friendship.receiver_id == user_id)),
        Friendship.status == 'accepted'
    ).first()
    if not friendship:
        return "not"
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            dm = DirectMessage(sender_id=user_id, receiver_id=friend_id, content=content)
            db.session.add(dm)
            db.session.commit()
        return "post"
    return DirectMessage.query.filter(
        ((DirectMessage.sender_id == user_id) & (DirectMessage.receiver_id == friend_id)) |
        ((DirectMessage.sender_id == friend_id) & (DirectMessage.receiver_id == user_id))
    ).order_by(DirectMessage.timestamp.asc()).all()

def create_room(session, request, name):
    is_public = request.form.get('is_public') == 'true'
    code = generate_room_code()
    chat_room = ChatRoom(name=name, code=code, is_public=is_public, owner_id=session['user_id'])
    db.session.add(chat_room)
    db.session.flush()
    membership = ChatRoomMember(user_id=session['user_id'], room_id=chat_room.id)
    db.session.add(membership)
    db.session.commit()
    return {"code":code, "chat_room":chat_room}

def join_room(request, session):
    code = request.form.get('code', '').strip().upper()
    chat_room = ChatRoom.query.filter_by(code=code).first()
    if not chat_room:
        return{"flash":['Invalid room code.', 'error'], "url":"join_room"}
    existing = ChatRoomMember.query.filter_by(user_id=session['user_id'], room_id=chat_room.id).first()
    if existing:
        return{"flash":['You are already in this room.', 'info'], "url":['room'], "id":chat_room.id}
    membership = ChatRoomMember(user_id=session['user_id'], room_id=chat_room.id)
    db.session.add(membership)
    db.session.commit()
    return{"flash":[f'Joined room: {chat_room.name}!', 'success'], "url":['room'], "id":chat_room.id}

def room(room_id, session, request):
    chat_room = ChatRoom.query.get_or_404(room_id)
    membership = ChatRoomMember.query.filter_by(user_id=session['user_id'], room_id=room_id).first()
    if not membership:
        return {"status":"fail"}
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            msg = ChatRoomMessage(room_id=room_id, sender_id=session['user_id'], content=content)
            db.session.add(msg)
            db.session.commit()
        return {"status":"post"}
    messages = ChatRoomMessage.query.filter_by(room_id=room_id).order_by(ChatRoomMessage.timestamp.asc()).all()
    members = ChatRoomMember.query.filter_by(room_id=room_id).all()
    return {"status":"render", "args":{"url":'chat/room.html', "room":chat_room, "messages":messages, "members":members, "current_user_id":session['user_id']}}
