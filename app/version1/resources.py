from flask import g, jsonify, request, Response
from flask.ext.restful import Resource, marshal
from flask.ext.httpauth import HTTPBasicAuth
from flask_restful import reqparse
from sqlalchemy.exc import IntegrityError
from serializers import user_serializer, bucketlist_serializer, item_serializer
from .. models import User, Bucketlist, Item
from .. import db, app


auth = HTTPBasicAuth()


@auth.error_handler
def unauthorized(message=None):
    """
    Return 403 instead of 401 to prevent browsers from displaying the default
    auth dialog
    """
    if not message:
        message = "You are not authorized to access this page. Please log in"
        " and try aagin."
    return jsonify({
        "Message": message
    }), 403


@app.before_request
def before_request():
    """
    Verify a user's password.
    Returns true if the password is correct.
    """
    if request.endpoint not in ["userlogin", "userregister"]:
        token = request.headers.get("Token")
        if token is not None:
            user = User.verify_auth_token(token)
            if user:
                g.user = user
            else:
                return unauthorized("The token you have entered is invalid.")
        else:
            return unauthorized("Please enter a token.")


def add_item(**kwargs):
    """
    Add a user, bucketlist, or bucketlist item to the database.
    Also handles integrity errors.
    Arguments:
        kwargs["name"]: The title of the item to be added to the db.
        kwargs["item"]: The item to be added to the database.
        kwargs["serializer"]: The marshal serializer.
        kwargs["is_user"]: The flag used to identify users.
        kwargs["is_bucketlist"]: The flag used to identify bucketlists.
        kwargs["is_item"]: The flag used to identify bucketlist items.
    """
    try:
        db.session.add(kwargs["item"])
        db.session.commit()
        if kwargs["is_user"]:
            item_type = "user"
        elif kwargs["is_bucketlist"]:
            item_type = "bucketlist"
        elif kwargs["is_item"]:
            item_type = "bucketlist item"

        message = {"Message": "You have successfully registered a new " +
                   item_type + "."}
        response = marshal(kwargs['item'], kwargs['serializer'])
        response.update(message)
        return response, 201

    except IntegrityError:
        """When adding an item that already exists"""
        db.session.rollback()
        return {"Error": "The " + kwargs["name"] +
                " that you tried to enter already exists."}


def delete_item(item, name, **kwargs):
    """
    Delete a user, bucketlist, or bucketlist item from the database.

    Arguments:
        item: The item to be deleted.
        name: The name of the item to be deleted.
        kwargs["is_user"]: The flag is used to identify users.
        kwargs["is_bucketlist"]: The flag is used to identify bucketlists.
        kwargs["is_item"]: The flag is used to identify bucketlist items.
    """
    if item:
        db.session.delete(item)
        db.session.commit()
        if kwargs["is_user"]:
            item_type = "user"
        elif kwargs["is_bucketlist"]:
            item_type = "bucketlist"
        elif kwargs["is_item"]:
            item_type = "bucketlist item"
        return {"Message": "You have successfully deleted the following " +
                item_type + ": " + name}
    else:
        return {"Message": "Unsuccessful. Please try again!"}


class Index(Resource):
    """
    Manage responses to the index route.
    URL: /api/v1.0/
    Request: GET
    """

    def get(self):
        """Return a welcome message"""
        return {"Message": "Welcome to the Bucket List API. "
                "Register a new user or login to get started!"}


class UserRegister(Resource):
    """
    Register a new user.
    URL: /api/v1.0/auth/register/
    Request: POST
    """

    def post(self):
        """ Add a user """
        parser = reqparse.RequestParser()
        parser.add_argument(
            "username",
            required=True,
            help="Please enter a username.")
        parser.add_argument(
            "password",
            required=True,
            help="Please enter a password.")
        args = parser.parse_args()
        username, password = args["username"], args["password"]
        user = User(username=username,
                    password=password)
        return add_item(name="username",
                        item=user,
                        serializer=user_serializer,
                        is_user=True,
                        is_bucketlist=False,
                        is_item=False)


class UserLogin(Resource):
    """
    Log a user in.
    URL: /api/v1.0/auth/login/
    Request: POST
    """

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument(
            "username",
            required=True,
            help="Please enter a username.")
        parser.add_argument(
            "password",
            required=True,
            help="Please enter a password.")
        args = parser.parse_args()
        username, password = args["username"], args["password"]

        if username and password:
            user = User.query.filter_by(username=username).first()
        else:
            return {"Message": "Please enter a username and password."}
        if user and user.verify_password(password):
            token = user.generate_auth_token()
            return {"Token": token.decode("ascii")}
        else:
            return {"Message": "Error: incorrect username and/or password. "
                    "Please try again!"}


class BucketListsAPI(Resource):
    """
    URL: /api/v1.0/bucketlists/
    Requests: GET, POST
    """
    def get(self):
        bucketlists = Bucketlist.query.filter_by(user_id=g.user.id).all()
        return marshal(bucketlists, bucketlist_serializer), 201

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument("title", required=True, help="No title provided.")
        parser.add_argument("description", type=str, default="")
        args = parser.parse_args()
        title, description = args["title"], args["description"]
        bucketlist = Bucketlist(title=title,
                                description=description,
                                user_id=g.user.id)
        return add_item(name="title",
                        item=bucketlist,
                        serializer=bucketlist_serializer,
                        is_user=False,
                        is_bucketlist=True,
                        is_item=False)


class BucketListAPI(Resource):
    """
    URL: /api/v1.0/bucketlist/<id>
    Requests: GET, PUT, DELETE
    """
    def get(self):
        pass

    def put(self):
        pass

    def delete(self, id):
        bucketlist = Bucketlist.query.filter_by(id=id).first()
        if bucketlist:
            return delete_item(bucketlist,
                               bucketlist.title,
                               is_user=False,
                               is_bucketlist=True,
                               is_item=False)
        else:
            return {"Message": "The bucket list you are trying to delete "
                    "no longer exists. Please try again!"}


class ItemsAPI(Resource):
    """
    URL: /api/v1.0/bucketlist/<id>/items/
    Requests: GET, POST
    """
    def get(self):
        pass

    def post(self):
        pass


class ItemAPI(Resource):
    """
    URL: /api/v1.0/bucketlists/<id>/items/<item_id>
    Requests: GET, PUT, DELETE
    """
    def get(self):
        pass

    def delete(self, id):
        pass