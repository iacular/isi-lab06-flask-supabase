import os
import psycopg2
from dotenv import load_dotenv
from sqlalchemy import select, text, or_, URL
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

PROJECT_REF = "musnyhqedcmndfplntzy"
password = os.getenv("DB_PASSWORD")
raw_db_url = os.getenv("DATABASE_URL")

# Dacă ai pus doar DB_PASSWORD, găsim automat clusterul corect din Supabase
if password:
    password = password.strip()
    candidate_hosts = [
        "aws-0-eu-central-1.pooler.supabase.com",
        "aws-1-eu-central-1.pooler.supabase.com",
        "aws-1-eu-west-1.pooler.supabase.com",
        "aws-0-eu-west-1.pooler.supabase.com",
        "aws-0-eu-west-2.pooler.supabase.com",
        "aws-1-eu-west-2.pooler.supabase.com",
        "aws-0-eu-west-3.pooler.supabase.com",
        "aws-0-eu-north-1.pooler.supabase.com",
        "aws-0-us-east-1.pooler.supabase.com",
    ]
    chosen_host = None
    for host in candidate_hosts:
        try:
            conn = psycopg2.connect(
                host=host,
                port=5432,
                user=f"postgres.{PROJECT_REF}",
                password=password,
                 dbname="postgres",
                connect_timeout=3
            )
            conn.close()
            chosen_host = host
            print(f"[OK] Cluster Supabase găsit automat: {host}")
            break
        except psycopg2.OperationalError as e:
            err_msg = str(e)
            if "tenant/user" in err_msg or "Tenant or user not found" in err_msg:
                continue
            elif "password authentication failed" in err_msg:
                raise RuntimeError(f"Hostul {host} este cel corect, dar PAROLA din .env este greșită!")
            else:
                continue

    if not chosen_host:
        raise RuntimeError("Nu am găsit proiectul pe clusterele standard. Verifică în Supabase -> Connect -> Connection string.")

    db_url = URL.create(
        drivername="postgresql+psycopg2",
        username=f"postgres.{PROJECT_REF}",
        password=password,
        host=chosen_host,
        port=5432,
        database="postgres"
    ).render_as_string(hide_password=False)

elif raw_db_url:
    raw_db_url = raw_db_url.strip()
    for prefix in ("postgres://", "postgresql://"):
        if raw_db_url.startswith(prefix):
            raw_db_url = "postgresql+psycopg2://" + raw_db_url[len(prefix):]
            break
    db_url = raw_db_url
else:
    raise RuntimeError("Setează DB_PASSWORD în fișierul backend/.env")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

db = SQLAlchemy(app)


class Task(db.Model):
    __tablename__ = "task"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True, default="")
    completed = db.Column(db.Boolean, default=False)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


with app.app_context():
    db.create_all()
    print("Conectat la Postgres, tabelul task exista.")


def error(message, code):
    return jsonify({"status": False, "error": message}), code


@app.route('/', methods=['GET'])
def index():
    return "Lab6 Backend Server"


# Pasul 3.4: Verificarea conexiunii la DB
@app.route('/db-check', methods=['GET'])
def db_check():
    try:
        row = db.session.execute(
            text("SELECT current_database() AS db, version() AS version")
        ).mappings().one()

        return jsonify({
            "status": True,
            "database": "PostgreSQL",
            "version": row["version"],
            "data": dict(row)
        }), 200
    except Exception as e:
        return error(str(e), 500)


# TODO 1 & TODO 7: POST /tasks (Adăugare + Validare)
@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return error("Trimite un body JSON.", 400)

    title = data.get("title")
    description = data.get("description", "")

    if not isinstance(title, str) or not title.strip():
        return error("Câmpul 'title' este obligatoriu.", 400)

    if len(title.strip()) > 100:
        return error("Câmpul 'title' poate avea maxim 100 de caractere.", 400)

    if description is not None and (not isinstance(description, str) or len(description) > 200):
        return error("Descriere invalidă (maxim 200 de caractere).", 400)

    task = Task(
        title=title.strip(),
        description=description if description is not None else ""
    )

    db.session.add(task)
    db.session.commit()

    return jsonify({
        "status": True,
        "data": task.as_dict()
    }), 201


# TODO 2: GET /tasks (Toate task-urile ordonate după id)
@app.route('/tasks', methods=['GET'])
def get_all_tasks():
    tasks = db.session.scalars(
        select(Task).order_by(Task.id)
    ).all()

    return jsonify({
        "status": True,
        "data": [task.as_dict() for task in tasks]
    }), 200


