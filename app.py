import flask
from flask_sqlalchemy import SQLAlchemy
from uuid import uuid4
from flask_login import LoginManager, login_user, current_user, logout_user, UserMixin
from id_verification import verify_id
import datetime
from flask_migrate import Migrate
from flask_mail import Mail, Message
import os
from pdf_to_images import process_pdf


app = flask.Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SECRET_KEY"] = "asaf-was223-sasf2-qsafs.aSAFSa2"

db = SQLAlchemy(app)

login_manager = LoginManager(app)

migrate = Migrate(app, db)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'bilgi@ebelgem.net'
app.config['MAIL_PASSWORD'] = 'vrtn kmni oeji asuo'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    password = db.Column(db.String)
    company_name = db.Column(db.String)

    @property
    def owned_docs(self):
        return Document.query.filter_by(owner_fk=self.id).all()

    @property
    def signed_docs(self):
        docs = Document.query.filter_by(owner_fk=self.id).all()
        signatures = 0
        for i in docs:
            for c in Signature.query.filter_by(document_fk=i.id).all():
                if c.status == "İmzalandı":
                    signatures += 1

        return signatures

    @property
    def pending_docs(self):
        docs = Document.query.filter_by(owner_fk=self.id).all()
        signatures = 0
        for i in docs:
            for c in Signature.query.filter_by(document_fk=i.id).all():
                if c.status == "İmza Talep Edildi":
                    signatures += 1

        return signatures

    @property
    def usage(self):
        docs = Document.query.filter_by(owner_fk=self.id).all()
        signatures = 0
        for i in docs:
            for c in Signature.query.filter_by(document_fk=i.id).all():
                if c.status == "İmzalandı" and c.signature_date > datetime.date.today() - datetime.timedelta(days=30):
                    signatures += 1

        return signatures


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_uuid = db.Column(db.String)
    owner_fk = db.Column(db.Integer)
    document_name = db.Column(db.String)

    @property
    def signature(self):
        return Signature.query.filter_by(document_fk=self.id).first()

    @property
    def owner(self):
        return User.query.get(self.owner_fk)


class Signature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_fk = db.Column(db.Integer)
    fullname = db.Column(db.String)
    tc_kimlik = db.Column(db.Integer)
    email = db.Column(db.String)
    status = db.Column(db.String, default="İmza Talep Edildi")
    ip_address = db.Column(db.String)
    signature_uuid = db.Column(db.String)
    signature_date = db.Column(db.Date)

    @property
    def document(self):
        return Document.query.get(self.document_fk)


def notify_signature(document):
    with open("emails/notify_success.html", "r") as email:
        msg = Message(
            subject=f"{document.document_name} Tamamlandı",
            sender="bilgi@ebelgem.net",
            recipients=[document.signature.email, document.owner.email]
        )
        msg.html = email.read().replace("%docname%", document.document_name)
        mail.send(message=msg)


def send_doc_email(signature):
    with open("emails/send_doc.html", "r") as email:
        msg = Message(
            subject=f"{signature.document.owner.company_name} size imzalamanız için bir doküman iletti.",
            sender="bilgi@ebelgem.net",
            recipients=[signature.email]
        )
        msg.html = email.read().replace("%company%", signature.document.owner.company_name).replace("%signature_uuid%", signature.signature_uuid)
        mail.send(message=msg)


@login_manager.user_loader
def user_loader(user_id):
    return User.query.get(user_id)


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route("/signup", methods=["POST", "GET"])
def signup():
    if flask.request.method == "POST":
        values = flask.request.values
        new_business_signup = User(email=values.get("email"), password=values.get("password"),
                                   company_name=values.get("company_name"))
        db.session.add(new_business_signup)
        db.session.commit()
        return flask.redirect("/signin")
    return flask.render_template("signup.html")


@app.route("/signin", methods=["POST", "GET"])
def signin():
    if flask.request.method == "POST":
        values = flask.request.values
        business_lookup = User.query.filter_by(email=values.get("email")).first()
        if business_lookup:
            if business_lookup.password == values.get("password"):
                login_user(business_lookup)
                return flask.redirect("/dashboard")

        return flask.render_template("signin.html", failed_login=True)

    return flask.render_template("signin.html")


