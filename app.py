import string
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from models import db, Party, Member, Message, User, Friendship, DirectMessage, ChatRoom, ChatRoomMember, ChatRoomMessage
from functools import wraps
from dotenv import load_dotenv

load_dotenv()
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


@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    user = User.query.get(session['user_id'])
    parties = Party.query.order_by(Party.created_at.desc()).all()
    chat_info = chat.chat_info(user.id)
    
    search_results = None
    search_query = None
    
    if request.method == 'POST':
        info = chat.user_search(request=request, session=session)
        search_results = info.get("results")
        search_query = info.get("query")
        
    return render_template('home.html', user=user, username=session['username'],
            parties=parties, friends=chat_info["friends"], pending=chat_info["pending"], rooms=chat_info["rooms"],
            search_results=search_results, search_query=search_query)

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
    return render_template('chat/search.html', results=info["results"], query=info["query"])

# ─── Friend System ────────────────────────────────────────────────────────────

@app.route('/friends/add/<int:target_id>', methods=['POST'])
@login_required
def add_friend(target_id):
    val = chat.add_friend(session=session, target_id=target_id)
    if val == "self":
        flash("You can't add yourself.", 'error')
        return redirect(request.referrer or url_for('home'))
    else:
        if val == "previous":
            flash('Friend request already sent or you are already friends.', 'error')
        else:
            flash('Friend request sent!', 'success')
        return redirect(request.referrer or url_for('home'))

@app.route('/friends/accept/<int:friendship_id>', methods=['POST'])
@login_required
def accept_friend(friendship_id):
    val = chat.accept_friend(friendship_id=friendship_id, session=session)
    if val == "fail":
        flash('Unauthorized.', 'error')
        return redirect(url_for('home'))
    flash('Friend request accepted!', 'success')
    return redirect(url_for('home'))

@app.route('/friends/decline/<int:friendship_id>', methods=['POST'])
@login_required
def decline_friend(friendship_id):
    val = chat.decline_friend(friendship_id=friendship_id, session=session)
    if val == "fail":
        flash('Unauthorized.', 'error')
        return redirect(url_for('home'))
    flash('Friend request declined.', 'info')
    return redirect(url_for('home'))


@app.route('/dm/<int:friend_id>', methods=['GET', 'POST'])
@login_required
def direct_message(friend_id):
    val = chat.send_dm(session=session, friend_id=friend_id, request=request)
    if val == "not":
        flash('You must be friends to send a direct message.', 'error')
        return redirect(url_for('home'))
    if val == "post":
        return redirect(url_for('direct_message', friend_id=friend_id))
    return render_template('chat/dm.html', friend=User.query.get_or_404(friend_id), messages=val, current_user_id=session['user_id'])

# ─── Chat Rooms ───────────────────────────────────────────────────────────────

@app.route('/rooms/create', methods=['GET', 'POST'])
@login_required
def create_room():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if not name:
            flash('Room name is required.', 'error')
            return redirect(url_for('create_room'))
        val = chat.create_room(session=session, request=request, name=name)
        flash(f'Room created! Share the code: {val["code"]}', 'success')
        return redirect(url_for('room', room_id=val["chat_room"].id))
    return render_template('chat/create_room.html')

@app.route('/rooms/join', methods=['GET', 'POST'])
@login_required
def join_room():
    if request.method == 'POST':
        val : dict = chat.join_room
        flash(val["flash"][0], val["flash"][1])
        if "id" in val:
            return redirect(url_for(val["url"], room_id=val["id"]))
        return redirect(url_for(val["url"]))
    return render_template('chat/join_room.html')

@app.route('/rooms/browse')
@login_required
def browse_rooms():
    rooms = ChatRoom.query.filter_by(is_public=True).order_by(ChatRoom.created_at.desc()).all()
    user_room_ids = {m.room_id for m in ChatRoomMember.query.filter_by(user_id=session['user_id']).all()}
    return render_template('chat/browse_rooms.html', rooms=rooms, user_room_ids=user_room_ids)

@app.route('/rooms/<int:room_id>', methods=['GET', 'POST'])
@login_required
def room(room_id):
    val = chat.room(room_id=room_id, session=session, request=request)
    if val["status"] == "fail":
        flash('You are not a member of this room.', 'error')
        return redirect(url_for('home'))
    if val["status"] == "post":
        return redirect(url_for('room', room_id=room_id))
    return render_template(val["args"]["url"], room=val["args"]["room"], messages=val["args"]["messages"],
                           members=val["args"]["members"], current_user_id=val["args"]["current_user_id"])


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
    r_name = request.args.get('r_name', '')
    c = request.args.get('c', '')
    return render_template('create_party.html', r_name=r_name, c=c)

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
    query = request.args.get()
    cuisine = request.args.get()
    start_date = request.args.get()
    end_date = request.args.get()
    parties = Party.query
    if query:
        parties = parties.filter(Party.r_name.ilike(f'%{query}%'))
    if cuisine:
        parties = parties.filter(Party.c.ilike(f'%{cuisine}%'))
    if start_date:
        parties = parties.filter(Party.p_date == start_date)
    parties = parties.order_by(Party.created_at.desc()).all()
    return render_template('party_search.html', parties=parties, query=query, cuisine=cuisine, date=start_date)

# ─── Restaurant Search ────────────────────────────────────────────────────────

@app.route('/restaurant_search')
@login_required
def restaurant_search():
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    return render_template('restaurant_search.html', api_key=api_key)

# ─── Map ─────────────────────────────────────────────────────────────────────

@app.route('/map')
@login_required
def map_view():
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    return render_template('map.html', api_key=api_key)

if __name__ == '__main__':
    app.run(debug=True)