# TODO 3: GET /tasks/select, GET /tasks/<id>, GET /tasks/select/<id>
@app.route('/tasks/select', methods=['GET'])
def get_all_tasks_select():
    tasks = db.session.execute(
        text("SELECT * FROM task ORDER BY id")
    ).mappings().all()

    return jsonify({
        "status": True,
        "data": [dict(task) for task in tasks]
    }), 200


@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return error("Task not found", 404)

    return jsonify({
        "status": True,
        "data": task.as_dict()
    }), 200


@app.route('/tasks/select/<int:task_id>', methods=['GET'])
def get_task_select(task_id):
    task = db.session.execute(
        text("SELECT * FROM task WHERE id = :id"),
        {"id": task_id}
    ).mappings().first()

    if task is None:
        return error("Task not found", 404)

    return jsonify({
        "status": True,
        "data": dict(task)
    }), 200


# TODO 4 & TODO 7: PUT /tasks/<id> (Actualizare + Validare)
@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return error("Task not found", 404)

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return error("Trimite un body JSON.", 400)

    if "title" in data:
        title = data["title"]
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 100:
            return error("'title' nu poate fi gol și poate avea maxim 100 de caractere.", 400)
        task.title = title.strip()

    if "description" in data:
        description = data["description"]
        if description is not None and (not isinstance(description, str) or len(description) > 200):
            return error("Descriere invalidă.", 400)
        task.description = description

    if "completed" in data:
        if not isinstance(data["completed"], bool):
            return error("'completed' trebuie să fie true sau false.", 400)
        task.completed = data["completed"]

    db.session.commit()

    return jsonify({
        "status": True,
        "data": task.as_dict()
    }), 200


# TODO 5: DELETE /tasks/<id>
@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return error("Task not found", 404)

    db.session.delete(task)
    db.session.commit()

    return jsonify({
        "status": True,
        "message": "Task deleted successfully"
    }), 200


# TODO 6: PATCH /tasks/<id>/complete
@app.route('/tasks/<int:task_id>/complete', methods=['PATCH'])
def complete_task(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        return error("Task not found", 404)

    task.completed = True
    db.session.commit()

    return jsonify({
        "status": True,
        "data": task.as_dict()
    }), 200


# TODO 8: GET /tasks/filter?completed=true|false
@app.route('/tasks/filter', methods=['GET'])
def filter_tasks():
    completed = request.args.get("completed", "").lower()
    if completed not in ("true", "false"):
        return error("Parametrul 'completed' trebuie să fie true sau false.", 400)

    completed_value = completed == "true"

    tasks = db.session.scalars(
        select(Task)
        .where(Task.completed == completed_value)
        .order_by(Task.id)
    ).all()

    return jsonify({
        "status": True,
        "data": [task.as_dict() for task in tasks]
    }), 200


# TODO 9: GET /tasks/paginate?page=2&limit=5
@app.route('/tasks/paginate', methods=['GET'])
def paginate_tasks():
    try:
        page = int(request.args.get("page", 1))
        # Acceptă atât 'limit' (cerut în laborator) cât și 'per_page'
        raw_limit = request.args.get("limit", request.args.get("per_page", 5))
        limit = int(raw_limit)
    except ValueError:
        return error("Parametrii de paginare trebuie să fie numere întregi.", 400)

    if page < 1 or limit < 1 or limit > 100:
        return error("Condiții: page >= 1 și 1 <= limit <= 100.", 400)

    pagination = db.paginate(
        select(Task).order_by(Task.id),
        page=page,
        per_page=limit,
        error_out=False
    )

    return jsonify({
        "status": True,
        "data": [task.as_dict() for task in pagination.items],
        "page": page,
        "limit": limit,
        "total": pagination.total,
        "pages": pagination.pages
    }), 200


# TODO 10: GET /tasks/search?q=flask
@app.route('/tasks/search', methods=['GET'])
def search_tasks():
    query = request.args.get("q", "").strip()
    if not query:
        return error("Parametrul 'q' este obligatoriu.", 400)

    tasks = db.session.scalars(
        select(Task)
        .where(
            or_(
                Task.title.ilike(f"%{query}%"),
                Task.description.ilike(f"%{query}%")
            )
        )
        .order_by(Task.id)
    ).all()

    return jsonify({
        "status": True,
        "data": [task.as_dict() for task in tasks]
    }), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)