from flask_sqlalchemy import SQLAlchemy
print("DEBUG: models.py is being imported")

# Initialize SQLAlchemy (linked to app in app.py)
db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return f"<User {self.name}>"
