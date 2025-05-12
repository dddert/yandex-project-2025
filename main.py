from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'

Base = declarative_base()
engine = create_engine('sqlite:///files.db')
Session = sessionmaker(bind=engine)
session = Session()

UPLOAD_FOLDER = 'downloads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'ogg'}

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    file_name = Column(String)
    description = Column(Text)
    date_uploaded = Column(DateTime)

class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    title = Column(String)
    content = Column(Text)
    date_created = Column(DateTime)

Base.metadata.create_all(engine)

@app.route('/')
def index():
    files = session.query(File).all()
    notes = session.query(Note).all()
    return render_template('index.html', files=files, notes=notes)
from flask import send_from_directory

@app.route('/downloads/<path:filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/addnote', methods=['GET', 'POST'])
def add_note():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        user_id = int(request.form['user_id'])
        new_note = Note(user_id=user_id, title=title, content=content, date_created=datetime.now())
        session.add(new_note)
        session.commit()
        flash('Заметка добавлена!')
        return redirect(url_for('index'))
    return render_template('add_note.html')

@app.route('/deletenote/<int:note_id>')
def delete_note(note_id):
    note = session.query(Note).get(note_id)
    if note:
        session.delete(note)
        session.commit()
        flash('Заметка удалена.')
    return redirect(url_for('index'))

@app.route('/deletefile/<int:file_id>')
def delete_file(file_id):
    file = session.query(File).get(file_id)
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        session.delete(file)
        session.commit()
        flash('Файл удалён.')
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        uploaded_file = request.files['file']
        user_id = int(request.form['user_id'])
        if uploaded_file and allowed_file(uploaded_file.filename):
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(file_path)

            new_file_record = File(
                user_id=user_id,
                file_name=uploaded_file.filename,
                description='Загруженный через веб',
                date_uploaded=datetime.now()
            )
            session.add(new_file_record)
            session.commit()
            flash('Файл успешно загружен!')
            return redirect(url_for('index'))
        else:
            flash('Недопустимый формат файла.')
    return render_template('upload.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(debug=True)
