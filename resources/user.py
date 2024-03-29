from flask.views import MethodView
from flask_smorest import Blueprint, abort
from passlib.hash import pbkdf2_sha256
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity, create_refresh_token
from mail import mail

from db import db
from models import UserModel
from schemas import UserSchema, UserRegisterSchema
from blocklist import BLOCKLIST
from flask_mail import Message

blp = Blueprint('Users', 'users', description='Operations on users')

def send_register_email(user):
    msg = Message('Welcome to stores RESTAPI', 
                  sender='noreply@demo.com',
                  recipients=[user.email],
                  body=f'Your account with username {user.username} has been created successfully'
                  )
    mail.send(msg)

@blp.route('/register')
class UserRegister(MethodView):

    @blp.arguments(UserRegisterSchema)
    def post(self, user_data):
        try:
            user=UserModel(username=user_data['username'],
            email=user_data['email'],
            password=pbkdf2_sha256.hash(user_data['password'])
            )
            db.session.add(user)
            db.session.commit()
            send_register_email(user)
            return {"message": "user created successfully"}
        except IntegrityError:
            abort(409, "A user with that username already exists")


@blp.route('/login')
class UserLogin(MethodView):

    @blp.arguments(UserSchema)
    def post(self, user_data):
        user = UserModel.query.filter_by(username=user_data['username']).first()

        if user and pbkdf2_sha256.verify(user_data['password'], user.password):
            access_token = create_access_token(identity=user.id, fresh=True)
            refresh_token = create_refresh_token(identity=user.id)
            return {"access token": access_token, "refresh_token": refresh_token}
        abort(401, "Invalid Credentials")


@blp.route('/refresh')
class TokenRefresh(MethodView):
    @jwt_required(refresh=True)
    def post(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        return {"access_token": new_token}


@blp.route('/logout')
class UserLogout(MethodView):
    @jwt_required()
    def post(self):
        jti = get_jwt()['jti']
        print(jti)
        BLOCKLIST.add(jti)
        return {"message": "Successfully logged out"}



@blp.route('/user/<int:user_id>')
class User(MethodView):

    @blp.response(200, UserSchema)
    def get(self, user_id):
        user = UserModel.query.get_or_404(user_id)
        return user

    def delete(self, user_id):
        user = UserModel.query.get_or_404(user_id)

        db.session.delete(user)
        db.session.commit()
        return {"message": "User deleted"}, 200

