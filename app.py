import string
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from models import db, Party, Member, Message, User, Friendship, DirectMessage, ChatRoom, ChatRoomMember, ChatRoomMessage
from functools import wraps
import chat

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'super_secret_key_for_yygs_hackathon'
db.init_app(app)

with app.app_context():
    db.create_all()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def home():
    user = User.query.get(session['user_id'])
    parties = Party.query.order_by(Party.created_at.desc()).all()
    chat_info = chat.chat_info(user.id)
    return render_template('home.html', user=user, username=session['username'],
            parties=parties, friends=chat_info["friends"], pending=chat_info["pending"], rooms=chat_info["rooms"])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or Email already exists.', 'error')
        else:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['username_or_email']
        password = request.form['password']
        user = User.query.filter(
            ((User.username == username_or_email) | (User.email == username_or_email)) &
            (User.password == password)
        ).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ─── User Search ──────────────────────────────────────────────────────────────

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search_users():
    info = chat.user_search(request=request, session=session)
    return render_template('search.html', results=info["results"], query=info["query"])

# ─── Friend System ────────────────────────────────────────────────────────────

@app.route('/friends/add/<int:target_id>', methods=['POST'])
@login_required
def add_friend(target_id):
    user_id = session['user_id']
    if target_id == user_id:
        flash("You can't add yourself.", 'error')
        return redirect(url_for('search_users'))
    existing = Friendship.query.filter(
        ((Friendship.requester_id == user_id) & (Friendship.receiver_id == target_id)) |
        ((Friendship.requester_id == target_id) & (Friendship.receiver_id == user_id))
    ).first()
    if existing:
        flash('Friend request already sent or you are already friends.', 'error')
    else:
        friendship = Friendship(requester_id=user_id, receiver_id=target_id, status='pending')
        db.session.add(friendship)
        db.session.commit()
        flash('Friend request sent!', 'success')
    return redirect(url_for('search_users'))

