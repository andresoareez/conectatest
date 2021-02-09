import functools
import flask
from authlib.client import OAuth2Session
import google.oauth2.credentials
import googleapiclient.discovery
from models import User
import json

ACCESS_TOKEN_URI = 'https://www.googleapis.com/oauth2/v4/token'
AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent'
# Autenticando com Open Id Profile.
AUTHORIZATION_SCOPE ='openid email profile'
AUTH_REDIRECT_URI = "http://127.0.0.1:8040/google/auth"
BASE_URI = "http://127.0.0.1:8040"
CLIENT_ID = "1004161982937-3nj973qjl7bcfpa3gm40bb5mtqvhmn1v.apps.googleusercontent.com"
CLIENT_SECRET = "weDePVfDkdDTxtfT-tc2hLCY"
AUTH_TOKEN_KEY = 'auth_token'
# Guardando o estado de paramentro do OAuth na sessao flask
AUTH_STATE_KEY = 'auth_state'

app = flask.Blueprint('google_auth', __name__)


def is_logged_in():
    return True if AUTH_TOKEN_KEY in flask.session else False


def build_credentials():
    if not is_logged_in():
        raise Exception('User must be logged in')

    oauth2_tokens = flask.session[AUTH_TOKEN_KEY]

    return google.oauth2.credentials.Credentials(
        oauth2_tokens['access_token'],
        refresh_token=oauth2_tokens['refresh_token'],
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri=ACCESS_TOKEN_URI)

# pegando informação do usuario google e passando num dicionario
def get_user_info():
    credentials = build_credentials()

    oauth2_client = googleapiclient.discovery.build(
        'oauth2', 'v2',
        credentials=credentials)
    datauser = oauth2_client.userinfo().get()

    return oauth2_client.userinfo().get().execute()

def banco_de_dados():
    dados = get_user_info()
    email = dados['email']
    separadordom = email.find("@") +1
    dominio = email[separadordom:]
    contatos = User(email=email, dominio=dominio)
    contatos.save()

def no_cache(view):
    @functools.wraps(view)
    def no_cache_impl(*args, **kwargs):
        response = flask.make_response(view(*args, **kwargs))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return functools.update_wrapper(no_cache_impl, view)


@app.route('/google/login')
@no_cache
def login():
    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=AUTHORIZATION_SCOPE,
                            redirect_uri=AUTH_REDIRECT_URI)

    uri, state = session.authorization_url(AUTHORIZATION_URL)

    flask.session[AUTH_STATE_KEY] = state
    flask.session.permanent = True

    return flask.redirect(uri, code=302)


# verificando de o paramentro na url é o mesmo salvo na ultima sessão
@app.route('/google/auth')
@no_cache
def google_auth_redirect():
    req_state = flask.request.args.get('state', default=None, type=None)

    if req_state != flask.session[AUTH_STATE_KEY]:
        response = flask.make_response('Invalid state parameter', 401)
        return response

    session = OAuth2Session(CLIENT_ID, CLIENT_SECRET,
                            scope=AUTHORIZATION_SCOPE,
                            state=flask.session[AUTH_STATE_KEY],
                            redirect_uri=AUTH_REDIRECT_URI)

    oauth2_tokens = session.fetch_access_token(
        ACCESS_TOKEN_URI,
        authorization_response=flask.request.url)

    flask.session[AUTH_TOKEN_KEY] = oauth2_tokens

    return flask.redirect(BASE_URI, code=302)


@app.route('/google/logout')
@no_cache
def logout():
    flask.session.pop(AUTH_TOKEN_KEY, None)
    flask.session.pop(AUTH_STATE_KEY, None)

    return flask.redirect(BASE_URI, code=302)