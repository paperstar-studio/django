import io
import os
from github import Auth, Github



def abel_gh_auth():
    SECRET_KEY = os.getenv("GH_AUTH") 
    #SECRET_KEY = os.environ.get("GH_AUTH")
    auth = Auth.Token(SECRET_KEY)
    return Github(auth=auth), Github(auth=auth).get_user()


def abel_put_file(g, u, in_file="U.csv"):
    repo = u.get_repo("data-storage")
    branch = "main"
    all_files = []
    contents = repo.get_contents("")
    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
        else:
            file = file_content
            all_files.append(
                str(file).replace('ContentFile(path="', "").replace('")', "")
            )
    with open(in_file, "r") as file:
        content = file.read()
    git_file = in_file
    if git_file in all_files:
        contents = repo.get_contents(git_file)
        repo.update_file(
            contents.path, "committing files", content, contents.sha, branch=branch
        )
        print(git_file + " UPDATED")
    else:
        repo.create_file(git_file, "committing files", content, branch=branch)
        print(git_file + " CREATED")
    return 0


def abel_get_file(g, u, get_file="U.csv"):
    repo = u.get_repo("data-storage")
    file_content = repo.get_contents(get_file)
    file_content = file_content.decoded_content.decode()
    return io.StringIO(file_content)



def gather_oauth():
    import cherrypy
    import os
    import sys
    import threading
    import traceback
    import webbrowser

    from urllib.parse import urlparse
    from base64 import b64encode
    from fitbit.api import Fitbit
    from oauthlib.oauth2.rfc6749.errors import MismatchingStateError, MissingTokenError

    class OAuth2Server:
        def __init__(self, client_id, client_secret, redirect_uri='http://127.0.0.1:8080/'):
            self.success_html = """
                <h1>You are now authorized to access the Fitbit API!</h1>
                <br/><h3>You can close this window</h3>"""
            self.failure_html = """<h1>ERROR: %s</h1><br/><h3>You can close this window</h3>%s"""
            self.fitbit = Fitbit( client_id, client_secret, redirect_uri=redirect_uri, timeout=10,)
            self.redirect_uri = redirect_uri

        def browser_authorize(self):
            url, _ = self.fitbit.client.authorize_token_url()
            threading.Timer(1, webbrowser.open, args=(url,)).start()
            urlparams = urlparse(self.redirect_uri)
            cherrypy.config.update({'server.socket_host': urlparams.hostname,
                                    'server.socket_port': urlparams.port})
            cherrypy.quickstart(self)

        @cherrypy.expose
        def index(self, state, code=None, error=None):
            error = None
            if code:
                try:
                    self.fitbit.client.fetch_access_token(code)
                except MissingTokenError:
                    error = self._fmt_failure(
                        'Missing access token parameter.</br>Please check that '
                        'you are using the correct client_secret')
                except MismatchingStateError:
                    error = self._fmt_failure('CSRF Warning! Mismatching state')
            else:
                error = self._fmt_failure('Unknown error while authenticating')
            self._shutdown_cherrypy()
            return error if error else self.success_html

        def _fmt_failure(self, message):
            tb = traceback.format_tb(sys.exc_info()[2])
            tb_html = '<pre>%s</pre>' % ('\n'.join(tb)) if tb else ''
            return self.failure_html % (message, tb_html)

        def _shutdown_cherrypy(self):
            if cherrypy.engine.state == cherrypy.engine.states.STARTED:
                threading.Timer(1, cherrypy.engine.exit).start()

    client_id = "23PHFZ"
    client_secret = "c9c1e6571a6d9202ac912c32ed15b4c1"
    
    server = OAuth2Server(client_id, client_secret)
    server.browser_authorize()

    #profile = server.fitbit.user_profile_get()
    #print('You are authorized to access data for the user: {}'.format(
    #    profile['user']['fullName']))

    #print('TOKEN\n=====\n')
    
    return_dict = {}
    for key, value in server.fitbit.client.session.token.items():
        #print('{} = {}'.format(key, value))
        return_dict[key] = value
    
    return return_dict   
    #return redirect('/data_old')
    #return redirect(reverse('graphs:data_old', kwargs={ 'bar': 'FooBar' }))