@app.route('/friends/accept/<int:friendship_id>', methods=['POST'])
@login_required
def accept_friend(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.receiver_id != session['user_id']:
        flash('Unauthorized.', 'error')
        return redirect(url_for('home'))
    friendship.status = 'accepted'
    db.session.commit()
    flash('Friend request accepted!', 'success')
    return redirect(url_for('home'))

@app.route('/friends/decline/<int:friendship_id>', methods=['POST'])
@login_required
def decline_friend(friendship_id):
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.receiver_id != session['user_id']:
        flash('Unauthorized.', 'error')
        return redirect(url_for('home'))
    db.session.delete(friendship)
    db.session.commit()
    flash('Friend request declined.', 'info')
    return redirect(url_for('home'))

# ─── Direct Messages ──────────────────────────────────────────────────────────

@app.route('/dm/<int:friend_id>', methods=['GET', 'POST'])
@login_required
def direct_message(friend_id):
    user_id = session['user_id']
    friend = User.query.get_or_404(friend_id)
    friendship = Friendship.query.filter(
        ((Friendship.requester_id == user_id) & (Friendship.receiver_id == friend_id)) |
        ((Friendship.requester_id == friend_id) & (Friendship.receiver_id == user_id)),
        Friendship.status == 'accepted'
    ).first()
    if not friendship:
        flash('You must be friends to send a direct message.', 'error')
        return redirect(url_for('home'))
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            dm = DirectMessage(sender_id=user_id, receiver_id=friend_id, content=content)
            db.session.add(dm)
            db.session.commit()
        return redirect(url_for('direct_message', friend_id=friend_id))
    messages = DirectMessage.query.filter(
        ((DirectMessage.sender_id == user_id) & (DirectMessage.receiver_id == friend_id)) |
        ((DirectMessage.sender_id == friend_id) & (DirectMessage.receiver_id == user_id))
    ).order_by(DirectMessage.timestamp.asc()).all()
    return render_template('dm.html', friend=friend, messages=messages, current_user_id=user_id)

# ─── Chat Rooms ───────────────────────────────────────────────────────────────

@app.route('/rooms/create', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        is_public = request.form.get('is_public') == 'true'
        if not name:
            flash('Room name is required.', 'error')
            return redirect(url_for('create_room'))
        code = generate_room_code()
        chat_room = ChatRoom(name=name, code=code, is_public=is_public, owner_id=session['user_id'])
        db.session.add(chat_room)
        db.session.flush()
        membership = ChatRoomMember(user_id=session['user_id'], room_id=chat_room.id)
        db.session.add(membership)
        db.session.commit()
        flash(f'Room created! Share the code: {code}', 'success')
        return redirect(url_for('room', room_id=chat_room.id))
    return render_template('create_room.html')

@app.route('/rooms/join', methods=['GET', 'POST'])
@login_required
def join_room():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        chat_room = ChatRoom.query.filter_by(code=code).first()
        if not chat_room:
            flash('Invalid room code.', 'error')
            return redirect(url_for('join_room'))
        existing = ChatRoomMember.query.filter_by(user_id=session['user_id'], room_id=chat_room.id).first()
        if existing:
            flash('You are already in this room.', 'info')
            return redirect(url_for('room', room_id=chat_room.id))
        membership = ChatRoomMember(user_id=session['user_id'], room_id=chat_room.id)
        db.session.add(membership)
        db.session.commit()
        flash(f'Joined room: {chat_room.name}!', 'success')
        return redirect(url_for('room', room_id=chat_room.id))
    return render_template('join_room.html')

@app.route('/rooms/browse')
@login_required
def browse_rooms():
    rooms = ChatRoom.query.filter_by(is_public=True).order_by(ChatRoom.created_at.desc()).all()
    user_room_ids = {m.room_id for m in ChatRoomMember.query.filter_by(user_id=session['user_id']).all()}
    return render_template('browse_rooms.html', rooms=rooms, user_room_ids=user_room_ids)

@app.route('/rooms/<int:room_id>', methods=['GET', 'POST'])
@login_required
def room(room_id):
    chat_room = ChatRoom.query.get_or_404(room_id)
    membership = ChatRoomMember.query.filter_by(user_id=session['user_id'], room_id=room_id).first()
    if not membership:
        flash('You are not a member of this room.', 'error')
        return redirect(url_for('home'))
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if content:
            msg = ChatRoomMessage(room_id=room_id, sender_id=session['user_id'], content=content)
            db.session.add(msg)
            db.session.commit()
        return redirect(url_for('room', room_id=room_id))
    messages = ChatRoomMessage.query.filter_by(room_id=room_id).order_by(ChatRoomMessage.timestamp.asc()).all()
    members = ChatRoomMember.query.filter_by(room_id=room_id).all()
    return render_template('room.html', room=chat_room, messages=messages, members=members, current_user_id=session['user_id'])

# ─── Party Routes (from team) ─────────────────────────────────────────────────

@app.route('/party/create', methods=['GET', 'POST'])
@login_required
def create_party():
    if request.method == 'POST':
        new_party = Party(
            r_name=request.form['r_name'],
            c=request.form['c'],
            p_size=request.form['p_size'],
            p_host=session['username'],
            p_date=request.form['p_date']
        )
        db.session.add(new_party)
        db.session.commit()
        flash('Party created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_party.html')

@app.route('/party/<int:party_id>')
@login_required
def view_party(party_id):
    party = Party.query.get_or_404(party_id)
    return render_template('party.html', party=party)

@app.route('/party/<int:party_id>/join', methods=['POST'])
@login_required
def join_party(party_id):
    party = Party.query.get_or_404(party_id)
    already_member = Member.query.filter_by(name=session['username'], party_id=party_id).first()
    if already_member:
        flash('You are already in this party!', 'error')
        return redirect(url_for('view_party', party_id=party_id))
    if len(party.members) >= party.p_size:
        flash('This party is full!', 'error')
        return redirect(url_for('view_party', party_id=party_id))
    member = Member(name=session['username'], party_id=party_id)
    db.session.add(member)
    db.session.commit()
    flash('You joined the party!', 'success')
    return redirect(url_for('view_party', party_id=party_id))

@app.route('/party/<int:party_id>/message', methods=['POST'])
@login_required
def send_message(party_id):
    content = request.form['content']
    if content.strip():
        message = Message(content=content, sender=session['username'], party_id=party_id)
        db.session.add(message)
        db.session.commit()
    return redirect(url_for('view_party', party_id=party_id))

@app.route('/party/<int:party_id>/leave', methods=['POST'])
@login_required
def leave_party(party_id):
    member = Member.query.filter_by(name=session['username'], party_id=party_id).first()
    if member:
        db.session.delete(member)
        db.session.commit()
        flash('You left the party.', 'info')
    return redirect(url_for('home'))

@app.route('/party_search')
@login_required
def party_search():
    query = request.args.get('q', '')
    cuisine = request.args.get('cuisine', '')
    date = request.args.get('date', '')
    parties = Party.query
    if query:
        parties = parties.filter(Party.r_name.ilike(f'%{query}%'))
    if cuisine:
        parties = parties.filter(Party.c.ilike(f'%{cuisine}%'))
    if date:
        parties = parties.filter(Party.p_date == date)
    parties = parties.order_by(Party.created_at.desc()).all()
    return render_template('party_search.html', parties=parties, query=query, cuisine=cuisine, date=date)

if __name__ == '__main__':
    app.run(debug=True)