@app.route("/dashboard")
def dashboard():
    if not current_user.is_authenticated:
        return flask.redirect("/")
    documents = current_user.owned_docs
    return flask.render_template("dashboard.html", documents=documents, user=current_user)


@app.route("/upload_doc", methods=["POST", "GET"])
def upload_doc():
    if flask.request.method == "POST":
        values = flask.request.values

        pdf_document = flask.request.files.get("agreement_doc")
        doc_name = pdf_document.filename
        doc_uuid = str(uuid4())
        pdf_document.save("documents/" + doc_uuid + ".pdf")

        new_document = Document(document_uuid=doc_uuid, owner_fk=current_user.id, document_name=doc_name)
        db.session.add(new_document)
        db.session.commit()

        new_requested_signature = Signature(email=values.get("email"), signature_uuid=str(uuid4()),
                                            document_fk=new_document.id)

        db.session.add(new_requested_signature)
        db.session.commit()

        process_pdf(new_document.document_uuid)

        send_doc_email(signature=new_requested_signature)

        return flask.redirect("/dashboard")
    return flask.render_template("upload_doc.html")


@app.route("/sign_doc/<signature_uuid>", methods=["POST", "GET"])
def sign_doc(signature_uuid):
    signature = Signature.query.filter_by(signature_uuid=signature_uuid).first()
    if not signature:
        return flask.render_template("deleted_doc.html")
    if not signature.document:
        return flask.render_template("deleted_doc.html")
    if flask.request.method == "POST":
        values = flask.request.values

        if not verify_id(values.get("tc_kimlik"), values.get("name"), values.get("surname"), values.get("dob")):
            return flask.render_template("cannot_verify_id.html", signature_uuid=signature.signature_uuid)

        new_signature = Signature.query.filter_by(signature_uuid=signature_uuid).first()

        new_signature.status = "İmzalandı"
        new_signature.ip_address = flask.request.environ["REMOTE_ADDR"] if not flask.request.environ.get(
                'HTTP_X_FORWARDED_FOR') else flask.request.environ.get('HTTP_X_FORWARDED_FOR')
        new_signature.fullname = values.get("name") + " " + values.get("surname")
        new_signature.tc_kimlik = values.get("tc_kimlik")
        new_signature.signature_date = datetime.date.today()

        db.session.commit()

        notify_signature(new_signature.document)

        return flask.render_template("thanks.html")

    return flask.render_template("sign_doc.html", signature=signature)


@app.route("/profile")
def profile():
    return flask.render_template("profile.html", user=current_user)


@app.route("/cancel/<doc_uuid>")
def cancel_doc(doc_uuid):
    doc = Document.query.filter_by(document_uuid=doc_uuid).first()
    if not doc.owner.id == current_user.id:
        return flask.redirect("/dashboard")
    if doc.signature.status == "İmzalandı":
        return flask.redirect("/dashboard")
    db.session.delete(doc.signature)
    db.session.delete(doc)
    db.session.commit()
    return flask.redirect("/dashboard")


@app.route("/logout")
def logout():
    logout_user()
    return flask.redirect("/")


@app.route("/view_doc/<doc_uuid>")
def view_doc(doc_uuid):
    return flask.render_template("view_doc.html", document=Document.query.filter_by(document_uuid=doc_uuid).first())


@app.route("/documents/<doc_uuid>")
def documents(doc_uuid):
    doc_images = sorted(os.listdir(f"documents/{doc_uuid}"))
    return flask.render_template("docview.html", doc_images=doc_images, doc_uuid=doc_uuid)


@app.route("/documenthost/<doc_uuid>/<img_name>")
def documenthost(doc_uuid, img_name):
    return flask.send_file(f"documents/{doc_uuid}/{img_name}")


@app.route("/static/<filename>")
def static_host(filename):
    return flask.send_file("static/" + filename)


@app.route("/<other>")
def other_host(other):
    return flask.render_template(other + ".html")
